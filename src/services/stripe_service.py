"""
Stripe service module for handling all Stripe-related functionality.
"""
import stripe
from typing import Dict, Any
import logging
from src.config import get_settings
from src.database import get_user_by_id

# Set up logger
logger = logging.getLogger(__name__)

settings = get_settings()
stripe.api_key = settings.stripe_secret_key

class StripeService:
    def __init__(self):
        """Initialize the Stripe service"""
        self.settings = get_settings()
        stripe.api_key = self.settings.stripe_secret_key
        
        # Define product metadata
        self.products = {
            "fixed": {
                "name": "ReachGenie - Fixed Plan",
                "description": "Predictable monthly pricing with base fee and lead tier costs",
                "metadata": {"plan_type": "fixed"}
            },
            "performance": {
                "name": "ReachGenie - Performance Plan",
                "description": "Pay-as-you-go pricing with lower base fee and per-meeting charges",
                "metadata": {"plan_type": "performance"}
            },
            "email_channel": {
                "name": "ReachGenie - Email Channel",
                "description": "Professional email outreach automation",
                "metadata": {"addon_type": "channel", "channel": "email"}
            },
            "phone_channel": {
                "name": "ReachGenie - Phone Channel",
                "description": "Direct phone call outreach and management",
                "metadata": {"addon_type": "channel", "channel": "phone"}
            },
            "linkedin_channel": {
                "name": "ReachGenie - LinkedIn Channel",
                "description": "LinkedIn connection and messaging automation",
                "metadata": {"addon_type": "channel", "channel": "linkedin"}
            },
            "whatsapp_channel": {
                "name": "ReachGenie - WhatsApp Channel",
                "description": "WhatsApp business messaging integration",
                "metadata": {"addon_type": "channel", "channel": "whatsapp"}
            },
            "meetings": {
                "name": "ReachGenie - Meetings Booked",
                "description": "Usage-based billing for successful meeting bookings",
                "metadata": {"type": "meetings_usage", "plan_type": "performance"}
            }
        }
        
        # Define price configurations
        self.price_configs = {
            "fixed": {
                2500: {"base": 800, "leads": 75},  # $875 total
                5000: {"base": 800, "leads": 150}, # $950 total
                7500: {"base": 800, "leads": 225}, # $1,025 total
                10000: {"base": 800, "leads": 300} # $1,100 total
            },
            "performance": {
                2500: {"base": 600, "leads": 0},   # $600 total
                5000: {"base": 600, "leads": 75},  # $675 total
                7500: {"base": 600, "leads": 150}, # $750 total
                10000: {"base": 600, "leads": 225} # $825 total
            },
            "channels": {
                "fixed": {
                    "email": 50,
                    "phone": 1500,
                    "linkedin": 300,
                    "whatsapp": 200
                },
                "performance": {
                    "email": 25,
                    "phone": 750,
                    "linkedin": 150,
                    "whatsapp": 100
                }
            }
        }
    
    async def create_product(self, product_type: str) -> Dict:
        """
        Create a Stripe product
        
        Args:
            product_type: Type of product to create (fixed, performance, email_channel, phone_channel, linkedin_channel, whatsapp_channel)
            
        Returns:
            Created product object
        """
        try:
            product_config = self.products.get(product_type)
            if not product_config:
                raise ValueError(f"Invalid product type: {product_type}")
            
            product = stripe.Product.create(
                name=product_config["name"],
                description=product_config["description"],
                metadata=product_config["metadata"]
            )
            
            logger.info(f"Created Stripe product: {product.id} ({product.name})")
            return product
            
        except Exception as e:
            logger.error(f"Error creating Stripe product: {str(e)}")
            raise
    
    async def create_price(self, product_id: str, amount: int, metadata: Dict = None) -> Dict:
        """
        Create a Stripe price
        
        Args:
            product_id: Stripe product ID
            amount: Price amount in cents
            metadata: Optional metadata for the price
            
        Returns:
            Created price object
        """
        try:
            price = stripe.Price.create(
                product=product_id,
                unit_amount=amount * 100,  # Convert to cents
                currency="usd",
                recurring={"interval": "month"},
                metadata=metadata or {}
            )
            
            logger.info(f"Created Stripe price: {price.id} (${amount})")
            return price
            
        except Exception as e:
            logger.error(f"Error creating Stripe price: {str(e)}")
            raise
    
    async def create_all_products_and_prices(self) -> Dict[str, str]:
        """
        Create all necessary products and prices in Stripe
        
        Returns:
            Dictionary mapping price types to their Stripe price IDs
        """
        price_ids = {}
        
        try:
            # Create base products
            fixed_product = await self.create_product("fixed")
            performance_product = await self.create_product("performance")
            email_product = await self.create_product("email_channel")
            phone_product = await self.create_product("phone_channel")
            linkedin_product = await self.create_product("linkedin_channel")
            whatsapp_product = await self.create_product("whatsapp_channel")
            meetings_product = await self.create_product("meetings")
            
            # Create prices for fixed plans
            for tier, amounts in self.price_configs["fixed"].items():
                total = amounts["base"] + amounts["leads"]
                price = await self.create_price(
                    fixed_product.id,
                    total,
                    {
                        "plan_type": "fixed",
                        "lead_tier": str(tier),
                        "base_amount": str(amounts["base"]),
                        "lead_amount": str(amounts["leads"])
                    }
                )
                price_ids[f"fixed_{tier}"] = price.id
            
            # Create prices for performance plans
            for tier, amounts in self.price_configs["performance"].items():
                total = amounts["base"] + amounts["leads"]
                price = await self.create_price(
                    performance_product.id,
                    total,
                    {
                        "plan_type": "performance",
                        "lead_tier": str(tier),
                        "base_amount": str(amounts["base"]),
                        "lead_amount": str(amounts["leads"])
                    }
                )
                price_ids[f"performance_{tier}"] = price.id
            
            # Create metered price for meetings (performance plan only)
            if self.settings.stripe_meetings_booked_meter_id:
                try:
                    metered_price = await self.create_metered_price_for_meetings(meetings_product.id)
                    price_ids["performance_meetings"] = metered_price.id
                except Exception as e:
                    logger.error(f"Failed to create metered price for meetings: {str(e)}")
                    # Continue with other prices even if metered price creation fails
            
            # Create prices for channels
            # Fixed plan channels
            price = await self.create_price(
                email_product.id,
                self.price_configs["channels"]["fixed"]["email"],
                {"plan_type": "fixed", "channel": "email", "addon_type": "channel"}
            )
            price_ids["email_fixed"] = price.id
            
            price = await self.create_price(
                phone_product.id,
                self.price_configs["channels"]["fixed"]["phone"],
                {"plan_type": "fixed", "channel": "phone", "addon_type": "channel"}
            )
            price_ids["phone_fixed"] = price.id
            
            price = await self.create_price(
                linkedin_product.id,
                self.price_configs["channels"]["fixed"]["linkedin"],
                {"plan_type": "fixed", "channel": "linkedin", "addon_type": "channel"}
            )
            price_ids["linkedin_fixed"] = price.id
            
            price = await self.create_price(
                whatsapp_product.id,
                self.price_configs["channels"]["fixed"]["whatsapp"],
                {"plan_type": "fixed", "channel": "whatsapp", "addon_type": "channel"}
            )
            price_ids["whatsapp_fixed"] = price.id
            
            # Performance plan channels
            price = await self.create_price(
                email_product.id,
                self.price_configs["channels"]["performance"]["email"],
                {"plan_type": "performance", "channel": "email", "addon_type": "channel"}
            )
            price_ids["email_performance"] = price.id
            
            price = await self.create_price(
                phone_product.id,
                self.price_configs["channels"]["performance"]["phone"],
                {"plan_type": "performance", "channel": "phone", "addon_type": "channel"}
            )
            price_ids["phone_performance"] = price.id
            
            price = await self.create_price(
                linkedin_product.id,
                self.price_configs["channels"]["performance"]["linkedin"],
                {"plan_type": "performance", "channel": "linkedin", "addon_type": "channel"}
            )
            price_ids["linkedin_performance"] = price.id
            
            price = await self.create_price(
                whatsapp_product.id,
                self.price_configs["channels"]["performance"]["whatsapp"],
                {"plan_type": "performance", "channel": "whatsapp", "addon_type": "channel"}
            )
            price_ids["whatsapp_performance"] = price.id

            return price_ids
            
        except Exception as e:
            logger.error(f"Error creating Stripe products and prices: {str(e)}")
            raise

    async def create_billing_meter(
        self,
        display_name: str,
        event_name: str,
        event_payload_key: str = "value",
        customer_payload_key: str = "stripe_customer_id"
    ) -> Dict:
        """
        Create a Stripe billing meter for usage-based billing.
        
        Args:
            display_name: Display name for the meter
            event_name: Name of the event to track
            event_payload_key: Key in the event payload that contains the value to measure (default: "value")
            customer_payload_key: Key in the event payload that contains the customer ID (default: "stripe_customer_id")
            
        Returns:
            Created billing meter object
        """
        try:
            meter = stripe.billing.Meter.create(
                display_name=display_name,
                event_name=event_name,
                default_aggregation={
                    "formula": "sum"
                },
                customer_mapping={
                    "event_payload_key": customer_payload_key,
                    "type": "by_id"
                },
                value_settings={
                    "event_payload_key": event_payload_key
                }
            )
            
            logger.info(f"Created Stripe billing meter: {meter.id} ({display_name})")
            return meter
            
        except Exception as e:
            logger.error(f"Error creating Stripe billing meter: {str(e)}")
            raise

    async def create_metered_price_for_meetings(self, product_id: str) -> Dict:
        """
        Create a metered price for meetings booked in the Performance Plan.
        
        Args:
            product_id: The ID of the Performance Plan product
            
        Returns:
            Created price object
        """
        try:
            if not self.settings.stripe_meetings_booked_meter_id:
                raise ValueError("STRIPE_MEETINGS_BOOKED_METER_ID not configured")

            price = stripe.Price.create(
                product=product_id,
                currency="usd",
                unit_amount=6000,  # $60.00 per meeting
                billing_scheme="per_unit",
                recurring={
                    "usage_type": "metered",
                    "interval": "month",
                    "meter": self.settings.stripe_meetings_booked_meter_id
                },
                metadata={
                    "type": "meetings_usage",
                    "plan_type": "performance"
                }
            )
            
            logger.info(f"Created metered price for meetings: {price.id}")
            return price
            
        except Exception as e:
            logger.error(f"Error creating metered price for meetings: {str(e)}")
            raise

    async def report_meeting_booked(self, stripe_customer_id: str, count: int = 1) -> Dict:
        """
        Report a meeting booking to Stripe for usage-based billing.
        
        Args:
            stripe_customer_id: The Stripe customer ID to report usage for
            count: Number of meetings to report (default: 1)
            
        Returns:
            Dict containing the meter event details
        """
        try:
            # Report the meeting event
            meter_event = stripe.billing.MeterEvent.create(
                event_name="reachgenie_meetings_booked",
                payload={
                    "stripe_customer_id": stripe_customer_id,
                    "value": count
                }
            )
            
            logger.info(f"Reported {count} meeting(s) for customer {stripe_customer_id}")
            return meter_event
            
        except Exception as e:
            logger.error(f"Error reporting meeting booking: {str(e)}")
            raise

    async def get_subscription_details(self, user_id: str) -> Dict[str, Any]:
        """
        Get subscription details for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with subscription items and their details
        """
        try:
            # Get user details using get_user_by_id
            user = await get_user_by_id(user_id)
            if not user or not user.get('subscription_id'):
                return {
                    "has_subscription": False,
                    "message": "No active subscription"
                }
            
            # Get subscription from Stripe
            subscription = stripe.Subscription.retrieve(user['subscription_id'])
            
            # Extract subscription items
            subscription_items = []
            for item in subscription.items.data:
                price = item.price
                product = stripe.Product.retrieve(price.product)
                
                # Format the price amount
                amount = price.unit_amount / 100  # Convert cents to dollars
                
                # Create item description
                item_details = {
                    "name": product.name,
                    "quantity": item.quantity,
                    "price": f"${amount:.2f} per month"
                }
                
                subscription_items.append(item_details)
            
            return {
                "has_subscription": True,
                "subscription_items": subscription_items
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription details: {str(e)}")
            return {
                "has_subscription": False,
                "message": str(e)
            }

# Create a global instance
stripe_service = StripeService() 