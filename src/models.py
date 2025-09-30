from pydantic import BaseModel, EmailStr, Field, validator, field_validator
from typing import Optional, List, Union, Dict, Any
from datetime import datetime
from uuid import UUID
import json
import logging
from enum import Enum, auto

logger = logging.getLogger(__name__)

class VoiceType(str, Enum):
    JOSH = "josh"
    FLORIAN = "florian"
    DEREK = "derek"
    JUNE = "june"
    NAT = "nat"
    PAIGE = "paige"

class BackgroundTrackType(str, Enum):
    OFFICE = "office"
    CAFE = "cafe"
    RESTAURANT = "restaurant"
    NONE = "none"

class LanguageCode(str, Enum):
    EN = "en"
    EN_US = "en-US"
    EN_GB = "en-GB"
    EN_AU = "en-AU"
    EN_NZ = "en-NZ"
    EN_IN = "en-IN"
    ZH = "zh"
    ZH_CN = "zh-CN"
    ZH_HANS = "zh-Hans"
    ZH_TW = "zh-TW"
    ZH_HANT = "zh-Hant"
    ES = "es"
    ES_419 = "es-419"
    FR = "fr"
    FR_CA = "fr-CA"
    DE = "de"
    EL = "el"
    HI = "hi"
    HI_LATN = "hi-Latn"
    JA = "ja"
    KO = "ko"
    KO_KR = "ko-KR"
    PT = "pt"
    PT_BR = "pt-BR"
    IT = "it"
    NL = "nl"
    PL = "pl"
    RU = "ru"
    SV = "sv"
    SV_SE = "sv-SE"
    DA = "da"
    DA_DK = "da-DK"
    FI = "fi"
    ID = "id"
    MS = "ms"
    TR = "tr"
    UK = "uk"
    BG = "bg"
    CS = "cs"
    RO = "ro"
    SK = "sk"

class VoiceAgentSettings(BaseModel):
    prompt: str
    voice: VoiceType
    background_track: BackgroundTrackType
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    language: LanguageCode
    transfer_phone_number: Optional[str] = None
    voice_settings: Optional[Dict[str, Any]] = None
    noise_cancellations: Optional[bool] = None
    phone_number: Optional[str] = None
    record: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "You are {name}, a customer service agent at {company} calling {name} about {reason}",
                "voice": "florian",
                "background_track": "office",
                "temperature": 0.7,
                "language": "en-US",
                "transfer_phone_number": "+15551234567",
                "voice_settings": {"pitch": 1.0, "speed": 1.0},
                "noise_cancellations": True,
                "phone_number": "+15557654321",
                "record": True
            }
        }

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    old_password: Optional[str] = None
    new_password: Optional[str] = None

    @field_validator('new_password')
    def validate_passwords(cls, value: Optional[str], info):
        if value is not None:
            old_password = info.data.get('old_password')
            if not old_password:
                raise ValueError('old_password is required when setting new_password')
        return value

class UserCompanyRole(BaseModel):
    company_id: UUID
    role: str

class UserInDB(UserBase):
    id: UUID
    name: Optional[str] = None
    verified: bool = False
    created_at: datetime
    company_roles: Optional[List[UserCompanyRole]] = None
    plan_type: str
    upgrade_message: Optional[str] = None
    subscription_status: Optional[str] = None
    lead_tier: Optional[int] = None
    channels_active: Optional[Dict[str, Any]] = None
    billing_period_start: Optional[datetime] = None
    billing_period_end: Optional[datetime] = None
    subscription_details: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "name": "John Doe",
                "verified": True,
                "created_at": "2024-03-15T00:00:00Z",
                "company_roles": [
                    {
                        "company_id": "6f141775-3e94-44ee-99d4-8e704cbe3e4a",
                        "role": "admin"
                    }
                ]
            }
        }

class InviteUserRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    role: str

    @field_validator('role')
    def validate_role(cls, v):
        if v not in ['admin', 'sdr']:
            raise ValueError('role must be either "admin" or "sdr"')
        return v

