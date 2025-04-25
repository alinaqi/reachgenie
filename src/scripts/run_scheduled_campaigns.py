#!/usr/bin/env python3
"""
Run Scheduled Campaigns

This script checks for campaigns that are scheduled to run and haven't been auto-triggered yet.
Uses keyset pagination to efficiently process large numbers of campaigns.
"""
import asyncio
import logging
from uuid import UUID
from typing import Optional

from src.database import get_pending_scheduled_campaigns

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
BATCH_SIZE = 50  # Number of campaigns to process in each batch

async def process_scheduled_campaigns():
    """
    Process all scheduled campaigns using keyset pagination.
    """
    try:
        total_campaigns = 0
        last_id: Optional[UUID] = None
        
        while True:
            # Get batch of campaigns
            campaigns = await get_pending_scheduled_campaigns(last_id=last_id, limit=BATCH_SIZE)
            
            # Break if no more campaigns
            if not campaigns:
                break
                
            # Process each campaign in the batch
            for campaign in campaigns:
                logger.info(
                    f"\n Found pending scheduled campaign - "
                    f"ID: {campaign['id']}, \n "
                    f"Name: {campaign['name']}, \n "
                    f"Company: {campaign['companies']['name']}, \n "
                    f"Scheduled At: {campaign['scheduled_at']} \n "
                )
                total_campaigns += 1
                
            # Update last_id for next batch
            last_id = UUID(campaigns[-1]['id'])
            
        logger.info(f"Completed processing {total_campaigns} scheduled campaigns")
            
    except Exception as e:
        logger.error(f"Error in scheduled campaigns check: {str(e)}")

if __name__ == "__main__":
    asyncio.run(process_scheduled_campaigns()) 