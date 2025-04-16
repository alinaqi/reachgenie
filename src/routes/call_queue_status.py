from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
import logging

from src.auth import get_current_user
from src.database import (
    get_call_queue_item,
    get_campaign_by_id,
    get_companies_by_user_id,
    update_call_queue_item_status
)
from src.models import CallQueueRetryResponse

# Set up logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/call-queues",
    tags=["Campaigns & Calls"]
)

@router.post("/{queue_id}/retry", response_model=CallQueueRetryResponse)
async def retry_call_queue_item(
    queue_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Retry a call queue item by marking it as pending
    
    Args:
        queue_id: UUID of the call queue item
        current_user: Current authenticated user
        
    Returns:
        CallQueueRetryResponse with status and details
    """
    # Get the call queue item
    queue_item = await get_call_queue_item(queue_id)
    if not queue_item:
        raise HTTPException(status_code=404, detail="Call queue item not found")
    
    # Get the campaign to verify company access
    campaign = await get_campaign_by_id(queue_item['campaign_id'])
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check if user has access to the company
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(campaign["company_id"]) for company in companies):
        raise HTTPException(status_code=403, detail="Not authorized to access this call queue item")
    
    # Only allow retrying failed items
    if queue_item['status'] != 'failed':
        raise HTTPException(status_code=400, detail="Only failed call queue items can be retried")

    try:
        # Update the status to pending
        await update_call_queue_item_status(
            queue_id=queue_id,
            status='pending',
            retry_count=0
        )
        
        return CallQueueRetryResponse(
            message="Call queue item retry initiated successfully",
            queue_id=queue_id,
            status="initiated"
        )
    except Exception as e:
        logger.error(f"Error retrying call queue item {queue_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retry call queue item") 