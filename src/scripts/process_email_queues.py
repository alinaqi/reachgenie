#!/usr/bin/env python3
import asyncio
import sys
import os
import logging
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.services.email_queue_processor import process_email_queues
from src.config import get_settings
import bugsnag
from bugsnag.handlers import BugsnagHandler

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("email_queue_processor")

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
    """Main function to process email queues"""
    try:
        logger.info("Starting email queue processing")
        await process_email_queues()
    except Exception as e:
        logger.error(f"Error in email queue processing: {str(e)}")
        bugsnag.notify(e)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error in email queue processing: {str(e)}")
        bugsnag.notify(e)
        sys.exit(1) 