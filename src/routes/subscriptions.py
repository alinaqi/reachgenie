from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import stripe
from src.config import get_settings
from src.auth import get_current_user
import logging
from src.services.subscriptions import get_or_create_stripe_customer, get_price_id_for_plan, get_price_id_for_channel

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/subscriptions", tags=["Subscriptions"])

# Initialize settings
settings = get_settings()
stripe.api_key = settings.stripe_secret_key

class Channel(BaseModel):
    email: bool = False
    phone: bool = False
    whatsapp: bool = False
    linkedin: bool = False

class CreateSubscriptionRequest(BaseModel):
    plan_type: str  # 'fixed' or 'performance'
    lead_tier: int  # 2500, 5000, 7500, or 10000
    channels: Channel

@router.post("/", response_model=dict)
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a subscription for the current user
    
    This endpoint:
    1. Validates the requested plan and channels
    2. Creates or retrieves Stripe customer
    3. Creates a Stripe checkout session
    4. Returns the session URL
    """
    try:
        # Validate plan type
        if request.plan_type not in ["fixed", "performance"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid plan type. Must be 'fixed' or 'performance'"
            )
        
        # Validate lead tier
        if request.lead_tier not in [2500, 5000, 7500, 10000]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid lead tier. Must be 2500, 5000, 7500, or 10000"
            )
        
        # Get or create Stripe customer
        customer_id = await get_or_create_stripe_customer(
            current_user["id"],
            current_user["email"],
            current_user["name"]
        )
        
        # Get price ID for the base plan
        base_price_id = await get_price_id_for_plan(request.plan_type, request.lead_tier)
        
        # Prepare line items starting with base plan
        line_items = [{
            "price": base_price_id,
            "quantity": 1
        }]
        
        # Add selected channels
        channels_dict = request.channels.dict()
        for channel, is_selected in channels_dict.items():
            if is_selected:
                channel_price_id = await get_price_id_for_channel(channel, request.plan_type)
                if channel_price_id:
                    line_items.append({
                        "price": channel_price_id,
                        "quantity": 1
                    })
        
        # Create Stripe checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=line_items,
            success_url=f"{settings.frontend_url}/subscription/success",
            cancel_url=f"{settings.frontend_url}/subscription/cancel",
            metadata={
                "user_id": current_user["id"],
                "plan_type": request.plan_type,
                "lead_tier": str(request.lead_tier),
                "channels": ",".join([k for k, v in channels_dict.items() if v])
            }
        )
        
        return {
            "session_id": session.id,
            "session_url": session.url,
            "subscription_id": session.subscription
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error in create_subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in create_subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription"
        ) 