class CompanyInviteRequest(BaseModel):
    invites: List[InviteUserRequest]

class InviteResult(BaseModel):
    email: str
    status: str
    message: str

class CompanyInviteResponse(BaseModel):
    message: str
    results: List[InviteResult]

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Processed all invites",
                "results": [
                    {
                        "email": "john@hotmail.com",
                        "status": "success",
                        "message": "Created user and sent invite"
                    },
                    {
                        "email": "fahad@hotmail.com",
                        "status": "success",
                        "message": "Added existing user to company"
                    }
                ]
            }
        }

class InvitePasswordRequest(BaseModel):
    token: str
    password: str

class CompanyBase(BaseModel):
    name: str
    address: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    overview: Optional[str] = None
    background: Optional[str] = None
    products_services: Optional[str] = None
    account_email: Optional[str] = None
    cronofy_provider: Optional[str] = None
    cronofy_linked_email: Optional[str] = None
    cronofy_default_calendar_name: Optional[str] = None
    cronofy_default_calendar_id: Optional[str] = None
    voice_agent_settings: Optional[VoiceAgentSettings] = None
    products: Optional[List[Dict[str, Any]]] = Field(None, example=[{
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Product Name",
        "total_campaigns": 5
    }])
    total_leads: Optional[int] = None
    custom_calendar_link: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyInDB(CompanyBase):
    id: UUID
    user_id: UUID

class ProductBase(BaseModel):
    product_name: str
    file_name: Optional[str] = None
    original_filename: Optional[str] = None
    description: Optional[str] = None
    product_url: Optional[str] = None
    enriched_information: Optional[Dict[str, Any]] = None
    ideal_icps: Optional[List[Dict[str, Any]]] = None

class ProductCreate(ProductBase):
    pass

class ProductInDB(ProductBase):
    id: UUID
    company_id: UUID
    created_at: Optional[datetime] = None
    deleted: bool = False

class CompanySize(BaseModel):
    employees: Dict[str, Optional[int]]
    revenue: Optional[Dict[str, Union[int, str]]] = None

class ExclusionCriteria(BaseModel):
    industries: Optional[List[str]] = None
    companySize: Optional[CompanySize] = None

class CompanyAttributes(BaseModel):
    industries: List[str]
    companySize: CompanySize
    geographies: Dict[str, List[str]]
    maturity: List[str]
    funding: Optional[Dict[str, Any]] = None
    technologies: Optional[List[str]] = None

class ContactAttributes(BaseModel):
    jobTitles: List[str]
    departments: List[str]
    seniority: List[str]
    responsibilities: List[str]

class IdealCustomerProfile(BaseModel):
    idealCustomerProfile: Dict[str, Any] = Field(
        ...,
        example={
            "companyAttributes": {
                "industries": ["SaaS", "Technology"],
                "companySize": {
                    "employees": {"min": 50, "max": 1000},
                    "revenue": {"min": 5000000, "max": 100000000, "currency": "USD"}
                },
                "geographies": {
                    "countries": ["USA", "UK", "Canada"],
                    "regions": ["North America", "Western Europe"]
                },
                "maturity": ["Growth Stage", "Established"],
                "funding": {
                    "hasReceivedFunding": True,
                    "fundingRounds": ["Series A", "Series B"]
                },
                "technologies": ["CRM", "Marketing Automation"]
            },
            "contactAttributes": {
                "jobTitles": ["Chief Revenue Officer", "VP of Sales"],
                "departments": ["Sales", "Revenue Operations"],
                "seniority": ["Director", "VP", "C-Level"],
                "responsibilities": ["Revenue Growth", "Sales Strategy"]
            },
            "businessChallenges": ["Lead Generation", "Sales Efficiency"],
            "buyingTriggers": ["Recent Leadership Change", "Funding Announcement"],
            "exclusionCriteria": {
                "industries": ["Education", "Government"],
                "companySize": {
                    "employees": {"min": 0, "max": 10}
                }
            }
        }
    )

