from fastapi import APIRouter, Request, HTTPException, status
from src.config import get_settings
from src.routes.checkout_sessions import fulfill_checkout
import stripe
import logging
from src.database import supabase

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/stripe", tags=["Stripe Webhooks"])

# Initialize settings
settings = get_settings()
stripe.api_key = settings.stripe_secret_key

async def update_subscription_status(subscription: stripe.Subscription):
    """
    Update user's subscription status in the database
    """
    try:
        # Get the customer ID from the subscription
        customer_id = subscription.customer
        
        # Find user with this stripe customer ID
        response = supabase.table("users").select("id").eq("stripe_customer_id", customer_id).execute()
        
        if not response.data:
            logger.error(f"No user found with stripe customer ID: {customer_id}")
            return
            
        # Update the user's subscription status
        supabase.table("users").update({
            "subscription_status": subscription.status
        }).eq("stripe_customer_id", customer_id).execute()
        
        logger.info(f"Updated subscription status to {subscription.status} for customer {customer_id}")
        
    except Exception as e:
        logger.error(f"Error updating subscription status: {str(e)}")
        raise

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events
    
    Currently handling:
    - checkout.session.async_payment_succeeded
    - checkout.session.completed
    - customer.subscription.updated
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
        elif event.type in ["customer.subscription.updated", "customer.subscription.deleted", "customer.subscription.created"]:
            subscription = event.data.object
            await update_subscription_status(subscription)
            
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