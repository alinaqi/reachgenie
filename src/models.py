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
    phone_number: str
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

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class BlandWebhookPayload(BaseModel):
    call_id: str
    summary: Optional[str] = None
    corrected_duration: str
    analysis: dict
    transcripts: list[dict]
    recording_url: Optional[str] = None

class CampaignType(str, Enum):
    EMAIL = 'email'
    CALL = 'call'

class EmailCampaignBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: CampaignType = CampaignType.EMAIL
    product_id: UUID
    template: Optional[str] = None

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
    status: str
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

# Lead response models
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

    @validator('financials', pre=True)
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
                    "headcount": 1500,
                    "industries": ["Technology", "Software"],
                    "department": "Engineering",
                    "sic_code": "7371",
                    "isic_code": "6201",
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
                    "company_description": "Leading software company",
                    "technologies": ["Python", "React", "AWS"],
                    "financials": {
                        "revenue": "$100M-$500M",
                        "funding": "$50M Series C"
                    },
                    "company_founded_year": 2010,
                    "seniority": "Executive",
                    "hiring_positions": [
                        {
                            "title": "Senior Engineer",
                            "url": "https://example.com/jobs/123",
                            "location": "San Francisco, CA",
                            "date": "2024-01-01"
                        }
                    ],
                    "location_move": {
                        "from": {
                            "country": "Canada",
                            "state": "ON"
                        },
                        "to": {
                            "country": "United States",
                            "state": "CA"
                        },
                        "date": "2023-12-01"
                    },
                    "job_change": {
                        "previous": {
                            "company": "Previous Corp",
                            "title": "Engineering Manager"
                        },
                        "new": {
                            "company": "Example Corp",
                            "title": "CTO"
                        },
                        "date": "2024-01-01"
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

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "role": "admin",
                "user_company_profile_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }
 