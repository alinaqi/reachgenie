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

from src.database import (
    get_pending_scheduled_campaigns,
    create_campaign_run,
    mark_campaign_as_triggered,
    get_campaign_lead_count,
    has_pending_upload_tasks,
    get_active_campaign_runs_count
)
from src.celery_app.tasks.run_campaign import celery_run_company_campaign

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
    Reuses existing campaign running logic from the API endpoint.
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
                campaign_id = UUID(campaign['id'])
                company_id = UUID(campaign['company_id'])
                
                try:
                    # Check for active runs first
                    active_runs_count = await get_active_campaign_runs_count(campaign_id)
                    if active_runs_count > 0:
                        logger.info(
                            f"Skipping scheduled campaign {campaign['name']} ({campaign_id}). "
                            "Campaign is already in running state."
                        )
                        continue

                    # Check for pending upload tasks
                    if await has_pending_upload_tasks(company_id):
                        logger.info(
                            f"Skipping scheduled campaign {campaign_id} for company {company_id}. "
                            "There are leads being processed from recent file uploads."
                        )
                        continue
                    
                    logger.info(
                        f"\nProcessing scheduled campaign - "
                        f"ID: {campaign_id}, "
                        f"Campaign Name: {campaign['name']}, "
                        f"Company Name: {campaign['companies']['name']}, "
                        f"Scheduled At: {campaign['scheduled_at']}"
                    )
                    
                    # Get total leads count
                    lead_count = await get_campaign_lead_count(campaign)
                    
                    # Create campaign run record
                    campaign_run = await create_campaign_run(
                        campaign_id=campaign_id,
                        status="idle",
                        leads_total=lead_count
                    )
                    
                    if not campaign_run:
                        logger.error(f"Failed to create campaign run for campaign {campaign_id}")
                        continue
                        
                    campaign_run_id = UUID(campaign_run['id'])
                    logger.info(f"Created campaign run {campaign_run_id} with {lead_count} leads")
                    
                    # Queue the campaign using Celery task
                    celery_run_company_campaign.delay(
                        str(campaign_id),
                        str(campaign_run_id)
                    )
                    logger.info(f"Queued campaign {campaign_id} for processing with run ID {campaign_run_id}")
                    
                    # Mark campaign as auto-triggered
                    if await mark_campaign_as_triggered(campaign_id):
                        logger.info(f"Successfully marked campaign {campaign_id} as triggered")
                    else:
                        logger.error(f"Failed to mark campaign {campaign_id} as triggered")
                    
                    total_campaigns += 1
                    
                except Exception as e:
                    logger.error(f"Error processing campaign {campaign_id}: {str(e)}")
                    continue
                
            # Update last_id for next batch
            last_id = UUID(campaigns[-1]['id'])
            
        logger.info(f"Completed processing {total_campaigns} scheduled campaigns")
            
    except Exception as e:
        logger.error(f"Error in scheduled campaigns check: {str(e)}")

if __name__ == "__main__":
    asyncio.run(process_scheduled_campaigns()) 