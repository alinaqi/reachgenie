import asyncio
from uuid import UUID
import logging
from ..config import celery_app
from src.database import process_do_not_email_csv_upload
from celery.exceptions import Ignore, SoftTimeLimitExceeded
from celery import states
from src.database import get_task_status

logger = logging.getLogger(__name__)

async def _async_process_do_not_contact(company_id: str, file_url: str, user_id: str, task_id: str):    
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
        
        return await process_do_not_email_csv_upload(
            company_id=UUID(company_id),
            file_url=file_url,
            user_id=UUID(user_id),
            task_id=UUID(task_id)
        )
    except Exception as e:
        logger.error(f"Error in _async_process_do_not_contact: {str(e)}")
        raise

@celery_app.task(
    name='reachgenie.tasks.process_do_not_contact_csv',
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def celery_process_do_not_contact(self, *, company_id: str, file_url: str, user_id: str, task_id: str):
    """
    Celery task that processes a do-not-contact CSV file upload.
    
    Args:
        company_id: UUID string of the company
        file_url: URL of the uploaded file in storage
        user_id: UUID string of the user who initiated the upload
        task_id: UUID string of the upload task
    """
    try:
        logger.info(f"Starting do-not-contact CSV processing task for task_id: {task_id}")
        
        # Create a new event loop for all async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                _async_process_do_not_contact(
                    company_id=company_id,
                    file_url=file_url,
                    user_id=user_id,
                    task_id=task_id
                )
            )
            
            logger.info(f"Do-not-contact CSV processing completed successfully for task_id: {task_id}")
            return result
        except SoftTimeLimitExceeded:
            logger.error(f"Do-not-contact task: {task_id} reached soft timeout limit")
            raise  # Re-raise so that it can be retried up to max retries
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Error in do-not-contact CSV processing task: {task_id} - {str(exc)}")

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