#!/usr/bin/env python3
import asyncio
import sys
import logging

from src.services.campaign_schedule_populator import populate_campaign_schedules
from src.config import get_settings
import bugsnag
from bugsnag.handlers import BugsnagHandler

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("campaign_schedule_populator")

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
    """Main function to populate campaign schedules"""
    try:
        await populate_campaign_schedules()
    except Exception as e:
        logger.error(f"Error in campaign schedule population: {str(e)}")
        bugsnag.notify(e)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error in campaign schedule population: {str(e)}")
        bugsnag.notify(e)
        sys.exit(1) 