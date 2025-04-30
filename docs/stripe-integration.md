
# ReachGenie Simplified Tier-Based Pricing in Stripe

## Overview

This implementation simplifies ReachGenie's pricing model by creating fixed packages based on lead tiers, with package changes occurring whenever users modify their tier selection.

## Package Structure

### Core Packages

Create distinct products in Stripe for each lead tier × plan type combination:

**Fixed Plan Packages:**
1. Fixed-2500: $800/month base + $75 for 2,500 leads = **$875/month**
2. Fixed-5000: $800/month base + $150 for 5,000 leads = **$950/month**
3. Fixed-7500: $800/month base + $225 for 7,500 leads = **$1,025/month**
4. Fixed-10000: $800/month base + $300 for 10,000 leads = **$1,100/month**

**Performance Plan Packages:**
1. Performance-2500: $600/month base (10 meetings min) + $0 for 2,500 leads = **$600/month**
2. Performance-5000: $600/month base (10 meetings min) + $75 for 5,000 leads = **$675/month**
3. Performance-7500: $600/month base (10 meetings min) + $150 for 7,500 leads = **$750/month**
4. Performance-10000: $600/month base (10 meetings min) + $225 for 10,000 leads = **$825/month**

### Channel Add-ons

Channels remain as subscription add-ons that can be toggled independently:

**Fixed Plan Channel Add-ons:**
- Email: +$50/month
- Phone: +$1,500/month
- LinkedIn: +$300/month (coming soon)
- WhatsApp: +$200/month (coming soon)

**Performance Plan Channel Add-ons:**
- Email: +$25/month
- Phone: +$750/month
- LinkedIn: +$150/month (coming soon)
- WhatsApp: +$100/month (coming soon)

## Stripe Implementation

### 1. Product & Price Configuration

Set up products for each core package and channel:

```javascript
// Example: Creating Fixed-5000 package
const fixed5000 = await stripe.prices.create({
  product: 'prod_reachgenie_fixed_tier',
  unit_amount: 95000, // $950.00
  currency: 'usd',
  recurring: {
    interval: 'month',
  },
  metadata: {
    plan_type: 'fixed',
    lead_tier: '5000'
  }
});

// Example: Creating Email channel add-on for fixed plan
const fixedEmailAddon = await stripe.prices.create({
  product: 'prod_reachgenie_email_channel',
  unit_amount: 5000, // $50.00
  currency: 'usd',
  recurring: {
    interval: 'month',
  },
  metadata: {
    addon_type: 'channel',
    channel: 'email',
    plan_type: 'fixed'
  }
});
```

### 2. Subscription Creation

When creating a subscription, select the appropriate base package and add channels:

```javascript
// Subscribe customer to Fixed-5000 package with Email channel
const subscription = await stripe.subscriptions.create({
  customer: 'cus_123456',
  items: [
    { price: 'price_fixed_5000' }, // Base package price ID
    { price: 'price_fixed_email' } // Email channel price ID
  ],
  metadata: {
    plan_type: 'fixed',
    lead_tier: '5000'
  }
});
```

### 3. Changing Lead Tiers

When a user changes their lead tier, update the base subscription item:

```javascript
// Find the base package subscription item
const subscription = await stripe.subscriptions.retrieve('sub_123456');
const basePackageItem = subscription.items.data.find(
  item => item.price.metadata.lead_tier !== undefined
);

// Update to new tier (e.g., from 5000 to 7500)
await stripe.subscriptionItems.update(basePackageItem.id, {
  price: 'price_fixed_7500', // New tier price ID
  proration_behavior: 'create_prorations' // Prorate the change
});

// Update subscription metadata
await stripe.subscriptions.update(subscription.id, {
  metadata: {
    ...subscription.metadata,
    lead_tier: '7500'
  }
});
```

### 4. Changing Plan Type

When a user switches between fixed and performance plans:

