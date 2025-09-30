import asyncio
import uuid
from uuid import UUID

from src.main import run_company_campaign
from src.database import create_campaign_run, get_campaign_by_id, get_company_by_id

async def run():
    # Campaign and company IDs
    campaign_id = UUID('ba582e0d-e7fe-4fa0-951d-0f0bd43c0a1f')
    company_id = UUID('a7e85ef3-388a-44c0-988b-c848336e02aa')
    
    # Create a new campaign run
    campaign_run_id = uuid.uuid4()
    print(f'Created campaign run ID: {campaign_run_id}')
    
    # Get campaign and company details for logging
    campaign = await get_campaign_by_id(campaign_id)
    company = await get_company_by_id(company_id)
    
    print(f"Running campaign: {campaign.get('name', campaign_id)}")
    print(f"For company: {company.get('name', company_id)}")
    
    # Create campaign run in the database
    print("Creating campaign run record...")
    campaign_run = await create_campaign_run(
        campaign_id=campaign_id,
        status="idle",
        leads_total=0,
        leads_processed=0
    )
    
    if not campaign_run:
        print("Failed to create campaign run record. Aborting.")
        return
        
    # Use the ID from the created record
    campaign_run_id = UUID(campaign_run['id'])
    print(f"Successfully created campaign run with ID: {campaign_run_id}")
    
    # Run the campaign, which should queue emails instead of sending
    print("Starting campaign execution...")
    await run_company_campaign(campaign_id, campaign_run_id)
    
    print("Campaign execution initiated. Emails should be queued now.")
    print("To check the queue, query the email_queue table in the database.")

if __name__ == "__main__":
    asyncio.run(run()) 