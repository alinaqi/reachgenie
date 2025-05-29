import asyncio
from uuid import UUID
import logging
from ..config import celery_app
from src.database import process_do_not_email_csv_upload, init_pg_pool
import src.database

logger = logging.getLogger(__name__)

async def _async_process_do_not_contact(company_id: str, file_url: str, user_id: str, task_id: str):
    # Force a clean start to avoid inherited pool across fork
    global pg_pool
    await init_pg_pool(force_reinit=True)
    
    try:
        return await process_do_not_email_csv_upload(
            company_id=UUID(company_id),
            file_url=file_url,
            user_id=UUID(user_id),
            task_id=UUID(task_id)
        )
    finally:
        if src.database.pg_pool:
            await src.database.pg_pool.close()
            src.database.pg_pool = None

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
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Error in do-not-contact CSV processing task: {str(exc)}")
        raise self.retry(exc=exc) 