class LeadBase(BaseModel):
    name: str
    email: Optional[str]
    company: Optional[str] = None
    phone_number: Optional[str] = None
    company_size: Optional[str] = None
    job_title: Optional[str] = None
    company_facebook: Optional[str] = None
    company_twitter: Optional[str] = None
    company_revenue: Optional[str] = None

class LeadCreate(LeadBase):
    pass

class LeadInDB(LeadBase):
    id: UUID
    company_id: UUID

class PaginatedLeadResponse(BaseModel):
    items: List[LeadInDB]
    total: int
    page: int
    page_size: int
    total_pages: int

class CallBase(BaseModel):
    lead_id: UUID
    product_id: UUID

class CallCreate(CallBase):
    pass

class CallInDB(BaseModel):
    id: UUID
    lead_id: UUID
    product_id: UUID
    campaign_id: UUID
    duration: Optional[int] = None
    sentiment: Optional[str] = None
    summary: Optional[str] = None
    bland_call_id: Optional[str] = None
    has_meeting_booked: bool
    transcripts: Optional[list[dict]] = None
    recording_url: Optional[str] = None
    script: Optional[str] = None
    created_at: datetime
    lead_name: Optional[str] = None
    lead_phone_number: Optional[str] = None
    campaign_name: Optional[str] = None
    failure_reason: Optional[str] = None
    last_called_at: Optional[datetime] = None
    

class PaginatedCallResponse(BaseModel):
    items: List[CallInDB]
    total: int
    page: int
    page_size: int
    total_pages: int

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class BlandWebhookPayload(BaseModel):
    call_id: str
    summary: Optional[str] = None
    corrected_duration: Optional[str] = None
    analysis: Optional[dict] = None
    transcripts: list[dict]
    recording_url: Optional[str] = None
    error_message: Optional[str] = None

class CampaignType(str, Enum):
    EMAIL = 'email'
    CALL = 'call'
    EMAIL_AND_CALL = 'email_and_call'
    LINKEDIN = 'linkedin'

class EmailCampaignBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: CampaignType = CampaignType.EMAIL
    product_id: UUID
    template: Optional[str] = None
    number_of_reminders: Optional[int] = 0
    days_between_reminders: Optional[int] = 0
    auto_reply_enabled: Optional[bool] = False
    phone_number_of_reminders: Optional[int] = 0
    phone_days_between_reminders: Optional[int] = 0
    trigger_call_on: Optional[str] = Field(None, description="Condition to trigger a call", example="after_email_sent")
    scheduled_at: Optional[datetime] = Field(None, description="When the campaign should be scheduled to start")

class TaskResponse(BaseModel):
    task_id: UUID
    message: str
class TestRunCampaignRequest(BaseModel):
    lead_contact: str
class EmailCampaignCreate(EmailCampaignBase):
    pass

class EmailCampaignInDB(EmailCampaignBase):
    id: UUID
    company_id: UUID
    created_at: datetime

class CampaignRunResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    run_at: datetime
    leads_total: int
    leads_processed: int
    has_failed_items: bool
    status: str
    failure_reason: Optional[str] = None
    created_at: datetime
    campaigns: Dict[str, Any] = Field(
        description="Campaign details including name and type. Example: {'name': 'Q4 Sales Campaign', 'type': 'email'}"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "campaign_id": "123e4567-e89b-12d3-a456-426614174001",
                "run_at": "2024-03-15T00:00:00Z",
                "leads_total": 100,
                "leads_processed": 50,
                "has_failed_items": False,
                "status": "running",
                "created_at": "2024-03-15T00:00:00Z",
                "campaigns": {
                    "name": "Q4 Sales Campaign",
                    "type": "email"
                }
            }
        }

class CampaignGenerationRequest(BaseModel):
    achievement_text: str

class CampaignGenerationResponse(BaseModel):
    campaign_name: str
    description: str
    email_subject: str
    email_body: str

# Leads upload response model
class LeadsUploadResponse(BaseModel):
    message: str
    leads_saved: int
    leads_skipped: int
    unmapped_headers: List[str]

