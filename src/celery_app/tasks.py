import asyncio
from uuid import UUID
from celery import states
from celery.exceptions import Ignore
from .config import celery_app
from src.main import run_company_campaign
from src.logger import get_logger
from src.database import get_campaign_run

logger = get_logger(__name__)

@celery_app.task(
    name='tasks.run_campaign',
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def celery_run_company_campaign(self, campaign_id: str, campaign_run_id: str):
    """
    Celery task that wraps the async run_company_campaign function.
    Handles the conversion between string and UUID, and manages the event loop.
    """
    try:
        logger.info(f"Starting campaign task for campaign_id: {campaign_id}, run_id: {campaign_run_id}")
        
        campaign_run = get_campaign_run(UUID(campaign_run_id))

        # If campaign run doesn't exist, fail early
        if not campaign_run:
            logger.error(f"Campaign run {campaign_run_id} not found")
            raise ValueError(f"Campaign run {campaign_run_id} not found")
        
        # Check campaign run status
        if campaign_run['status'] in ['completed', 'failed']:
            logger.info(f"Campaign run {campaign_run_id} already processed with status: {campaign_run['status']}")
            return {
                'status': campaign_run['status'],
                'campaign_id': campaign_id,
                'campaign_run_id': campaign_run_id
            }
        
        # Use asyncio.run
        result = asyncio.run(
            run_company_campaign(
                UUID(campaign_id), 
                UUID(campaign_run_id)
            )
        )
        
        logger.info(f"Campaign task completed successfully for campaign_id: {campaign_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Error in campaign task: {str(exc)}")
        
        # If we've exceeded retries, mark as failed
        if self.request.retries >= self.max_retries:
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