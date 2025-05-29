import asyncio
from uuid import UUID
from celery import states
from celery.exceptions import Ignore
import logging
from ..config import celery_app
from src.main import run_company_campaign
from src.database import get_campaign_run
from src.database import init_pg_pool
import src.database
from celery.exceptions import SoftTimeLimitExceeded

logger = logging.getLogger(__name__)

async def _async_run_campaign(campaign_id: str, campaign_run_id: str, celery_task_id: str):
    
    # pg_pool variable and init_pg_pool calls are only needed if you are using direct calls to postgres using asyncpg from your task
    global pg_pool
    # Force a clean start to avoid inherited pool across fork
    await init_pg_pool(force_reinit=True) # Add this for every task because we need to create a new asyncpg pool for every task run
    
    logger.info(f"asyncpg pool after init: {src.database.pg_pool}") # Ensure the pool is created fresh inside this subprocess
    
    try:
        campaign_run = await get_campaign_run(UUID(campaign_run_id))
        if not campaign_run:
            logger.error(f"Campaign run {campaign_run_id} not found")
            raise ValueError("Campaign run not found")

        # Update campaign run with celery task ID
        from src.database import update_campaign_run_celery_task_id
        await update_campaign_run_celery_task_id(UUID(campaign_run_id), celery_task_id)

        # Check campaign run status
        if campaign_run['status'] in ['completed']:
            logger.info(f"Campaign run {campaign_run_id} already processed with status: {campaign_run['status']}")
            return {
                'status': campaign_run['status'],
                'campaign_id': campaign_id,
                'campaign_run_id': campaign_run_id
            }

        return await run_company_campaign(UUID(campaign_id), UUID(campaign_run_id))
    finally:
        logger.info(f"Asyncpg pool that is going to be closed: {src.database.pg_pool}")
        if src.database.pg_pool:
            await src.database.pg_pool.close()  # close the pool at the end of the task to release connections
            src.database.pg_pool = None

@celery_app.task(
    name='reachgenie.tasks.run_campaign',
    bind=True,
    max_retries=3,
    default_retry_delay=60 # 60 seconds
)
def celery_run_company_campaign(self, *, campaign_id: str, campaign_run_id: str):
    """
    Celery task that wraps the async run_company_campaign function.
    Handles the conversion between string and UUID, and manages the event loop.
    
    Args:
        campaign_id: UUID string of the campaign to run
        campaign_run_id: UUID string of the campaign run
    """
    try:
        logger.info(f"Starting campaign task for campaign_id: {campaign_id}, run_id: {campaign_run_id}")
        
        # Create a new event loop for all async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Your Celery task creates a new event loop each time it runs _async_run_campaign and creates a new asyncpg pool in that event loop
            result = loop.run_until_complete(_async_run_campaign(campaign_id, campaign_run_id, self.request.id))
            
            logger.info(f"Campaign task completed successfully for campaign_id: {campaign_id}")
            return result
        except SoftTimeLimitExceeded:
            logger.error(f"Campaign run {campaign_run_id} reached soft timeout limit")
            raise  # Re-raise so that it can be retried upto max retries
        finally:
            # Clean up the loop
            loop.close()
            
    except Exception as exc:
        logger.error(f"Error in campaign task: {str(exc)}")
        
        # If we've exceeded retries, mark as failed
        if self.request.retries >= self.max_retries:
            # Create a new event loop for the final database update
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Update campaign run status to failed with timeout message
                from src.database import update_campaign_run_status
                loop.run_until_complete(
                    update_campaign_run_status(
                        campaign_run_id=UUID(campaign_run_id),
                        status="failed",
                        failure_reason="Campaign execution exceeded the maximum time limit, Try running the same campaign again to process the remaining leads"
                    )
                )
            except Exception as update_error:
                logger.error(f"Failed to update campaign run status: {str(update_error)}")
            finally:
                loop.close()
                
            self.update_state(
                state=states.FAILURE,
                meta={
                    'exc_type': type(exc).__name__,
                    'exc_message': str(exc),
                    'campaign_id': campaign_id,
                    'campaign_run_id': campaign_run_id
                }
            )
            raise Ignore() # Stop retrying
        
        # Otherwise retry
        raise self.retry(exc=exc) 