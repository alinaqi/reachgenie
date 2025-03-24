#!/usr/bin/env python3
import asyncio
import sys
import logging
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.services.call_queue_processor import process_call_queues
from src.config import get_settings
import bugsnag
from bugsnag.handlers import BugsnagHandler

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("call_queue_processor")

# Configure Bugsnag
settings = get_settings()
bugsnag.configure(
    api_key=settings.bugsnag_api_key,
    release_stage=settings.environment,
)

handler = BugsnagHandler()
handler.setLevel(logging.ERROR)
logger.addHandler(handler)

async def main():
    """Main function to process call queues"""
    try:
        logger.info("Starting call queue processing")
        await process_call_queues()
        logger.info("Call queue processing completed")
    except Exception as e:
        logger.error(f"Error in call queue processing: {str(e)}")
        bugsnag.notify(e)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error in call queue processing: {str(e)}")
        bugsnag.notify(e)
        sys.exit(1)