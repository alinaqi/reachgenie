# Add these to your models.py CampaignType enum:

class CampaignType(str, Enum):
    EMAIL = 'email'
    CALL = 'call'
    EMAIL_AND_CALL = 'email_and_call'
    LINKEDIN = 'linkedin'  # Add this
    LINKEDIN_AND_EMAIL = 'linkedin_and_email'  # Add this
    LINKEDIN_AND_CALL = 'linkedin_and_call'  # Add this
    ALL_CHANNELS = 'all_channels'  # Add this

# Update EmailCampaignBase to be more generic CampaignBase:
class CampaignBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: CampaignType
    product_id: UUID
    
    # Email settings
    template: Optional[str] = None
    number_of_reminders: Optional[int] = 0
    days_between_reminders: Optional[int] = 0
    auto_reply_enabled: Optional[bool] = False
    
    # Call settings
    phone_number_of_reminders: Optional[int] = 0
    phone_days_between_reminders: Optional[int] = 0
    trigger_call_on: Optional[str] = Field(None, description="Condition to trigger a call")
    
    # LinkedIn settings
    linkedin_message_template: Optional[str] = None
    linkedin_invitation_template: Optional[str] = None
    linkedin_inmail_enabled: Optional[bool] = False
    linkedin_number_of_reminders: Optional[int] = 0
    linkedin_days_between_reminders: Optional[int] = 0
    
    # Scheduling
    scheduled_at: Optional[datetime] = Field(None, description="When the campaign should be scheduled to start")
