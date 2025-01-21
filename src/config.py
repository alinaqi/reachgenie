from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    jwt_secret_key: str
    algorithm: str = "HS256"
    supabase_url: str
    supabase_key: str
    SUPABASE_SERVICE_KEY: str  # Changed to match .env file name
    perplexity_api_key: str
    bland_api_key: str
    bland_api_url: str = "https://api.bland.ai"
    webhook_base_url: str
    mailjet_api_key: str
    mailjet_api_secret: str
    mailjet_sender_email: str
    mailjet_sender_name: str
    mailjet_webhook_secret: str
    mailjet_parse_email: str  # Email address for parsing replies
    openai_api_key: str  # OpenAI API key for sentiment analysis
    calendly_username: str = "sdr-ai"  # Default value, should be overridden in .env
    cronofy_client_id: str = ""  # Made optional with default empty string
    cronofy_client_secret: str = ""  # Made optional with default empty string
    cronofy_redirect_uri: str = ""  # Made optional with default empty string
    
    # Encryption settings
    encryption_key: str
    encryption_salt: str

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings() 