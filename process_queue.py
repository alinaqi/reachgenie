import asyncio
import logging
from src.services.email_queue_processor import process_email_queues

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("queue_processor_test")

async def run():
    logger.info("Starting email queue processing test")
    
    try:
        # Process all queued emails
        await process_email_queues()
        logger.info("Email queue processing completed")
    except Exception as e:
        logger.error(f"Error processing email queue: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run()) 