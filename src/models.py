from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Union, Dict, Any
from datetime import datetime
from uuid import UUID
import json

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: UUID
    created_at: datetime

class CompanyBase(BaseModel):
    name: str
    address: Optional[str] = None
    industry: Optional[str] = None
    cronofy_provider: Optional[str] = None
    cronofy_linked_email: Optional[str] = None
    cronofy_default_calendar_name: Optional[str] = None
    cronofy_default_calendar_id: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyInDB(CompanyBase):
    id: UUID
    user_id: UUID

class ProductBase(BaseModel):
    product_name: str
    description: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductInDB(ProductBase):
    id: UUID
    company_id: UUID

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

class CallBase(BaseModel):
    lead_id: UUID
    product_id: UUID

class CallCreate(CallBase):
    pass

class CallInDB(CallBase):
    id: UUID
    duration: Optional[int] = None
    sentiment: Optional[str] = None
    summary: Optional[str] = None
    bland_call_id: Optional[str] = None
    lead_name: Optional[str] = None
    product_name: Optional[str] = None
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class BlandWebhookPayload(BaseModel):
    call_id: str
    summary: str
    corrected_duration: str
    analysis: dict

class EmailCampaignBase(BaseModel):
    name: str
    description: Optional[str] = None
    email_subject: str
    email_body: str

class EmailCampaignCreate(EmailCampaignBase):
    pass

class EmailCampaignInDB(EmailCampaignBase):
    id: UUID
    company_id: UUID
    created_at: datetime

# Campaign generation models
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
    account_email: str
    account_password: str
    type: str = Field(..., description="Type of account (e.g., 'gmail')")
 