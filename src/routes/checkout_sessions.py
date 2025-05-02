from fastapi import APIRouter, HTTPException, status
from src.config import get_settings
import stripe
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/checkout-sessions", tags=["Checkout Sessions"])

# Initialize settings
settings = get_settings()
stripe.api_key = settings.stripe_secret_key

@router.get("/{session_id}")
async def get_checkout_session(session_id: str):
    """
    Retrieve a Stripe Checkout Session by its ID
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
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