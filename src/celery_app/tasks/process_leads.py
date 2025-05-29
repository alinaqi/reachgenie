import asyncio
from uuid import UUID
from celery import states
from celery.exceptions import Ignore, SoftTimeLimitExceeded
import logging
from ..config import celery_app
from src.main import process_leads_upload
from src.database import get_task_status

logger = logging.getLogger(__name__)

async def _async_process_leads(company_id: str, file_url: str, user_id: str, task_id: str):
    try:
        # Check if task is already completed
        task = await get_task_status(UUID(task_id))
        if task and task['status'] in ['completed', 'failed']:
            logger.info(f"Task {task_id} already processed with status: {task['status']}")
            return {
                'status': task['status'],
                'task_id': task_id,
                'result': task.get('result')
            }

        return await process_leads_upload(UUID(company_id), file_url, UUID(user_id), UUID(task_id))
    except Exception as e:
        logger.error(f"Error in _async_process_leads: {str(e)}")
        raise

@celery_app.task(
    name='reachgenie.tasks.process_leads',
    bind=True,
    max_retries=3,
    default_retry_delay=60  # 60 seconds
)
def celery_process_leads(self, *, company_id: str, file_url: str, user_id: str, task_id: str):
    """
    Celery task that wraps the async process_leads_upload function.
    Handles the conversion between string and UUID, and manages the event loop.
    
    Args:
        company_id: UUID string of the company
        file_url: URL of the uploaded file in storage
        user_id: UUID string of the user who initiated the upload
        task_id: UUID string of the upload task
    """
    try:
        logger.info(f"Starting leads processing task for company_id: {company_id}, task_id: {task_id}")
        
        # Create a new event loop for all async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Your Celery task creates a new event loop each time it runs _async_process_leads
            result = loop.run_until_complete(_async_process_leads(company_id, file_url, user_id, task_id))
            
            logger.info(f"Leads processing task: {task_id} completed successfully")
            return result
        except SoftTimeLimitExceeded:
            logger.error(f"Leads processing task: {task_id} reached soft timeout limit")
            raise  # Re-raise so that it can be retried up to max retries
        finally:
            # Clean up the loop
            loop.close()
            
    except Exception as exc:
        logger.error(f"Error in leads processing task: {task_id} - {str(exc)}")
        
        # If we've exceeded retries, mark as failed
        if self.request.retries >= self.max_retries:
            # Create a new event loop for the final database update
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                from src.database import update_task_status
                loop.run_until_complete(
                    update_task_status(
                        UUID(task_id),
                        "failed",
                        str(exc)
                    )
                )
            except Exception as update_error:
                logger.error(f"Failed to update task status: {str(update_error)}")
            finally:
                loop.close()
                
            self.update_state(
                state=states.FAILURE,
                meta={
                    'exc_type': type(exc).__name__,
                    'exc_message': str(exc),
                    'company_id': company_id,
                    'task_id': task_id
                }
            )
            raise Ignore()  # Stop retrying
        
        # Otherwise retry
        raise self.retry(exc=exc) 