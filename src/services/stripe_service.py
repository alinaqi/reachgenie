"""
Stripe service module for handling all Stripe-related functionality.
"""
import stripe
from typing import Dict
import logging
from src.config import get_settings

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
                "name": "Fixed Plan",
                "description": "Fixed monthly pricing with base fee + lead tier cost",
                "metadata": {"plan_type": "fixed"}
            },
            "performance": {
                "name": "Performance Plan",
                "description": "Performance-based pricing with lower base fee + lead tier cost + per-meeting cost",
                "metadata": {"plan_type": "performance"}
            },
            "email_channel": {
                "name": "Email Channel",
                "description": "Email outreach capability",
                "metadata": {"addon_type": "channel", "channel": "email"}
            },
            "phone_channel": {
                "name": "Phone Channel",
                "description": "Phone outreach capability",
                "metadata": {"addon_type": "channel", "channel": "phone"}
            },
            "linkedin_channel": {
                "name": "LinkedIn Channel",
                "description": "LinkedIn outreach capability",
                "metadata": {"addon_type": "channel", "channel": "linkedin"}
            },
            "whatsapp_channel": {
                "name": "WhatsApp Channel",
                "description": "WhatsApp outreach capability",
                "metadata": {"addon_type": "channel", "channel": "whatsapp"}
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

# Create a global instance
stripe_service = StripeService() 