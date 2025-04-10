from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from uuid import UUID
import logging

from src.auth import get_current_user
from src.database import (
    get_campaign_run,
    get_campaign_by_id,
    get_companies_by_user_id,
    update_queue_item_status,
    update_call_queue_item_status,
    update_campaign_run_status
)
from src.models import CampaignRetryResponse

# Set up logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/campaign-runs",
    tags=["Campaigns & Emails"]
)

@router.post("/{campaign_run_id}/retry", response_model=CampaignRetryResponse)
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
        CampaignRetryResponse with status and details
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
    
    return CampaignRetryResponse(
        message="Campaign retry initiated successfully",
        campaign_run_id=campaign_run_id,
        status="initiated"
    )

@router.post("/{campaign_run_id}/retry/call", response_model=CampaignRetryResponse)
async def retry_failed_campaign_calls(
    campaign_run_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Retry failed calls for a specific campaign run.
    
    Args:
        campaign_run_id: UUID of the campaign run
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user
        
    Returns:
        CampaignRetryResponse with status and details
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
    background_tasks.add_task(retry_failed_calls, campaign_run_id)
    
    return CampaignRetryResponse(
        message="Campaign call retry initiated successfully",
        campaign_run_id=campaign_run_id,
        status="initiated"
    )

async def retry_failed_emails(campaign_run_id: UUID, batch_size: int = 500):
    """
    Background task to retry failed emails for a campaign run using keyset pagination.
    Processes emails in batches to avoid memory issues with large campaigns.
    
    Args:
        campaign_run_id: UUID of the campaign run
        batch_size: Number of emails to process in each batch
    """
    try:
        from src.database import supabase  # Import here to avoid circular imports

        # Update campaign run status to running
        await update_campaign_run_status(
            campaign_run_id=campaign_run_id,
            status="running"
        )
        logger.info(f"Updated campaign run {campaign_run_id} status to running")

        last_seen_id = None
        while True:
            # Build base query
            query = supabase.table('email_queue')\
                .select('id')\
                .eq('campaign_run_id', str(campaign_run_id))\
                .eq('status', 'failed')\
                .order('id')\
                .limit(batch_size)
            
            # Add keyset condition if we have a last_seen_id
            if last_seen_id:
                query = query.gt('id', str(last_seen_id))
                
            response = query.execute()
            
            if not response.data:
                break  # No more failed emails to process
                
            # Update status of each email in the batch
            for email in response.data:
                try:
                    await update_queue_item_status(
                        queue_id=UUID(email['id']),
                        status='pending',
                        retry_count=0
                    )
                    logger.info(f"Reset status to pending for email queue item {email['id']}")
                except Exception as e:
                    logger.error(f"Failed to update status for email queue item {email['id']}: {str(e)}")
            
            # Update last_seen_id for next iteration
            last_seen_id = response.data[-1]['id']
            
        logger.info(f"Completed retrying failed emails for campaign run {campaign_run_id}")
        
    except Exception as e:
        logger.error(f"Error retrying failed emails for campaign run {campaign_run_id}: {str(e)}")

async def retry_failed_calls(campaign_run_id: UUID, batch_size: int = 500):
    """
    Background task to retry failed calls for a campaign run using keyset pagination.
    Processes calls in batches to avoid memory issues with large campaigns.
    
    Args:
        campaign_run_id: UUID of the campaign run
        batch_size: Number of calls to process in each batch
    """
    try:
        from src.database import supabase  # Import here to avoid circular imports
        
        # Update campaign run status to running
        await update_campaign_run_status(
            campaign_run_id=campaign_run_id,
            status="running"
        )
        logger.info(f"Updated campaign run {campaign_run_id} status to running")

        last_seen_id = None
        while True:
            # Build base query
            query = supabase.table('call_queue')\
                .select('id')\
                .eq('campaign_run_id', str(campaign_run_id))\
                .eq('status', 'failed')\
                .order('id')\
                .limit(batch_size)
            
            # Add keyset condition if we have a last_seen_id
            if last_seen_id:
                query = query.gt('id', str(last_seen_id))
                
            response = query.execute()
            
            if not response.data:
                break  # No more failed calls to process
                
            # Update status of each call in the batch
            for call in response.data:
                try:
                    await update_call_queue_item_status(
                        queue_id=UUID(call['id']),
                        status='pending',
                        retry_count=0
                    )
                    logger.info(f"Reset status to pending for call queue item {call['id']}")
                except Exception as e:
                    logger.error(f"Failed to update status for call queue item {call['id']}: {str(e)}")
            
            # Update last_seen_id for next iteration
            last_seen_id = response.data[-1]['id']
            
        logger.info(f"Completed retrying failed calls for campaign run {campaign_run_id}")
        
    except Exception as e:
        logger.error(f"Error retrying failed calls for campaign run {campaign_run_id}: {str(e)}") 