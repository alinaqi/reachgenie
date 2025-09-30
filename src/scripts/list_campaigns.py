#!/usr/bin/env python3
"""
List Campaigns

This script lists all campaigns in the database to help find valid campaign IDs.
"""
import asyncio
import logging
from uuid import UUID

from src.database import get_campaigns_by_company, get_companies_with_email_credentials

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def list_all_campaigns():
    """List all campaigns in the database"""
    
    try:
        # Get all companies with email credentials
        companies = await get_companies_with_email_credentials()
        
        if not companies:
            logger.info("No companies found with email credentials")
            return
            
        # Track total campaigns found
        total_campaigns = 0
        
        # Iterate through companies and list their campaigns
        for company in companies:
            company_id = UUID(company['id'])
            company_name = company.get('name', 'Unknown Company')
            
            logger.info(f"\nCompany: {company_name} ({company_id})")
            
            # Get campaigns for this company
            campaigns = await get_campaigns_by_company(company_id)
            
            if not campaigns:
                logger.info(f"  No campaigns found for {company_name}")
                continue
                
            # Display campaign details
            logger.info(f"  Found {len(campaigns)} campaigns:")
            for campaign in campaigns:
                campaign_id = campaign.get('id', 'Unknown ID')
                campaign_name = campaign.get('name', 'Unnamed Campaign')
                campaign_type = campaign.get('type', 'unknown')
                
                logger.info(f"  - {campaign_name} ({campaign_id}) - Type: {campaign_type}")
                total_campaigns += 1
                
        logger.info(f"\nTotal campaigns found: {total_campaigns}")
        
    except Exception as e:
        logger.error(f"Error listing campaigns: {str(e)}")

if __name__ == "__main__":
    asyncio.run(list_all_campaigns()) 