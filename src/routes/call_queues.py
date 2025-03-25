from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from uuid import UUID
import logging

from src.models import PaginatedCallQueueResponse
from src.database import (
    get_call_queues_by_campaign_run,
    get_campaign_run,
    get_campaign_by_id,
    get_companies_by_user_id
)
from src.auth import get_current_user

# Set up logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/campaigns",
    tags=["Campaigns & Calls"]
)

@router.get("/{campaign_run_id}/call-queues", response_model=PaginatedCallQueueResponse)
async def get_campaign_run_call_queues(
    campaign_run_id: UUID,
    page_number: int = Query(default=1, ge=1, description="Page number to fetch"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get paginated list of call queues for a specific campaign run
    
    Args:
        campaign_run_id: UUID of the campaign run
        page_number: Page number to fetch (default: 1)
        limit: Number of items per page (default: 20)
        current_user: Current authenticated user
        
    Returns:
        Paginated list of call queues
    """
    # Get the campaign run to verify access
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
    
    # Get paginated call queues
    return await get_call_queues_by_campaign_run(
        campaign_run_id=campaign_run_id,
        page_number=page_number,
        limit=limit
    ) 