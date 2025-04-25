#!/usr/bin/env python3
"""
Run Scheduled Campaigns

This script checks for campaigns that are scheduled to run and haven't been auto-triggered yet.
It runs as a cron job to find campaigns where:
- current_date >= scheduled_at
- auto_run_triggered = false
- company is not deleted
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict

from src.database import supabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def get_pending_scheduled_campaigns() -> List[Dict]:
    """
    Get all campaigns that are scheduled to run and haven't been auto-triggered yet.
    Only includes campaigns from non-deleted companies.
    
    Returns:
        List of campaign dictionaries
    """
    try:
        # Get current timestamp in UTC
        current_time = datetime.now(timezone.utc)
        
        # Query for eligible campaigns
        # Join with companies table to check deleted status
        response = supabase.from_('campaigns')\
            .select('id, name, scheduled_at, companies!inner(deleted)')\
            .eq('auto_run_triggered', False)\
            .eq('companies.deleted', False)\
            .lte('scheduled_at', current_time.isoformat())\
            .execute()
            
        if not response.data:
            logger.info("No pending scheduled campaigns found")
            return []
            
        return response.data
            
    except Exception as e:
        logger.error(f"Error fetching pending scheduled campaigns: {str(e)}")
        return []

async def main():
    """Main function to check scheduled campaigns"""
    try:
        # Get pending scheduled campaigns
        campaigns = await get_pending_scheduled_campaigns()
        
        logger.info(f"Found {len(campaigns)} pending scheduled campaigns")
        
        # Log found campaigns
        for campaign in campaigns:
            logger.info(f"Found pending scheduled campaign - ID: {campaign['id']}, Name: {campaign['name']}, Scheduled At: {campaign['scheduled_at']}")

    except Exception as e:
        logger.error(f"Error in scheduled campaigns check: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 