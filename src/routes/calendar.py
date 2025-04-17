from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from pydantic import BaseModel
from src.auth import get_current_user
from src.database import get_user_company_profile, get_company_by_id, update_company_custom_calendar

# Create router
calendar_router = APIRouter(
    prefix="/api/companies",
    tags=["Calendar"]
)

class CustomCalendarUpdate(BaseModel):
    custom_calendar_link: str

@calendar_router.put("/{company_id}/custom_calendar", response_model=dict)
async def update_custom_calendar(
    company_id: UUID,
    calendar_data: CustomCalendarUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update custom calendar link for a company
    """
    # Validate company access
    user_company_profile = await get_user_company_profile(current_user['id'], company_id)
    if not user_company_profile:
        raise HTTPException(status_code=403, detail="You don't have access to this company")
    
    # Get company to verify it exists
    company = await get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Update the custom calendar link
    updated_company = await update_company_custom_calendar(company_id, calendar_data.custom_calendar_link)
    
    if not updated_company:
        raise HTTPException(status_code=500, detail="Failed to update custom calendar link")
    
    return {"success": True, "message": "Custom calendar link updated successfully"} 