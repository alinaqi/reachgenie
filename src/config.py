from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    jwt_secret_key: str
    algorithm: str = "HS256"
    supabase_url: str
    supabase_key: str
    SUPABASE_SERVICE_KEY: str
    perplexity_api_key: str = Field(..., env='PERPLEXITY_API_KEY')
    openai_api_key: str
    bland_api_key: str
    bland_api_url: str = "https://api.bland.ai"
    webhook_base_url: str
    bland_tool_id: str
    bland_secret_key: str
    encryption_key: str
    encryption_salt: str
    cronofy_client_id: str
    cronofy_client_secret: str
    anthropic_api_key: str
    
    # Stripe settings
    stripe_secret_key: str
    stripe_webhook_secret: Optional[str] = None
    stripe_price_performance_meetings: Optional[str] = None
    stripe_meetings_booked_meter_id: Optional[str] = None  # Meter ID for tracking booked meetings
    stripe_price_fixed_2500: Optional[str] = None
    stripe_price_fixed_5000: Optional[str] = None
    stripe_price_fixed_7500: Optional[str] = None
    stripe_price_fixed_10000: Optional[str] = None
    stripe_price_performance_2500: Optional[str] = None
    stripe_price_performance_5000: Optional[str] = None
    stripe_price_performance_7500: Optional[str] = None
    stripe_price_performance_10000: Optional[str] = None
    stripe_price_email_fixed: Optional[str] = None
    stripe_price_phone_fixed: Optional[str] = None
    stripe_price_email_performance: Optional[str] = None
    stripe_price_phone_performance: Optional[str] = None
    stripe_price_linkedin_fixed: Optional[str] = None  # Coming soon
    stripe_price_whatsapp_fixed: Optional[str] = None  # Coming soon
    stripe_price_linkedin_performance: Optional[str] = None  # Coming soon
    stripe_price_whatsapp_performance: Optional[str] = None  # Coming soon
    
    # Bugsnag settings
    bugsnag_api_key: str
    environment: str = "development"
    
    # Mailjet settings
    mailjet_api_key: str
    mailjet_api_secret: str
    mailjet_sender_email: str
    mailjet_sender_name: str = "Outbound AI"  # Default sender name
    mailjet_webhook_secret: Optional[str] = None
    mailjet_parse_email: Optional[str] = None
    
    # NoReply Email settings for partnership emails
    noreply_email: Optional[str] = None
    noreply_password: Optional[str] = None
    noreply_provider: str = "gmail"  # Default provider (gmail, outlook, yahoo)
    
    # Calendar settings
    calendly_username: Optional[str] = None
    
    frontend_url: str = "http://localhost:5173"  # Default frontend URL

    redis_url: str = "redis://localhost:6379/0"
    
    # Unipile/LinkedIn settings
    unipile_api_key: Optional[str] = None
    unipile_dsn: Optional[str] = None
    unipile_webhook_secret: Optional[str] = None
    linkedin_messaging_enabled: bool = True
    linkedin_daily_invite_limit: int = 80
    linkedin_daily_profile_view_limit: int = 100
    linkedin_message_delay_seconds: int = 20

    class Config:
        env_file = ".env"

def get_settings():
    return Settings() 