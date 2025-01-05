from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from datetime import timedelta
import csv
import io
from typing import List
from uuid import UUID

from src.models import (
    UserCreate, CompanyCreate, ProductCreate, LeadCreate,
    CompanyInDB, ProductInDB, LeadInDB, CallInDB, Token
)
from src.database import (
    create_user,
    get_user_by_email,
    db_create_company,
    get_companies_by_user_id,
    db_create_product,
    get_products_by_company,
    create_lead,
    get_leads_by_company,
    create_call,
    get_call_summary,
    get_lead_by_id,
    get_product_by_id,
    update_call_details,
    get_company_by_id
)
from src.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, settings
)
from src.perplexity_enrichment import PerplexityEnricher
from src.config import get_settings
from src.bland_client import BlandClient

app = FastAPI(
    title="Outbound AI SDR API",
    description="API for SDR automation with AI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
        
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Authentication endpoints
@app.post("/api/auth/signup", response_model=dict)
async def signup(user: UserCreate):
    db_user = await get_user_by_email(user.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    hashed_password = get_password_hash(user.password)
    await create_user(user.email, hashed_password)
    return {"message": "Account created successfully"}

@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/reset-password")
async def reset_password(email: str):
    # Implementation for password reset (would typically send an email)
    return {"message": "Password reset link sent"}

# Company Management endpoints
@app.post(
    "/api/companies", 
    response_model=CompanyInDB
)
async def create_company(
    company: CompanyCreate,
    current_user: dict = Depends(get_current_user)
):
    return await db_create_company(
        current_user["id"],
        company.name,
        company.address,
        company.industry
    )

@app.post("/api/companies/{company_id}/products", response_model=ProductInDB)
async def create_product(
    company_id: UUID,
    product: ProductCreate,
    current_user: dict = Depends(get_current_user)
):
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    return await db_create_product(company_id, product.product_name, product.description)

@app.get("/api/companies/{company_id}/products", response_model=List[ProductInDB])
async def get_products(
    company_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    return await get_products_by_company(company_id)

@app.get("/api/companies", response_model=List[CompanyInDB])
async def get_companies(current_user: dict = Depends(get_current_user)):
    return await get_companies_by_user_id(current_user["id"])

# Lead Management endpoints
@app.post("/api/companies/{company_id}/leads/upload")
async def upload_leads(
    company_id: UUID,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    contents = await file.read()
    csv_data = csv.DictReader(io.StringIO(contents.decode()))
    lead_count = 0
    
    # Initialize Perplexity enricher
    settings = get_settings()
    enricher = PerplexityEnricher(settings.perplexity_api_key)
    
    for row in csv_data:
        lead_data = {
            "name": row.get("name"),
            "email": row.get("email"),
            "company": row.get("company"),
            "phone_number": row.get("phone_number"),
            "company_size": row.get("company_size"),
            "job_title": row.get("job_title"),
            "company_facebook": row.get("company_facebook"),
            "company_twitter": row.get("company_twitter"),
            "company_revenue": row.get("company_revenue")
        }
        
        # Enrich lead data with Perplexity if any required fields are missing
        if not all([lead_data.get(field) for field in ["email","phone_number","job_title", "company_size", "company_revenue","company_facebook","company_twitter"]]):
            lead_data = await enricher.enrich_lead_data(lead_data)
        
        await create_lead(company_id, lead_data)
        lead_count += 1
    
    return {"message": "Leads uploaded successfully", "lead_count": lead_count}

@app.get("/api/companies/{company_id}/leads", response_model=List[LeadInDB])
async def get_leads(
    company_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    return await get_leads_by_company(company_id)

# Calling functionality endpoints
@app.post("/api/calls/start", response_model=CallInDB)
async def start_call(
    lead_id: UUID,
    product_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    # Get user's companies
    user_companies = await get_companies_by_user_id(current_user["id"])
    company_ids = [str(company["id"]) for company in user_companies]
    
    # Get the lead and product details
    lead = await get_lead_by_id(lead_id)
    if not lead or str(lead["company_id"]) not in company_ids:
        raise HTTPException(status_code=404, detail="Lead not found or unauthorized access")
        
    product = await get_product_by_id(product_id)
    if not product or str(product["company_id"]) not in company_ids:
        raise HTTPException(status_code=404, detail="Product not found or unauthorized access")
    
    # Get company details
    company = await get_company_by_id(product["company_id"])
        
    # Generate the script based on product details
    script = f"""You are Alex, an AI sales representative at {company['name']} for {product['product_name']} 
    calling {lead['name']} about {product['product_name']}. 
    Your goal is to introduce the product to the lead and understand if there's interest.
    Key points about the product are: {product['description']}
    
    Start with a friendly introduction, explain the product briefly, and gauge interest.
    Be professional, friendly, and respect the person's time."""
    
    # Initialize Bland client and start the call
    settings = get_settings()
    bland_client = BlandClient(
        api_key=settings.bland_api_key,
        base_url=settings.bland_api_url,
        webhook_base_url=settings.webhook_base_url
    )
    
    try:
        bland_response = await bland_client.start_call(
            phone_number=lead['phone_number'],
            script=script
        )
        
        # Create call record in database
        call = await create_call(lead_id, product_id)
        
        # Update call with Bland call ID
        await update_call_details(call['id'], bland_call_id=bland_response['call_id'])
        
        return call
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate call: {str(e)}"
        )

@app.get("/api/calls/{call_id}", response_model=CallInDB)
async def get_call_details(
    call_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    call = await get_call_summary(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call 