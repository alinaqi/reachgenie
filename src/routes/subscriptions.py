from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import stripe
from src.config import get_settings
from src.auth import get_current_user
import logging
from src.services.subscriptions import get_or_create_stripe_customer, get_price_id_for_plan, get_price_id_for_channel
from datetime import datetime
from src.database import get_user_by_id, update_user_subscription_cancellation
from typing import Optional
from src.services.stripe_service import StripeService

# Configure logger
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api", tags=["Subscriptions"])

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

class CreateSubscriptionResponse(BaseModel):
    session_id: str
    session_url: str

class ChangeSubscriptionRequest(BaseModel):
    plan_type: Optional[str]  # fixed or performance
    lead_tier: Optional[int]  # 2500, 5000, 7500, or 10000
    channels: Optional[Channel]

class ChangeSubscriptionResponse(BaseModel):
    subscription_id: str

@router.post("/subscriptions", response_model=CreateSubscriptionResponse)
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
        
        # Add performance meetings price for usage based on meetings booked
        if request.plan_type == "performance" and settings.stripe_price_performance_meetings:
            line_items.append({
                "price": settings.stripe_price_performance_meetings
            })
        
        # Create Stripe checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=line_items,
            success_url=f"{settings.frontend_url}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
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
            "session_url": session.url
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error in create_subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException as e:
        logger.error(f"Error in create_subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e.detail)
        )

@router.post("/subscriptions/cancel", response_model=dict)
async def cancel_subscription(
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel the current user's subscription immediately with a prorated refund
    
    This endpoint:
    1. Retrieves the user's active subscription
    2. Cancels it immediately in Stripe with a prorated refund
    3. Updates the user's subscription status
    """
    try:
        # Get user details including subscription ID
        user = await get_user_by_id(current_user["id"])
        
        if not user or not user.get("subscription_id"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
            
        subscription_id = user["subscription_id"]
        
        # Cancel subscription in Stripe immediately with refund
        stripe.Subscription.delete(
            subscription_id,
            prorate=True  # Enable prorated refund for unused time
        )
        
        # Get current timestamp
        canceled_at = datetime.now()
        
        # Update user's subscription status in database
        updated_user = await update_user_subscription_cancellation(current_user["id"], canceled_at)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user subscription status"
            )
        
        return {
            "status": "success",
            "message": "Subscription has been canceled immediately with a prorated refund",
            "canceled_at": canceled_at.isoformat()
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error in cancel_subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in cancel_subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/subscriptions/change", response_model=ChangeSubscriptionResponse)
async def change_subscription(
    request: ChangeSubscriptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Change an existing subscription's plan type, lead tier, or channels
    """
    try:
        # Get user details
        user = await get_user_by_id(current_user["id"])
        
        if not user or not user.get("subscription_id"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        # Update subscription items
        stripe_service = StripeService()
        updated_subscription = await stripe_service.update_subscription_items(
            user["subscription_id"],
            request.plan_type,
            request.lead_tier,
            request.channels.dict()
        )
        
        return {
            "subscription_id": updated_subscription.id
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error in change_subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in change_subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 