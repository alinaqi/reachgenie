from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from pydantic import BaseModel
from typing import Optional

from src.auth import get_current_user
from src.database import (
    get_user_company_profile,
    get_company_by_id,
    update_company_details
)

# Create router
companies_router = APIRouter(
    prefix="/api/companies",
    tags=["Companies"]
)

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    industry: Optional[str] = None
    overview: Optional[str] = None
    background: Optional[str] = None
    products_services: Optional[str] = None

@companies_router.patch("/{company_id}", response_model=dict)
async def update_company(
    company_id: UUID,
    company_data: CompanyUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update company information.
    Only company administrators can update company details.
    
    Args:
        company_id: UUID of the company
        company_data: Updated company information
        current_user: Current authenticated user
        
    Returns:
        Updated company details
        
    Raises:
        404: Company not found
        403: User doesn't have access to this company or is not an admin
    """
    # Validate company access and admin role
    user_profile = await get_user_company_profile(current_user['id'], company_id)
    if not user_profile:
        raise HTTPException(status_code=403, detail="You don't have access to this company")
    
    if user_profile["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only company administrators can update company details"
        )
    
    # Get company to verify it exists
    company = await get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Update company details
    update_data = company_data.model_dump(exclude_unset=True)
    updated_company = await update_company_details(company_id, update_data)
    
    if not updated_company:
        raise HTTPException(status_code=500, detail="Failed to update company details")
    
    return updated_company 