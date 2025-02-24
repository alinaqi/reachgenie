import asyncio
import logging
from src.database import get_companies_with_email_credentials
from src.scripts.process_emails import fetch_emails

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    try:
        # Get all companies with email credentials
        companies = await get_companies_with_email_credentials()
        logger.info(f"Found {len(companies)} companies with email credentials")
        
        # Process emails for each company
        for company in companies:
            logger.info(f"Processing emails for company: {company['name']}")
            await fetch_emails(company)
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 