import asyncio
from uuid import UUID

from src.database import update_company_account_credentials, get_company_by_id

async def run():
    # Company ID
    company_id = UUID('a7e85ef3-388a-44c0-988b-c848336e02aa')
    
    # Get current company details
    company = await get_company_by_id(company_id)
    print(f"Current company details: {company}")
    
    # Set up test email credentials
    account_email = "test@example.com"
    account_password = "test_password"  # This will be encrypted
    account_type = "smtp"  # Assuming SMTP is a valid type
    
    print(f"Setting up email credentials for company: {company.get('name', company_id)}")
    
    # Update company with credentials
    updated_company = await update_company_account_credentials(
        company_id=company_id,
        account_email=account_email,
        account_password=account_password,
        account_type=account_type
    )
    
    print(f"Company credentials updated: {updated_company is not None}")
    
    # Verify update
    company_after = await get_company_by_id(company_id)
    print(f"Company now has email: {company_after.get('account_email')}")
    print(f"Company now has account type: {company_after.get('account_type')}")
    print(f"Company now has password set: {bool(company_after.get('account_password'))}")

if __name__ == "__main__":
    asyncio.run(run()) 