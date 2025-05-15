from fastapi import APIRouter, Depends, Query
from uuid import UUID
from src.auth import get_current_user
from src.database import (
    get_skipped_leads_by_task
)
from src.models import PaginatedSkippedLeadResponse

router = APIRouter()

@router.get(
    "/api/upload-tasks/{upload_task_id}/skipped-leads",
    response_model=PaginatedSkippedLeadResponse,
    tags=["Upload Tasks"]
)
async def get_task_skipped_leads(
    upload_task_id: UUID,
    page_number: int = Query(default=1, ge=1, description="Page number to fetch"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get paginated list of skipped leads for a specific upload task.
    
    Args:
        upload_task_id: UUID of the upload task
        page_number: Page number to fetch (default: 1)
        limit: Number of items per page (default: 20)
        current_user: Current authenticated user
        
    Returns:
        Paginated list of skipped leads
    """    
    # Get paginated skipped leads
    return await get_skipped_leads_by_task(
        upload_task_id=upload_task_id,
        page_number=page_number,
        limit=limit
    ) 