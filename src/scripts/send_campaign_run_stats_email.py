#!/usr/bin/env python3
import asyncio
import sys
import logging
from pathlib import Path

from src.services.campaign_stats_emailer import get_pending_campaign_schedules
from src.database import get_lead_details_for_email_interactions
from src.config import get_settings
import bugsnag
from bugsnag.handlers import BugsnagHandler

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("campaign_stats_emailer")

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
    """Main function to process campaign stats and send emails"""
    try:
        pending_schedules = await get_pending_campaign_schedules()
        logger.info(f"Found {len(pending_schedules)} pending schedules to process")
        
        for schedule in pending_schedules:
            logger.info(f"Processing schedule for campaign run: {schedule['campaign_run_id']}")
            
            leads = await get_lead_details_for_email_interactions(schedule['campaign_run_id'], schedule['data_fetch_date'])

            for lead in leads:
                print(f"Name: {lead['name']}")
                print(f"Company: {lead['company']}")
                print(f"Job Title: {lead['job_title']}")
                print();


    except Exception as e:
        logger.error(f"Error in campaign stats email processing: {str(e)}")
        bugsnag.notify(e)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error in campaign stats email processing: {str(e)}")
        bugsnag.notify(e)
        sys.exit(1)