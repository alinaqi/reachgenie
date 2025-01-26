from pydantic import BaseSettings

class Settings(BaseSettings):
    jwt_secret_key: str
    algorithm: str = "HS256"
    supabase_url: str
    supabase_key: str
    SUPABASE_SERVICE_KEY: str
    perplexity_api_key: str
    openai_api_key: str
    bland_api_key: str
    bland_api_url: str = "https://api.bland.ai"
    webhook_base_url: str
    encryption_key: str
    encryption_salt: str
    cronofy_client_id: str
    cronofy_client_secret: str

    class Config:
        env_file = ".env"

def get_settings():
    return Settings() 