from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from src.auth import get_current_user
from src.database import (
    get_upload_tasks_by_company,
    get_companies_by_user_id
)
from src.models import PaginatedUploadTaskResponse

router = APIRouter()

@router.get(
    "/api/companies/{company_id}/upload-tasks",
    response_model=PaginatedUploadTaskResponse,
    tags=["Upload Tasks"]
)
async def get_company_upload_tasks(
    company_id: UUID,
    page_number: int = Query(default=1, ge=1, description="Page number to fetch"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get paginated list of upload tasks for a company.
    
    Args:
        company_id: UUID of the company
        page_number: Page number for pagination (default: 1)
        limit: Number of items per page (default: 20, max: 100)
        current_user: Current authenticated user
        
    Returns:
        Paginated list of upload tasks
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get upload tasks
    result = await get_upload_tasks_by_company(
        company_id=company_id,
        page_number=page_number,
        limit=limit
    )
    
    return result