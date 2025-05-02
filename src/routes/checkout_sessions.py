from fastapi import APIRouter, HTTPException, status
from src.config import get_settings
import stripe
import logging
from src.database import supabase
from typing import Dict, Any

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/fulfill_checkout", tags=["Checkout Sessions"])

# Initialize settings
settings = get_settings()
stripe.api_key = settings.stripe_secret_key

@router.get("/{session_id}", response_model=Dict[str, Any])
async def fulfill_checkout_session(session_id: str):
    """
    Fulfill a Stripe Checkout Session
    """
    try:
        session = await fulfill_checkout(session_id)
        
        logger.info(f"Retrieved checkout session: {session}")
        
        return {
            "status": "success",
            "message": "Checkout session retrieved and fulfilled successfully"
        }

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error in get_checkout_session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in get_checkout_session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve checkout session"
        ) 
    
async def fulfill_checkout(session_id: str):
    """
    Fulfill a Stripe Checkout Session
    """
    checkout_session = stripe.checkout.Session.retrieve(session_id)

    # Check the Checkout Session's payment_status property to determine if fulfillment should be performed
    if checkout_session.payment_status == "paid":
        try:
            # Extract metadata from the session
            metadata = checkout_session.metadata
            user_id = metadata.get("user_id")
            plan_type = metadata.get("plan_type")
            lead_tier = int(metadata.get("lead_tier"))
            active_channels = metadata.get("channels", "").split(",")
            
            # Format channels as JSON object with boolean values
            channels_active = {
                "email": "email" in active_channels,
                "phone": "phone" in active_channels,
                "whatsapp": "whatsapp" in active_channels,
                "linkedin": "linkedin" in active_channels
            }
            
            # Get subscription ID from the session
            subscription_id = checkout_session.subscription
            
            # Update user record in the database
            update_data = {
                "plan_type": plan_type,
                "lead_tier": lead_tier,
                "channels_active": channels_active,
                "subscription_id": subscription_id
            }
            
            response = supabase.table("users").update(update_data).eq("id", user_id).execute()
            
            if not response.data:
                logger.error(f"Failed to update user {user_id} with subscription details")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update user subscription details"
                )
                
            logger.info(f"Successfully updated subscription details for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error fulfilling checkout: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fulfill checkout session"
            )
    
    return checkout_session