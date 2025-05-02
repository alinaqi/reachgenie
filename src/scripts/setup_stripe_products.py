#!/usr/bin/env python3
"""
Script to set up Stripe products and prices for ReachGenie.
This script will:
1. Create all necessary products in Stripe
2. Create all price points for each product
3. Print all price IDs for manual use
"""
import asyncio
import sys
import logging
from pathlib import Path
from typing import Dict

from src.services.stripe_service import stripe_service
from src.config import get_settings
import bugsnag
from bugsnag.handlers import BugsnagHandler

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("stripe_setup")

# Configure Bugsnag
settings = get_settings()
bugsnag.configure(
    api_key=settings.bugsnag_api_key,
    release_stage=settings.environment,
)

handler = BugsnagHandler()
handler.setLevel(logging.ERROR)
logger.addHandler(handler)

def print_price_ids(price_ids: Dict[str, str]):
    """
    Print price IDs in a clear format for copying
    
    Args:
        price_ids: Dictionary of price IDs from Stripe
    """
    print("\n=== Stripe Price IDs ===\n")
    print("# Fixed Plan Prices")
    print(f"STRIPE_PRICE_FIXED_2500={price_ids.get('fixed_2500', '')}")
    print(f"STRIPE_PRICE_FIXED_5000={price_ids.get('fixed_5000', '')}")
    print(f"STRIPE_PRICE_FIXED_7500={price_ids.get('fixed_7500', '')}")
    print(f"STRIPE_PRICE_FIXED_10000={price_ids.get('fixed_10000', '')}")
    
    print("\n# Performance Plan Prices")
    print(f"STRIPE_PRICE_PERFORMANCE_2500={price_ids.get('performance_2500', '')}")
    print(f"STRIPE_PRICE_PERFORMANCE_5000={price_ids.get('performance_5000', '')}")
    print(f"STRIPE_PRICE_PERFORMANCE_7500={price_ids.get('performance_7500', '')}")
    print(f"STRIPE_PRICE_PERFORMANCE_10000={price_ids.get('performance_10000', '')}")
    
    print("\n# Channel Prices - Fixed Plan")
    print(f"STRIPE_PRICE_EMAIL_FIXED={price_ids.get('email_fixed', '')}")
    print(f"STRIPE_PRICE_PHONE_FIXED={price_ids.get('phone_fixed', '')}")
    print(f"STRIPE_PRICE_LINKEDIN_FIXED={price_ids.get('linkedin_fixed', '')}")
    print(f"STRIPE_PRICE_WHATSAPP_FIXED={price_ids.get('whatsapp_fixed', '')}")
    
    print("\n# Channel Prices - Performance Plan")
    print(f"STRIPE_PRICE_EMAIL_PERFORMANCE={price_ids.get('email_performance', '')}")
    print(f"STRIPE_PRICE_PHONE_PERFORMANCE={price_ids.get('phone_performance', '')}")
    print(f"STRIPE_PRICE_LINKEDIN_PERFORMANCE={price_ids.get('linkedin_performance', '')}")
    print(f"STRIPE_PRICE_WHATSAPP_PERFORMANCE={price_ids.get('whatsapp_performance', '')}")
    
    print("\nCopy these price IDs and use them where needed.")

async def main():
    """Main function to set up Stripe products and prices"""
    try:
        # Check if Stripe API key is configured
        if not settings.stripe_secret_key:
            logger.error("STRIPE_SECRET_KEY not set in environment variables")
            sys.exit(1)
        
        logger.info("Starting Stripe product and price setup...")
        
        # Create all products and prices
        price_ids = await stripe_service.create_all_products_and_prices()
        
        # Print price IDs in a clear format
        print_price_ids(price_ids)
        
        logger.info("Stripe products and prices setup completed successfully")
        
    except Exception as e:
        logger.error(f"Error in Stripe setup: {str(e)}")
        bugsnag.notify(e)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())