```javascript
// Find the base package subscription item
const subscription = await stripe.subscriptions.retrieve('sub_123456');
const basePackageItem = subscription.items.data.find(
  item => item.price.metadata.lead_tier !== undefined
);
const leadTier = subscription.metadata.lead_tier;

// Update to new plan type (e.g., from fixed to performance)
await stripe.subscriptionItems.update(basePackageItem.id, {
  price: `price_performance_${leadTier}`, // New plan type price ID
  proration_behavior: 'create_prorations' // Prorate the change
});

// Update subscription metadata
await stripe.subscriptions.update(subscription.id, {
  metadata: {
    ...subscription.metadata,
    plan_type: 'performance'
  }
});

// Add metered usage item for performance plan
if (subscription.metadata.plan_type === 'fixed') {
  await stripe.subscriptionItems.create({
    subscription: subscription.id,
    price: 'price_performance_meeting_usage'
  });
}
```

### 5. Channel Management

Add or remove channels as subscription items:

```javascript
// Add a channel
await stripe.subscriptionItems.create({
  subscription: 'sub_123456',
  price: 'price_fixed_phone' // Channel price ID
});

// Remove a channel
await stripe.subscriptionItems.delete('si_channel_item_id');
```

## Handling Performance-Based Meetings

For performance plans, use metered billing for meetings beyond the minimum:

```javascript
// Report a meeting booking
const reportMeeting = async (subscriptionId) => {
  // Get the subscription
  const subscription = await stripe.subscriptions.retrieve(subscriptionId);
  
  // Check if this is a performance plan
  if (subscription.metadata.plan_type !== 'performance') {
    return;
  }
  
  // Find the meetings usage item
  const meetingsItem = subscription.items.data.find(
    item => item.price.metadata.usage_type === 'meetings'
  );
  
  if (meetingsItem) {
    // Report the meeting booking
    await stripe.subscriptionItems.createUsageRecord(
      meetingsItem.id,
      {
        quantity: 1,
        timestamp: 'now',
        action: 'increment'
      }
    );
  }
};
```

## Portal Configuration

Configure the Stripe Customer Portal to allow users to:

1. View their current subscription
2. Change their plan type
3. Change their lead tier
4. Add/remove channels
5. View meeting usage (for performance plans)

## Database Structure

Your application should maintain:

```
users
  id
  stripe_customer_id
  plan_type (fixed|performance)
  lead_tier (2500|5000|7500|10000)
  channels_active (json: {email: true, phone: false, ...})
  subscription_id
  
meetings
  id
  user_id
  booked_at
  reported_to_stripe (boolean)
```

## Webhooks

Set up Stripe webhooks to handle:

1. `customer.subscription.updated` - Update user's plan details in your database
2. `invoice.payment_succeeded` - Confirm successful payments
3. `invoice.payment_failed` - Handle failed payments


# reachgenie_package_service.py

import json
import stripe
from datetime import datetime
from typing import Dict, List, Optional, Union, Any

# Configure Stripe API key
stripe.api_key = "your_stripe_api_key"  # Should use environment variables in production