class CronofyAuthResponse(BaseModel):
    message: str

class HiringPosition(BaseModel):
    title: str
    url: Optional[str]
    location: Optional[str]
    date: Optional[str]

class LocationMove(BaseModel):
    from_: dict = Field(..., alias="from")
    to: dict
    date: Optional[str]

class JobChange(BaseModel):
    previous: dict
    new: dict
    date: Optional[str]

class CreateLeadRequest(BaseModel):
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    company: str
    phone_number: Optional[str] = None
    website: str
    company_size: Optional[str] = None
    job_title: Optional[str] = None
    lead_source: Optional[str] = None
    education: Optional[str] = None
    personal_linkedin_url: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    mobile: Optional[str] = None
    direct_phone: Optional[str] = None
    office_phone: Optional[str] = None
    hq_location: Optional[str] = None
    headcount: Optional[int] = None
    industries: Optional[List[str]] = None
    department: Optional[str] = None
    sic_code: Optional[str] = None
    isic_code: Optional[str] = None
    naics_code: Optional[str] = None
    company_address: Optional[str] = None
    company_city: Optional[str] = None
    company_zip: Optional[str] = None
    company_state: Optional[str] = None
    company_country: Optional[str] = None
    company_hq_address: Optional[str] = None
    company_hq_city: Optional[str] = None
    company_hq_zip: Optional[str] = None
    company_hq_state: Optional[str] = None
    company_hq_country: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    company_type: Optional[str] = None
    company_description: Optional[str] = None
    technologies: Optional[List[str]] = None
    financials: Optional[Union[Dict[str, Any], str, int, float]] = None
    company_founded_year: Optional[int] = None
    seniority: Optional[str] = None
    hiring_positions: Optional[List[Dict[str, Any]]] = None
    location_move: Optional[Dict[str, Any]] = None
    job_change: Optional[Dict[str, Any]] = None

class LeadDetail(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    first_name: Optional[str]
    last_name: Optional[str]
    email: str
    company: Optional[str]
    phone_number: str
    company_size: Optional[str]
    job_title: Optional[str]
    lead_source: Optional[str]
    education: Optional[str]
    personal_linkedin_url: Optional[str]
    country: Optional[str]
    city: Optional[str]
    state: Optional[str]
    mobile: Optional[str]
    direct_phone: Optional[str]
    office_phone: Optional[str]
    hq_location: Optional[str]
    website: Optional[str]
    headcount: Optional[int]
    industries: Optional[List[str]]
    department: Optional[str]
    sic_code: Optional[str]
    isic_code: Optional[str]
    naics_code: Optional[str]
    company_address: Optional[str]
    company_city: Optional[str]
    company_zip: Optional[str]
    company_state: Optional[str]
    company_country: Optional[str]
    company_hq_address: Optional[str]
    company_hq_city: Optional[str]
    company_hq_zip: Optional[str]
    company_hq_state: Optional[str]
    company_hq_country: Optional[str]
    company_linkedin_url: Optional[str]
    company_type: Optional[str]
    company_description: Optional[str]
    technologies: Optional[List[str]]
    financials: Optional[Union[Dict[str, Any], str, int, float]] = None
    company_founded_year: Optional[int]
    seniority: Optional[str]
    hiring_positions: Optional[List[HiringPosition]]
    location_move: Optional[LocationMove]
    job_change: Optional[JobChange]
    enriched_data: Optional[Dict[str, Any]] = None

    @field_validator('financials')
    def validate_financials(cls, v):
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, (int, float)):
            return {"value": str(v)}
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {"value": v}
        return {"value": str(v)}

