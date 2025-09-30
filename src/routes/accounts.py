from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from src.models import AccountEmailCheckResponse
from src.database import (
    get_companies_by_user_id,
    check_account_email_exists_in_other_companies
)
from src.auth import get_current_user

# Create router
accounts_router = APIRouter(
    prefix="/api/companies",
    tags=["Accounts"]
)

@accounts_router.get(
    "/{company_id}/accounts/{account_email}/check-duplicate",
    response_model=AccountEmailCheckResponse
)
async def check_duplicate_account_email(
    company_id: UUID,
    account_email: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Check if the given account_email exists in other non-deleted companies for the current user
    
    Args:
        company_id: UUID of the company
        account_email: Email address to check
        current_user: Current authenticated user
        
    Returns:
        AccountEmailCheckResponse indicating if email exists in other companies
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check if email exists in other companies
    exists = await check_account_email_exists_in_other_companies(
        company_id=company_id,
        account_email=account_email,
        user_id=UUID(current_user["id"])
    )
    
    return AccountEmailCheckResponse(
        exists=exists,
        message="Account email already exists in another company" if exists else "Account email is available"
    ) 