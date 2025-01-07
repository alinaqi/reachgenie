from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    jwt_secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    supabase_url: str
    supabase_key: str
    perplexity_api_key: str
    bland_api_key: str
    bland_api_url: str = "https://api.bland.ai"
    webhook_base_url: str
    mailjet_api_key: str
    mailjet_api_secret: str
    mailjet_sender_email: str
    mailjet_sender_name: str
    mailjet_webhook_secret: str  # Secret key for Mailjet webhook authentication

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings() 