class LeadResponse(BaseModel):
    status: str
    data: LeadDetail

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "company_id": "123e4567-e89b-12d3-a456-426614174001",
                    "name": "John Doe",
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john.doe@example.com",
                    "company": "Example Corp",
                    "phone_number": "+1234567890",
                    "company_size": "1000-5000",
                    "job_title": "CTO",
                    "lead_source": "LinkedIn",
                    "education": "MS Computer Science",
                    "personal_linkedin_url": "https://linkedin.com/in/johndoe",
                    "country": "United States",
                    "city": "San Francisco",
                    "state": "CA",
                    "mobile": "+1234567890",
                    "direct_phone": "+1234567891",
                    "office_phone": "+1234567892",
                    "hq_location": "San Francisco, CA",
                    "website": "https://example.com",
                    "headcount": 3500,
                    "industries": ["Technology", "Software"],
                    "department": "Engineering",
                    "sic_code": "7371",
                    "isic_code": "J6201",
                    "naics_code": "541511",
                    "company_address": "123 Main St",
                    "company_city": "San Francisco",
                    "company_zip": "94105",
                    "company_state": "CA",
                    "company_country": "United States",
                    "company_hq_address": "123 Main St",
                    "company_hq_city": "San Francisco",
                    "company_hq_zip": "94105",
                    "company_hq_state": "CA",
                    "company_hq_country": "United States",
                    "company_linkedin_url": "https://linkedin.com/company/example",
                    "company_type": "Public",
                    "company_description": "Leading provider of software solutions",
                    "technologies": ["React", "Python", "AWS"],
                    "financials": {"revenue": "$500M", "funding": "$50M"},
                    "company_founded_year": 2005,
                    "seniority": "Executive",
                    "enriched_data": {
                        "pain_points": ["Legacy system migration", "Security compliance", "Scaling challenges"],
                        "needs": ["Cloud migration", "DevOps automation", "Security enhancement"],
                        "motivations": ["Increasing developer productivity", "Reducing operational costs", "Improving security posture"],
                        "decision_factors": ["Performance", "Reliability", "Cost", "Ease of implementation"]
                    }
                }
            }
        }

class AccountCredentialsUpdate(BaseModel):
    account_email: str = Field(..., description="Email address for the account", min_length=1)
    account_password: str = Field(..., description="Password for the account", min_length=1)
    type: str = Field(..., description="Type of account (e.g., 'gmail')")

    class Config:
        json_schema_extra = {
            "example": {
                "account_email": "example@gmail.com",
                "account_password": "your_secure_password",
                "type": "gmail"
            }
        }

class EmailVerificationRequest(BaseModel):
    token: str

class EmailVerificationResponse(BaseModel):
    message: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ResetPasswordResponse(BaseModel):
    message: str

class EmailLogResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    lead_id: UUID
    sent_at: datetime
    campaign_name: Optional[str] = None
    lead_name: Optional[str] = None
    lead_email: Optional[str] = None
    has_opened: bool
    has_replied: bool
    has_meeting_booked: bool

class PaginatedEmailLogResponse(BaseModel):
    items: List[EmailLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class EmailLogDetailResponse(BaseModel):
    message_id: Optional[str]
    email_subject: Optional[str]
    email_body: Optional[str]
    sender_type: str
    sent_at: datetime
    created_at: datetime
    from_name: Optional[str]
    from_email: Optional[str]
    to_email: Optional[str]

class InviteTokenResponse(BaseModel):
    email: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@hotmail.com"
            }
        }

class EmailMessage(BaseModel):
    message_id: Optional[str]
    email_subject: Optional[str]
    email_body: Optional[str]
    sender_type: str
    sent_at: datetime
    created_at: datetime
    from_name: Optional[str]
    from_email: Optional[str]
    to_email: Optional[str]

class EmailHistoryDetail(BaseModel):
    id: UUID
    campaign_id: UUID
    campaign_name: str
    product_name: Optional[str]
    sent_at: datetime
    has_opened: bool
    has_replied: bool
    has_meeting_booked: bool
    messages: List[EmailMessage]

class CallHistoryDetail(BaseModel):
    id: UUID
    campaign_id: UUID
    campaign_name: str
    product_name: Optional[str]
    duration: Optional[int]
    sentiment: Optional[str]
    summary: Optional[str]
    bland_call_id: Optional[str]
    has_meeting_booked: bool
    transcripts: Optional[List[Dict[str, Any]]]
    created_at: datetime

