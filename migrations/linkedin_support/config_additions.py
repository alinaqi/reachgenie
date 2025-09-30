# Add these to your Settings class in config.py:

    # Unipile API settings
    unipile_api_key: str = Field(..., env='UNIPILE_API_KEY')
    unipile_dsn: str = Field(..., env='UNIPILE_DSN')
    unipile_webhook_secret: Optional[str] = Field(None, env='UNIPILE_WEBHOOK_SECRET')
    
    # LinkedIn Feature Configuration
    linkedin_messaging_enabled: bool = Field(True, env='LINKEDIN_MESSAGING_ENABLED')
    linkedin_daily_invite_limit: int = Field(80, env='LINKEDIN_DAILY_INVITE_LIMIT')
    linkedin_daily_profile_view_limit: int = Field(100, env='LINKEDIN_DAILY_PROFILE_VIEW_LIMIT')
    linkedin_message_delay_seconds: int = Field(20, env='LINKEDIN_MESSAGE_DELAY_SECONDS')
