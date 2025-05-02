from fastapi import APIRouter, HTTPException, status
from src.config import get_settings
import stripe
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/fulfill_checkout", tags=["Checkout Sessions"])

# Initialize settings
settings = get_settings()
stripe.api_key = settings.stripe_secret_key

@router.get("/{session_id}")
async def fulfill_checkout_session(session_id: str):
    """
    Fulfill a Stripe Checkout Session
    """
    try:
        session = await fulfill_checkout(session_id)
        
        logger.info(f"Retrieved checkout session: {session}")
        
        return session

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
        # Fulfill the order
        pass