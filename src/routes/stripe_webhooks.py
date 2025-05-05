from fastapi import APIRouter, Request, HTTPException, status
from src.config import get_settings
from src.routes.checkout_sessions import fulfill_checkout
import stripe
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/stripe", tags=["Stripe Webhooks"])

# Initialize settings
settings = get_settings()
stripe.api_key = settings.stripe_secret_key

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events
    
    Currently handling:
    - checkout.session.async_payment_succeeded
    - checkout.session.completed
    """
    # Get the raw request body for signature verification
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.stripe_webhook_secret
        )
        
        # Handle specific events
        if event.type in ["checkout.session.async_payment_succeeded", "checkout.session.completed"]:
            session = event.data.object
            session_response = await fulfill_checkout(session.id)

            logger.info(f"Retrieved checkout session from webhook: {session_response}")
            
        return {"status": "success"}
        
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature in Stripe webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 