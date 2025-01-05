from pydantic import BaseModel, EmailStr
from typing import Optional
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
    email: EmailStr
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

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None 