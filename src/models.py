from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID

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
 