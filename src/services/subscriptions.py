from src.config import get_settings
from typing import Optional
from fastapi import HTTPException, status
import stripe
from src.database import supabase
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Initialize settings
settings = get_settings()
stripe.api_key = settings.stripe_secret_key

async def get_price_id_for_plan(plan_type: str, lead_tier: int) -> str:
    """Get the Stripe price ID for a given plan type and lead tier"""
    price_map = {
        "fixed": {
            2500: settings.stripe_price_fixed_2500,
            5000: settings.stripe_price_fixed_5000,
            7500: settings.stripe_price_fixed_7500,
            10000: settings.stripe_price_fixed_10000
        },
        "performance": {
            2500: settings.stripe_price_performance_2500,
            5000: settings.stripe_price_performance_5000,
            7500: settings.stripe_price_performance_7500,
            10000: settings.stripe_price_performance_10000
        }
    }
    
    if plan_type not in price_map or lead_tier not in price_map[plan_type]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan type '{plan_type}' or lead tier {lead_tier}"
        )
    
    price_id = price_map[plan_type][lead_tier]
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Price ID not configured for {plan_type} plan with {lead_tier} leads"
        )
    
    return price_id

async def get_price_id_for_channel(channel: str, plan_type: str) -> Optional[str]:
    """Get the Stripe price ID for a given channel and plan type"""
    price_map = {
        "fixed": {
            "email": settings.stripe_price_email_fixed,
            "phone": settings.stripe_price_phone_fixed,
            "linkedin": settings.stripe_price_linkedin_fixed,
            "whatsapp": settings.stripe_price_whatsapp_fixed
        },
        "performance": {
            "email": settings.stripe_price_email_performance,
            "phone": settings.stripe_price_phone_performance,
            "linkedin": settings.stripe_price_linkedin_performance,
            "whatsapp": settings.stripe_price_whatsapp_performance
        }
    }
    
    if channel not in price_map[plan_type]:
        return None
    
    return price_map[plan_type][channel]

async def get_or_create_stripe_customer(user_id: str, email: str, name: str = None) -> str:
    """Get existing Stripe customer ID or create a new one"""
    try:
        # Check if user already has a Stripe customer ID
        response = supabase.table('users').select('stripe_customer_id').eq('id', user_id).execute()
        if response.data and response.data[0].get('stripe_customer_id'):
            return response.data[0]['stripe_customer_id']
        
        # Create new Stripe customer
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={
                "user_id": user_id
            }
        )
        
        # Update user record with Stripe customer ID
        supabase.table('users').update({
            'stripe_customer_id': customer.id
        }).eq('id', user_id).execute()
        
        return customer.id
        
    except Exception as e:
        logger.error(f"Error in get_or_create_stripe_customer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create Stripe customer"
        )