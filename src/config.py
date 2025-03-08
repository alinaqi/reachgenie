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
    
    frontend_url: str = "http://localhost:3000"  # Default frontend URL

    class Config:
        env_file = ".env"

def get_settings():
    return Settings() 