class LeadCommunicationHistory(BaseModel):
    email_history: List[EmailHistoryDetail]
    call_history: List[CallHistoryDetail]

class LeadSearchData(BaseModel):
    lead: LeadDetail
    communication_history: LeadCommunicationHistory

class LeadSearchResponse(BaseModel):
    status: str
    data: LeadSearchData

class CompanyUserResponse(BaseModel):
    name: Optional[str]
    email: str
    role: str
    user_company_profile_id: UUID
    is_owner: bool

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "role": "admin",
                "user_company_profile_id": "123e4567-e89b-12d3-a456-426614174000",
                "is_owner": True
            }
        }

class CallScriptResponse(BaseModel):
    status: str
    data: dict

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": {
                    "script": "Alex: Hello this is Alex, I am calling on behalf of Acme Inc. Do you have a bit of time?\nProspect: Yes, what is this about?\nAlex: Great to hear from you! I'm reaching out because..."
                }
            }
        }

class EmailScriptResponse(BaseModel):
    status: str
    data: dict

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": {
                    "subject": "Transform Your Outreach with Our AI-Powered Solution",
                    "body": "<p>Hello John,</p><p>I noticed that ACME Corp has been expanding its customer acquisition efforts, and thought you might be interested in learning how our AI-powered outreach platform can help streamline your sales process.</p><p>Our solution can help you:</p><ul><li>Reduce response time by 40%</li><li>Increase conversion rates by 25%</li><li>Save your team 15+ hours per week</li></ul><p>Would you be available for a quick 15-minute call next week to discuss how we might help ACME Corp achieve its growth goals?</p><p>Best regards,<br>Jane Smith</p>"
                }
            }
        }

class EmailThrottleSettings(BaseModel):
    max_emails_per_hour: int = Field(500, ge=1, le=1000, description="Maximum number of emails to send per hour")
    max_emails_per_day: int = Field(500, ge=1, le=10000, description="Maximum number of emails to send per day")
    enabled: bool = Field(True, description="Whether throttling is enabled")

    class Config:
        json_schema_extra = {
            "example": {
                "max_emails_per_hour": 500,
                "max_emails_per_day": 500,
                "enabled": True
            }
        }

# Do Not Email Models
class DoNotEmailRequest(BaseModel):
    email: EmailStr
    reason: str

class DoNotEmailResponse(BaseModel):
    success: bool
    message: str

class DoNotEmailEntry(BaseModel):
    id: UUID
    email: str
    reason: str
    company_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class DoNotEmailListResponse(BaseModel):
    items: List[DoNotEmailEntry]
    total: int
    page: int
    page_size: int
    total_pages: int

# Web Agent Models
class AnalysisSchema(BaseModel):
    """Schema for the analysis data collected from conversations"""
    prospect_name: Optional[str] = None
    company_name: Optional[str] = None
    current_outreach_method: Optional[str] = None
    pain_points: Optional[str] = None
    interested_in_demo: Optional[bool] = None
    email_address: Optional[str] = None
    preferred_demo_date: Optional[str] = None

class WebAgentMetadata(BaseModel):
    """Metadata for web agent"""
    source: str
    version: str
    user_id: Optional[str] = None

class WebAgentData(BaseModel):
    """Data model for web agent configuration"""
    prompt: str
    voice: str = "lucy"
    webhook: str
    analysis_schema: Dict[str, str]
    metadata: WebAgentMetadata
    language: str = "ENG"
    model: str = "enhanced"
    first_sentence: Optional[str] = None
    interruption_threshold: int = 120
    keywords: List[str] = []
    max_duration: int = 15

class AgentCreateResponse(BaseModel):
    """Response model for agent creation"""
    status: str
    message: str
    agent_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class WebhookResponse(BaseModel):
    """Response model for webhook endpoint"""
    status: str
    message: str
    agent_id: Optional[str] = None
    session_id: Optional[str] = None

