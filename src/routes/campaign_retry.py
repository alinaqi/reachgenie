from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict
from uuid import UUID
import logging
from datetime import datetime, timezone

from src.auth import get_current_user
from src.database import (
    get_campaign_run,
    get_campaign_by_id,
    get_companies_by_user_id,
    update_queue_item_status
)

# Set up logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/campaign-runs",
    tags=["Campaigns & Emails"]
)

@router.post("/{campaign_run_id}/retry", response_model=Dict[str, str])
async def retry_failed_campaign_emails(
    campaign_run_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Retry failed emails for a specific campaign run.
    
    Args:
        campaign_run_id: UUID of the campaign run
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user
        
    Returns:
        Dict with success message
    """
    # Get the campaign run to verify it exists
    campaign_run = await get_campaign_run(campaign_run_id)
    if not campaign_run:
        raise HTTPException(status_code=404, detail="Campaign run not found")
    
    # Get the campaign to verify company access
    campaign = await get_campaign_by_id(campaign_run['campaign_id'])
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check if user has access to the company
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(campaign["company_id"]) for company in companies):
        raise HTTPException(status_code=403, detail="Not authorized to access this campaign")
    
    # Add the retry task to background tasks
    background_tasks.add_task(retry_failed_emails, campaign_run_id)
    
    return {"message": "Campaign retry initiated successfully"}

async def retry_failed_emails(campaign_run_id: UUID, batch_size: int = 50):
    """
    Background task to retry failed emails for a campaign run.
    Processes emails in batches to avoid memory issues with large campaigns.
    
    Args:
        campaign_run_id: UUID of the campaign run
        batch_size: Number of emails to process in each batch
    """
    try:
        from src.database import supabase  # Import here to avoid circular imports
        
        offset = 0
        while True:
            # Get a batch of failed emails
            response = supabase.table('email_queue')\
                .select('id')\
                .eq('campaign_run_id', str(campaign_run_id))\
                .eq('status', 'failed')\
                .range(offset, offset + batch_size - 1)\
                .execute()
            
            if not response.data:
                break  # No more failed emails to process
                
            # Update status of each email in the batch
            for email in response.data:
                try:
                    await update_queue_item_status(
                        queue_id=UUID(email['id']),
                        status='pending'
                    )
                    logger.info(f"Reset status to pending for email queue item {email['id']}")
                except Exception as e:
                    logger.error(f"Failed to update status for email queue item {email['id']}: {str(e)}")
            
            offset += batch_size
            
        logger.info(f"Completed retrying failed emails for campaign run {campaign_run_id}")
        
    except Exception as e:
        logger.error(f"Error retrying failed emails for campaign run {campaign_run_id}: {str(e)}") 