from pydantic_settings import BaseSettings
from pydantic import Field

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
    encryption_key: str
    encryption_salt: str
    cronofy_client_id: str
    cronofy_client_secret: str
    
    # Mailjet settings
    mailjet_api_key: str
    mailjet_api_secret: str
    mailjet_sender_email: str
    mailjet_sender_name: str = "Outbound AI"  # Default sender name
    frontend_url: str = "http://localhost:3000"  # Default frontend URL
    bland_tool_secret: str

    class Config:
        env_file = ".env"

def get_settings():
    return Settings() 