class AgentSession(BaseModel):
    """Model for agent session data"""
    id: UUID
    agent_id: str
    user_id: UUID
    session_token: str
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    analysis: Optional[AnalysisSchema] = None

    class Config:
        from_attributes = True

class PartnershipType(str, Enum):
    RESELLER = "RESELLER"
    REFERRAL = "REFERRAL"
    TECHNOLOGY = "TECHNOLOGY"

class ApplicationStatus(str, Enum):
    PENDING = "PENDING"
    REVIEWING = "REVIEWING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class CompanySizeRange(str, Enum):
    TINY = "1-10"
    SMALL = "11-50"
    MEDIUM = "51-200"
    LARGE = "201-500"
    ENTERPRISE = "501+"

class PartnerApplicationBase(BaseModel):
    company_name: str
    contact_name: str
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    partnership_type: PartnershipType
    company_size: CompanySizeRange
    industry: str
    current_solutions: Optional[str] = None
    target_market: Optional[str] = None
    motivation: str
    additional_information: Optional[str] = None

class PartnerApplicationCreate(PartnerApplicationBase):
    """Model for creating a new partner application"""
    pass

class PartnerApplicationUpdate(BaseModel):
    """Model for updating an application's status"""
    status: ApplicationStatus

class PartnerApplicationNoteCreate(BaseModel):
    """Model for creating a new note on a partner application"""
    author_name: str
    note: str

class PartnerApplicationNote(PartnerApplicationNoteCreate):
    """Model for partner application note responses"""
    id: UUID
    application_id: UUID
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "application_id": "123e4567-e89b-12d3-a456-426614174001",
                "author_name": "John Doe",
                "note": "This company looks like a good fit for our referral program.",
                "created_at": "2023-01-01T12:00:00Z"
            }
        }
        from_attributes = True

class PartnerApplicationResponse(PartnerApplicationBase):
    """Model for partner application responses"""
    id: UUID
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime
    notes: Optional[List[PartnerApplicationNote]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "company_name": "Acme Corp",
                "contact_name": "John Doe",
                "contact_email": "john@acmecorp.com",
                "contact_phone": "+1-555-123-4567",
                "website": "https://acmecorp.com",
                "partnership_type": "RESELLER",
                "company_size": "11-50",
                "industry": "Technology",
                "current_solutions": "Currently using multiple CRM tools",
                "target_market": "SMB technology companies",
                "motivation": "Looking to expand product offerings for our clients",
                "additional_information": "We have a team of 5 sales reps",
                "status": "PENDING",
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-01T12:00:00Z",
                "notes": []
            }
        }
        from_attributes = True

class PartnerApplicationListResponse(BaseModel):
    """Model for paginated partner application list responses"""
    items: List[PartnerApplicationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    class Config:
        from_attributes = True

class PartnerApplicationStats(BaseModel):
    """Model for partner application statistics"""
    total_applications: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
    recent_applications: int  # Last 30 days
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_applications": 150,
                "by_status": {
                    "PENDING": 45,
                    "REVIEWING": 25,
                    "APPROVED": 50,
                    "REJECTED": 30
                },
                "by_type": {
                    "RESELLER": 75,
                    "REFERRAL": 50,
                    "TECHNOLOGY": 25
                },
                "recent_applications": 35
            }
        }
        from_attributes = True

class SimplePartnerApplicationResponse(BaseModel):
    """Model for minimal partner application creation response"""
    id: UUID
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "message": "Your partnership application has been submitted successfully. We will contact you soon."
            }
        }
        from_attributes = True

# Do Not Email Bulk Import Models
class DoNotEmailBulkImportResponse(BaseModel):
    message: str
    emails_saved: int
    emails_skipped: int
    unmapped_headers: List[str]

class EmailQueueItem(BaseModel):
    id: UUID
    company_id: UUID
    campaign_id: UUID
    campaign_run_id: UUID
    lead_id: UUID
    subject: str
    email_body: str
    status: str
    priority: int
    retry_count: int
    max_retries: int
    error_message: Optional[str]
    created_at: datetime
    scheduled_for: Optional[datetime]
    processed_at: Optional[datetime]
    lead_name: Optional[str]
    lead_email: Optional[str]