class ReachGeniePackageService:
    """
    Service to handle ReachGenie package management with tier-based pricing in Python
    """
    
    def __init__(self):
        # Package price IDs (would be stored in environment variables)
        self.prices = {
            "fixed": {
                2500: "price_fixed_2500",
                5000: "price_fixed_5000",
                7500: "price_fixed_7500",
                10000: "price_fixed_10000"
            },
            "performance": {
                2500: "price_performance_2500",
                5000: "price_performance_5000",
                7500: "price_performance_7500",
                10000: "price_performance_10000"
            },
            "channels": {
                "fixed": {
                    "email": "price_fixed_email",
                    "phone": "price_fixed_phone"
                },
                "performance": {
                    "email": "price_performance_email",
                    "phone": "price_performance_phone"
                }
            },
            "meetings_usage": "price_performance_meetings_usage"
        }
    
    def create_subscription(self, customer_id: str, package_options: Dict) -> Dict:
        """
        Create a new subscription for a customer
        
        Args:
            customer_id: Stripe customer ID
            package_options: Dict containing plan_type, lead_tier, and channels
            
        Returns:
            The created subscription object
        """
        plan_type = package_options.get("plan_type")
        lead_tier = package_options.get("lead_tier")
        channels = package_options.get("channels", {})
        
        try:
            # 1. Get base package price ID
            base_package_price_id = self.prices[plan_type][lead_tier]
            
            if not base_package_price_id:
                raise ValueError(f"Invalid package configuration: {plan_type}-{lead_tier}")
            
            # 2. Build subscription items array starting with base package
            items = [{"price": base_package_price_id}]
            
            # 3. Add channels to subscription items
            if channels:
                for channel, is_active in channels.items():
                    if is_active and channel in self.prices["channels"][plan_type]:
                        items.append({"price": self.prices["channels"][plan_type][channel]})
            
            # 4. Add metered usage item for performance plans
            if plan_type == "performance":
                items.append({"price": self.prices["meetings_usage"]})
            
            # 5. Create the subscription
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=items,
                metadata={
                    "plan_type": plan_type,
                    "lead_tier": str(lead_tier),
                    "active_channels": json.dumps(channels or {})
                }
            )
            
            # 6. Update user in database
            self._update_user_subscription_details(
                customer_id, subscription.id, plan_type, lead_tier, channels
            )
            
            return subscription
        
        except Exception as e:
            print(f"Error creating subscription: {str(e)}")
            raise
    
    def change_lead_tier(self, subscription_id: str, new_lead_tier: int) -> Dict:
        """
        Change a user's lead tier
        
        Args:
            subscription_id: Stripe subscription ID
            new_lead_tier: New lead tier (2500, 5000, 7500, 10000)
            
        Returns:
            Updated subscription object
        """
        try:
            # 1. Retrieve the current subscription
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            # 2. Get current plan type and verify new tier is valid
            plan_type = subscription.metadata.get("plan_type")
            current_lead_tier = int(subscription.metadata.get("lead_tier", 0))
            
            if current_lead_tier == new_lead_tier:
                return subscription  # No change needed
            
            new_package_price_id = self.prices[plan_type][new_lead_tier]
            
            if not new_package_price_id:
                raise ValueError(f"Invalid lead tier: {new_lead_tier}")
            
            # 3. Find the base package subscription item
            base_package_item = None
            for item in subscription.items.data:
                if (not item.price.metadata.get("addon_type") and 
                    not item.price.metadata.get("usage_type")):
                    base_package_item = item
                    break
            
            if not base_package_item:
                raise ValueError("Base package item not found")
            
            # 4. Update to the new package
            stripe.SubscriptionItem.modify(
                base_package_item.id,
                price=new_package_price_id,
                proration_behavior="create_prorations"
            )
            
            # 5. Update subscription metadata
            updated_subscription = stripe.Subscription.modify(
                subscription.id,
                metadata={
                    **subscription.metadata,
                    "lead_tier": str(new_lead_tier)
                }
            )
            
            # 6. Update user in database
            user_id = self._get_user_id_from_subscription(subscription_id)
            if user_id:
                self._update_user_lead_tier(user_id, new_lead_tier)
            
            return updated_subscription
            
        except Exception as e:
            print(f"Error changing lead tier: {str(e)}")
            raise
    
    def change_plan_type(self, subscription_id: str, new_plan_type: str) -> Dict:
        """
        Change plan type (fixed <-> performance)
        
        Args:
            subscription_id: Stripe subscription ID
            new_plan_type: New plan type ('fixed' or 'performance')
            
        Returns:
            Updated subscription object
        """
        try:
            # 1. Validate plan type
            if new_plan_type not in ["fixed", "performance"]:
                raise ValueError(f"Invalid plan type: {new_plan_type}")
            
            # 2. Retrieve the current subscription
            subscription = stripe.Subscription.retrieve(subscription_id)
            current_plan_type = subscription.metadata.get("plan_type")
            
            if current_plan_type == new_plan_type:
                return subscription  # No change needed
            
            # 3. Get current lead tier and active channels
            lead_tier = int(subscription.metadata.get("lead_tier", 2500))
            active_channels = {}
            
            try:
                active_channels = json.loads(subscription.metadata.get("active_channels", "{}"))
            except Exception as e:
                print(f"Error parsing active channels: {str(e)}")
            
            # 4. Get new base package price ID
            new_package_price_id = self.prices[new_plan_type][lead_tier]
            
            if not new_package_price_id:
                raise ValueError(f"Invalid package configuration: {new_plan_type}-{lead_tier}")
            
            # 5. Find the base package subscription item
            base_package_item = None
            for item in subscription.items.data:
                if (not item.price.metadata.get("addon_type") and 
                    not item.price.metadata.get("usage_type")):
                    base_package_item = item
                    break
            
            if not base_package_item:
                raise ValueError("Base package item not found")
            
            # 6. Update to the new package
            stripe.SubscriptionItem.modify(
                base_package_item.id,
                price=new_package_price_id,
                proration_behavior="create_prorations"
            )
            
            # 7. Handle channel updates (prices differ between plan types)
            self._update_channels_for_plan_change(subscription, new_plan_type, active_channels)
            
            # 8. Handle meetings usage item
            if new_plan_type == "performance":
                # Add usage item for performance plan
                stripe.SubscriptionItem.create(
                    subscription=subscription_id,
                    price=self.prices["meetings_usage"]
                )
            else:
                # Remove usage item when switching to fixed plan
                usage_item = None
                for item in subscription.items.data:
                    if item.price.metadata.get("usage_type") == "meetings":
                        usage_item = item
                        break
                
                if usage_item:
                    stripe.SubscriptionItem.delete(usage_item.id)
            
            # 9. Update subscription metadata
            updated_subscription = stripe.Subscription.modify(
                subscription_id,
                metadata={
                    **subscription.metadata,
                    "plan_type": new_plan_type
                }
            )
            
            # 10. Update user in database
            user_id = self._get_user_id_from_subscription(subscription_id)
            if user_id:
                self._update_user_plan_type(user_id, new_plan_type)
            
            return updated_subscription
            
        except Exception as e:
            print(f"Error changing plan type: {str(e)}")
            raise
    
    def update_channels(self, subscription_id: str, new_channels: Dict[str, bool]) -> Dict:
        """
        Update channels for a subscription
        
        Args:
            subscription_id: Stripe subscription ID
            new_channels: Dict of channel selections {email: True, phone: False, etc}
            
        Returns:
            Updated subscription object
        """
        try:
            # 1. Retrieve the current subscription
            subscription = stripe.Subscription.retrieve(subscription_id)
            plan_type = subscription.metadata.get("plan_type")
            
            # 2. Get current active channels
            current_channels = {}
            
            try:
                current_channels = json.loads(subscription.metadata.get("active_channels", "{}"))
            except Exception as e:
                print(f"Error parsing active channels: {str(e)}")
            
            # 3. Process channel changes
            available_channels = self.prices["channels"][plan_type].keys()
            
            for channel in available_channels:
                was_active = current_channels.get(channel, False)
                will_be_active = new_channels.get(channel, False)
                
                # Channel status changed
                if was_active != will_be_active:
                    if will_be_active:
                        # Add channel
                        stripe.SubscriptionItem.create(
                            subscription=subscription_id,
                            price=self.prices["channels"][plan_type][channel]
                        )
                    else:
                        # Remove channel
                        channel_item = None
                        for item in subscription.items.data:
                            if (item.price.metadata.get("addon_type") == "channel" and 
                                item.price.metadata.get("channel") == channel):
                                channel_item = item
                                break
                        
                        if channel_item:
                            stripe.SubscriptionItem.delete(channel_item.id)
            
            # 4. Update subscription metadata
            updated_subscription = stripe.Subscription.modify(
                subscription_id,
                metadata={
                    **subscription.metadata,
                    "active_channels": json.dumps(new_channels)
                }
            )
            
            # 5. Update user in database
            user_id = self._get_user_id_from_subscription(subscription_id)
            if user_id:
                self._update_user_channels(user_id, new_channels)
            
            return updated_subscription
            
        except Exception as e:
            print(f"Error updating channels: {str(e)}")
            raise
    
    def report_meeting_booking(self, user_id: str, count: int = 1) -> Optional[Dict]:
        """
        Report meeting booking for performance plan
        
        Args:
            user_id: User ID
            count: Number of meetings to report (default: 1)
            
        Returns:
            Usage record or None
        """
        try:
            # 1. Get user subscription details
            user = self._get_user_by_id(user_id)
            
            if not user or not user.get("subscription_id"):
                raise ValueError("User or subscription not found")
            
            # 2. Get subscription
            subscription = stripe.Subscription.retrieve(user["subscription_id"])
            
            # 3. Verify this is a performance plan
            if subscription.metadata.get("plan_type") != "performance":
                print("Not reporting meeting for fixed plan")
                return None
            
            # 4. Find meetings usage item
            usage_item = None
            for item in subscription.items.data:
                if item.price.metadata.get("usage_type") == "meetings":
                    usage_item = item
                    break
            
            if not usage_item:
                raise ValueError("Meetings usage item not found")
            
            # 5. Report usage
            usage_record = stripe.SubscriptionItem.create_usage_record(
                usage_item.id,
                quantity=count,
                timestamp=int(datetime.now().timestamp()),
                action="increment"
            )
            
            # 6. Record in database
            self._record_meeting_booking(user_id, count)
            
            return usage_record
            
        except Exception as e:
            print(f"Error reporting meeting booking: {str(e)}")
            raise
    
    def get_subscription_details(self, user_id: str) -> Dict[str, Any]:
        """
        Get subscription details for a user - for displaying in the UI
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with subscription details
        """
        try:
            # 1. Get user details from database
            user = self._get_user_by_id(user_id)
            
            if not user or not user.get("subscription_id"):
                return {
                    "has_subscription": False,
                    "message": "No active subscription"
                }
            
            # 2. Get subscription from Stripe
            subscription = stripe.Subscription.retrieve(user["subscription_id"])
            
            # 3. Extract plan type and lead tier
            plan_type = subscription.metadata.get("plan_type", "fixed")
            lead_tier = int(subscription.metadata.get("lead_tier", 2500))
            
            # 4. Extract active channels
            active_channels = {}
            try:
                active_channels = json.loads(subscription.metadata.get("active_channels", "{}"))
            except Exception:
                pass
            
            # 5. Calculate monthly cost
            monthly_cost = 0
            for item in subscription.items.data:
                if item.price.recurring and item.price.recurring.usage_type != "metered":
                    monthly_cost += item.price.unit_amount / 100 * item.quantity
            
            # 6. Check if this is a performance plan
            performance_metrics = None
            if plan_type == "performance":
                # Get meeting usage details
                usage_item = None
                for item in subscription.items.data:
                    if item.price.metadata.get("usage_type") == "meetings":
                        usage_item = item
                        break
                
                if usage_item:
                    # Get current usage
                    try:
                        usage_records = stripe.SubscriptionItem.list_usage_record_summaries(
                            usage_item.id
                        )
                        
                        current_usage = 0
                        if usage_records.data:
                            current_usage = usage_records.data[0].total_usage
                        
                        performance_metrics = {
                            "minimum_meetings": 10,
                            "current_meetings": current_usage,
                            "additional_meetings": max(0, current_usage - 10),
                            "per_meeting_cost": 60
                        }
                    except Exception as e:
                        print(f"Error getting usage records: {str(e)}")
                        performance_metrics = {
                            "minimum_meetings": 10,
                            "current_meetings": 0,
                            "additional_meetings": 0,
                            "per_meeting_cost": 60
                        }
            
            # 7. Build response
            return {
                "has_subscription": True,
                "subscription_id": subscription.id,
                "plan_type": plan_type,
                "lead_tier": lead_tier,
                "active_channels": active_channels,
                "monthly_base_cost": monthly_cost,
                "current_period_start": datetime.fromtimestamp(subscription.current_period_start).isoformat(),
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end).isoformat(),
                "status": subscription.status,
                "performance_metrics": performance_metrics
            }
            
        except Exception as e:
            print(f"Error getting subscription details: {str(e)}")
            return {
                "has_subscription": False,
                "error": str(e)
            }
    
    # ----- Helper methods -----
    
    def _update_channels_for_plan_change(self, subscription: Dict, new_plan_type: str, active_channels: Dict) -> None:
        """
        Update channels when changing plan type
        
        Args:
            subscription: Stripe subscription object
            new_plan_type: New plan type
            active_channels: Currently active channels
        """
        try:
            # Get all channel items
            channel_items = []
            for item in subscription.items.data:
                if item.price.metadata.get("addon_type") == "channel":
                    channel_items.append(item)
            
            # Process each active channel
            for channel, is_active in active_channels.items():
                if is_active and channel in self.prices["channels"][new_plan_type]:
                    # Find existing channel item
                    existing_item = None
                    for item in channel_items:
                        if item.price.metadata.get("channel") == channel:
                            existing_item = item
                            break
                    
                    if existing_item:
                        # Update to new plan price
                        stripe.SubscriptionItem.modify(
                            existing_item.id,
                            price=self.prices["channels"][new_plan_type][channel]
                        )
                    else:
                        # Add channel with new plan price
                        stripe.SubscriptionItem.create(
                            subscription=subscription.id,
                            price=self.prices["channels"][new_plan_type][channel]
                        )
            
        except Exception as e:
            print(f"Error updating channels for plan change: {str(e)}")
            raise
    
    # ----- Database integration methods -----
    # These methods would connect to your actual database
    
    def _update_user_subscription_details(self, customer_id: str, subscription_id: str, 
                                         plan_type: str, lead_tier: int, channels: Dict) -> None:
        """Update user subscription details in database"""
        # Implement with your database ORM
        print(f"DB: Updated user with customer ID {customer_id}, subscription {subscription_id}")
        # Example with SQLAlchemy: 
        # db.session.query(User).filter_by(stripe_customer_id=customer_id).update({
        #     "subscription_id": subscription_id,
        #     "plan_type": plan_type,
        #     "lead_tier": lead_tier,
        #     "channels": json.dumps(channels)
        # })
        # db.session.commit()
    
    def _update_user_lead_tier(self, user_id: str, lead_tier: int) -> None:
        """Update user lead tier in database"""
        print(f"DB: Updated user {user_id} lead tier to {lead_tier}")
        # Example: db.session.query(User).filter_by(id=user_id).update({"lead_tier": lead_tier})
        # db.session.commit()
    
    def _update_user_plan_type(self, user_id: str, plan_type: str) -> None:
        """Update user plan type in database"""
        print(f"DB: Updated user {user_id} plan type to {plan_type}")
        # Example: db.session.query(User).filter_by(id=user_id).update({"plan_type": plan_type})
        # db.session.commit()
    
    def _update_user_channels(self, user_id: str, channels: Dict) -> None:
        """Update user channels in database"""
        print(f"DB: Updated user {user_id} channels")
        # Example: db.session.query(User).filter_by(id=user_id).update({"channels": json.dumps(channels)})
        # db.session.commit()
    
    def _get_user_id_from_subscription(self, subscription_id: str) -> Optional[str]:
        """Get user ID from subscription ID"""
        print(f"DB: Getting user for subscription {subscription_id}")
        # Example: user = db.session.query(User).filter_by(subscription_id=subscription_id).first()
        # return user.id if user else None
        return "user_123"  # Mock for example
    
    def _get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        print(f"DB: Getting user {user_id}")
        # Example: user = db.session.query(User).filter_by(id=user_id).first()
        # return user.__dict__ if user else None
        return {
            "id": user_id,
            "subscription_id": "sub_123",
            "plan_type": "performance"
        }  # Mock for example
    
    def _record_meeting_booking(self, user_id: str, count: int) -> None:
        """Record meeting booking in database"""
        print(f"DB: Recorded {count} meeting(s) for user {user_id}")
        # Example: db.session.add(Meeting(user_id=user_id, count=count, booked_at=datetime.now(), reported_to_stripe=True))
        # db.session.commit()