class PaginatedEmailQueueResponse(BaseModel):
    items: List[EmailQueueItem]
    total: int
    page: int
    page_size: int
    total_pages: int

class CampaignRetryResponse(BaseModel):
    """Response model for campaign retry endpoint"""
    message: str
    campaign_run_id: UUID
    status: str = "initiated"

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Campaign retry initiated successfully",
                "campaign_run_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "initiated"
            }
        }

class CallQueueItem(BaseModel):
    id: UUID
    company_id: UUID
    campaign_id: UUID
    campaign_run_id: UUID
    lead_id: UUID
    status: str
    call_script: Optional[str]
    priority: int
    retry_count: int
    max_retries: int
    error_message: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]
    lead_name: Optional[str]
    lead_phone: Optional[str]

class PaginatedCallQueueResponse(BaseModel):
    items: List[CallQueueItem]
    total: int
    page: int
    page_size: int
    total_pages: int

class PaginatedCampaignRunResponse(BaseModel):
    items: List[CampaignRunResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class CallQueueRetryResponse(BaseModel):
    """Response model for call queue retry endpoint"""
    message: str
    queue_id: UUID
    status: str = "initiated"

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Call queue item retry initiated successfully",
                "queue_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "initiated"
            }
        }

class AccountEmailCheckResponse(BaseModel):
    exists: bool = Field(..., description="Whether the account email exists in other companies")
    message: str = Field(..., description="Descriptive message about the result")

    class Config:
        json_schema_extra = {
            "example": {
                "exists": True,
                "message": "Account email already exists in another company"
            }
        }

class UploadTaskResponse(BaseModel):
    id: UUID
    company_id: UUID
    user_id: UUID
    file_name: str
    type: str
    status: str
    result: Optional[Union[Dict[str, Any], str]] = None
    created_at: datetime

    @field_validator('result', mode='before')
    @classmethod
    def validate_result(cls, v: str) -> Optional[Union[Dict[str, Any], str]]:
        if not v:
            return v
        try:
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return v

class PaginatedUploadTaskResponse(BaseModel):
    items: List[UploadTaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "company_id": "123e4567-e89b-12d3-a456-426614174001",
                        "user_id": "123e4567-e89b-12d3-a456-426614174002",
                        "file_name": "leads_march_2024.csv",
                        "type": "leads",
                        "status": "completed",
                        "result": {
                            "leads_saved": 2,
                            "leads_skipped": 5,
                            "unmapped_headers": []
                        },
                        "created_at": "2024-01-01T12:00:00Z"
                    },
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174003",
                        "company_id": "123e4567-e89b-12d3-a456-426614174001",
                        "user_id": "123e4567-e89b-12d3-a456-426614174002",
                        "file_name": "do_not_email_list.csv",
                        "type": "do_not_email",
                        "status": "failed",
                        "result": "Invalid file format",
                        "created_at": "2024-01-01T12:00:00Z"
                    }
                ],
                "total": 50,
                "page": 1,
                "page_size": 20,
                "total_pages": 3
            }
        }

class SkippedRowResponse(BaseModel):
    id: UUID
    upload_task_id: UUID
    category: str
    row_data: Union[Dict[str, Any], str]
    created_at: datetime

    @field_validator('row_data', mode='before')
    @classmethod
    def validate_row_data(cls, v: str) -> Union[Dict[str, Any], str]:
        if not v:
            return v
        try:
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return v

class PaginatedSkippedRowResponse(BaseModel):
    items: List[SkippedRowResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "upload_task_id": "123e4567-e89b-12d3-a456-426614174001",
                        "category": "missing_name",
                        "row_data": {
                            "email": "test@example.com",
                            "company": "Test Corp"
                        },
                        "created_at": "2024-01-01T12:00:00Z"
                    }
                ],
                "total": 50,
                "page": 1,
                "page_size": 20,
                "total_pages": 3
            }
        }
 