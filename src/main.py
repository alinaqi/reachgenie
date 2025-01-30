from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone, timedelta
import csv
import io
import logging
from typing import List
from uuid import UUID
from openai import AsyncOpenAI
import json
import pycronofy
import uuid
from pydantic import BaseModel, EmailStr
from supabase import create_client, Client
from src.utils.smtp_client import SMTPClient
from src.utils.encryption import decrypt_password
from src.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, settings, request_password_reset, reset_password
)
from src.database import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    create_verification_token,
    get_valid_verification_token,
    mark_verification_token_used,
    mark_user_as_verified,
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
    get_company_by_id,
    update_call_webhook_data,
    get_calls_by_company_id,
    create_email_campaign,
    get_email_campaigns_by_company,
    get_email_campaign_by_id,
    get_leads_for_campaign,
    create_email_log,
    create_email_log_detail,
    update_company_cronofy_profile,
    clear_company_cronofy_data,
    update_product_details,
    create_upload_task,
    update_task_status,
    get_task_status,
    update_company_account_credentials,
    update_user
)
from src.services.email_service import email_service
from src.models import (
    UserCreate, CompanyCreate, ProductCreate,
    CompanyInDB, ProductInDB, LeadInDB, CallInDB, Token,
    BlandWebhookPayload, EmailCampaignCreate, EmailCampaignInDB,
    CampaignGenerationRequest, CampaignGenerationResponse,
    CronofyAuthResponse, LeadResponse,
    AccountCredentialsUpdate, UserUpdate, UserInDB,
    EmailVerificationRequest, EmailVerificationResponse,
    ResendVerificationRequest, ForgotPasswordRequest,
    ResetPasswordRequest, ResetPasswordResponse
)
from src.perplexity_enrichment import PerplexityEnricher
from src.config import get_settings
from src.bland_client import BlandClient
import secrets
from src.services.perplexity_service import perplexity_service

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TaskResponse(BaseModel):
    task_id: UUID
    message: str

app = FastAPI(
    title="Outbound AI SDR API",
    description="API for SDR automation with AI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

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
    created_user = await create_user(user.email, hashed_password)
    
    # Generate verification token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    await create_verification_token(created_user["id"], token, expires_at)
    
    # Send verification email
    try:
        user_name = created_user.get('name') or user.email.split('@')[0]
        await email_service.send_verification_email(user.email, token)
        logger.info(f"Verification email sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
        # Don't fail signup, but let user know they need to request a new verification email
        return {
            "message": "Account created successfully, but verification email could not be sent. Please use the resend verification endpoint."
        }
    
    return {"message": "Account created successfully. Please check your email to verify your account."}

@app.post("/api/auth/verify", response_model=EmailVerificationResponse)
async def verify_email(request: EmailVerificationRequest):
    token_data = await get_valid_verification_token(request.token)
    if not token_data:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token"
        )
    
    # Get user details before marking as verified
    user = await get_user_by_id(UUID(token_data["user_id"]))
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # Mark user as verified
    await mark_user_as_verified(UUID(token_data["user_id"]))
    
    # Mark token as used
    await mark_verification_token_used(request.token)
    
    # Send welcome email after successful verification
    try:
        user_name = user.get('name') or user['email'].split('@')[0]
        await email_service.send_welcome_email(user['email'], user_name)
        logger.info(f"Welcome email sent to {user['email']}")
    except Exception as e:
        # Log the error but don't fail the verification
        logger.error(f"Failed to send welcome email to {user['email']}: {str(e)}")
    
    return {"message": "Email verified successfully"}

@app.post("/api/auth/resend-verification", response_model=dict)
async def resend_verification(request: ResendVerificationRequest):
    user = await get_user_by_email(request.email)
    if not user:
        # Return success even if email doesn't exist to prevent email enumeration
        return {"message": "If your email is registered, you will receive a verification email"}
    
    if user["verified"]:
        return {"message": "Email is already verified"}
    
    # Generate new verification token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    await create_verification_token(user["id"], token, expires_at)
    
    # Send verification email
    try:
        user_name = user.get('name') or request.email.split('@')[0]
        await email_service.send_verification_email(request.email, token)
        logger.info(f"Verification email resent to {request.email}")
    except Exception as e:
        logger.error(f"Failed to resend verification email to {request.email}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to send verification email"
        )
    
    return {"message": "Verification email sent"}

@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is verified
    if not user["verified"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please verify your email before logging in",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user["email"]}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.patch("/api/users/me", response_model=UserInDB)
async def update_user_details(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update the authenticated user's details (name and/or password)
    """
    # Get current user from database to verify password
    user = await get_user_by_email(current_user["email"])
    
    if not user:
        logger.error(f"User not found for email: {current_user['email']}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prepare update data
    db_update = {}
    
    # Handle name update
    if update_data.name is not None:
        db_update["name"] = update_data.name
        
    # Handle password update
    if update_data.new_password is not None:
        # Verify old password
        if not verify_password(update_data.old_password, user["password_hash"]):
            logger.warning("Password verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Existing password is incorrect"
            )
        db_update["password_hash"] = get_password_hash(update_data.new_password)
    
    # If no fields to update, return early
    if not db_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )
    
    # Update user in database
    updated_user = await update_user(UUID(current_user["id"]), db_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return updated_user

@app.get("/api/users/me", response_model=UserInDB)
async def get_current_user_details(current_user: dict = Depends(get_current_user)):
    """
    Get details of the currently authenticated user
    """
    user = await get_user_by_email(current_user["email"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

# Company Management endpoints
@app.post(
    "/api/companies", 
    response_model=CompanyInDB
)
async def create_company(
    company: CompanyCreate,
    current_user: dict = Depends(get_current_user)
):
    # If website is provided, fetch additional information using Perplexity
    overview = None
    background = None
    products_services = None
    address = company.address
    industry = company.industry

    if company.website:
        try:
            company_info = await perplexity_service.fetch_company_info(company.website)
            if company_info:
                overview = company_info.get('overview')
                background = company_info.get('background')
                products_services = company_info.get('products_services')
                # Only update address and industry if not provided in the request
                if not address and company_info.get('address') != "Not available":
                    address = company_info.get('address')
                if not industry and company_info.get('industry') != "Not available":
                    industry = company_info.get('industry')
        except Exception as e:
            logger.error(f"Error fetching company info: {str(e)}")
            # Continue with company creation even if Perplexity fails

    return await db_create_company(
        current_user["id"],
        company.name,
        address,
        industry,
        company.website,
        overview,
        background,
        products_services
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
    return await db_create_product(company_id, product.product_name)

@app.get("/api/companies/{company_id}/products", response_model=List[ProductInDB])
async def get_products(
    company_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    return await get_products_by_company(company_id)

@app.put("/api/companies/{company_id}/products/{product_id}", response_model=ProductInDB)
async def update_product(
    company_id: UUID,
    product_id: UUID,
    product: ProductCreate,
    current_user: dict = Depends(get_current_user)
):
    # Verify company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Verify product exists and belongs to company
    existing_product = await get_product_by_id(product_id)
    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")
    if str(existing_product["company_id"]) != str(company_id):
        raise HTTPException(status_code=403, detail="Product does not belong to this company")
    
    return await update_product_details(product_id, product.product_name)

@app.get("/api/companies", response_model=List[CompanyInDB])
async def get_companies(current_user: dict = Depends(get_current_user)):
    return await get_companies_by_user_id(current_user["id"])

@app.get("/api/companies/{company_id}", response_model=CompanyInDB)
async def get_company(
    company_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    company = await get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return company

# Lead Management endpoints
@app.post("/api/companies/{company_id}/leads/upload", response_model=TaskResponse)
async def upload_leads(
    background_tasks: BackgroundTasks,
    company_id: UUID,
    current_user: dict = Depends(get_current_user),
    file: UploadFile = File(...)
):
    """
    Upload leads from CSV file. The processing will be done in the background.
    
    Args:
        background_tasks: FastAPI background tasks
        company_id: UUID of the company
        current_user: Current authenticated user
        file: CSV file containing lead data
        
    Returns:
        Task ID for tracking the upload progress
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        # Initialize Supabase client with service role
        settings = get_settings()
        supabase: Client = create_client(
            settings.supabase_url,
            settings.SUPABASE_SERVICE_KEY  
        )
        
        # Generate unique file name
        file_name = f"{company_id}/{uuid.uuid4()}.csv"
        
        # Read and upload file content
        file_content = await file.read()
        if isinstance(file_content, str):
            file_content = file_content.encode('utf-8')
        
        # Upload file to Supabase storage
        storage = supabase.storage.from_("leads-uploads")
        try:
            storage.upload(
                path=file_name,
                file=file_content,
                file_options={"content-type": "text/csv"}
            )
        except Exception as upload_error:
            logger.error(f"Storage upload error: {str(upload_error)}")
            raise HTTPException(status_code=500, detail="Failed to upload file to storage")
        
        # Create task record
        task_id = uuid.uuid4()
        await create_upload_task(task_id, company_id, current_user["id"], file_name)
        
        # Add background task
        background_tasks.add_task(
            process_leads_upload,
            company_id,
            file_name,
            current_user["id"],
            task_id
        )
        
        return TaskResponse(
            task_id=task_id,
            message="File upload started. Use the task ID to check the status."
        )
        
    except Exception as e:
        logger.error(f"Error starting leads upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/companies/{company_id}/leads", response_model=List[LeadInDB])
async def get_leads(
    company_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    return await get_leads_by_company(company_id)

@app.get("/api/companies/{company_id}/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(
    company_id: UUID,
    lead_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Get complete lead data by ID.
    
    Args:
        company_id: UUID of the company
        lead_id: UUID of the lead to retrieve
        current_user: Current authenticated user
        
    Returns:
        Complete lead data including all fields
        
    Raises:
        404: Lead not found
        403: User doesn't have access to this lead
    """
    # Get lead data
    lead = await get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check if lead belongs to the specified company
    if str(lead["company_id"]) != str(company_id):
        raise HTTPException(status_code=404, detail="Lead not found in this company")
    
    # Check if user has access to the company
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=403, detail="Not authorized to access this company")
    
    # Convert numeric fields to proper types if they're strings
    if lead.get("financials"):
        if isinstance(lead["financials"], str):
            try:
                lead["financials"] = json.loads(lead["financials"])
            except json.JSONDecodeError:
                lead["financials"] = {"value": lead["financials"]}
        elif isinstance(lead["financials"], (int, float)):
            lead["financials"] = {"value": str(lead["financials"])}
        elif not isinstance(lead["financials"], dict):
            lead["financials"] = {"value": str(lead["financials"])}
    
    if lead.get("industries"):
        if isinstance(lead["industries"], str):
            lead["industries"] = [ind.strip() for ind in lead["industries"].split(",")]
        elif not isinstance(lead["industries"], list):
            lead["industries"] = [str(lead["industries"])]
    
    if lead.get("technologies"):
        if isinstance(lead["technologies"], str):
            lead["technologies"] = [tech.strip() for tech in lead["technologies"].split(",")]
        elif not isinstance(lead["technologies"], list):
            lead["technologies"] = [str(lead["technologies"])]
    
    if lead.get("hiring_positions"):
        if isinstance(lead["hiring_positions"], str):
            try:
                lead["hiring_positions"] = json.loads(lead["hiring_positions"])
            except json.JSONDecodeError:
                lead["hiring_positions"] = []
        elif not isinstance(lead["hiring_positions"], list):
            lead["hiring_positions"] = []
    
    if lead.get("location_move"):
        if isinstance(lead["location_move"], str):
            try:
                lead["location_move"] = json.loads(lead["location_move"])
            except json.JSONDecodeError:
                lead["location_move"] = None
        elif not isinstance(lead["location_move"], dict):
            lead["location_move"] = None
    
    if lead.get("job_change"):
        if isinstance(lead["job_change"], str):
            try:
                lead["job_change"] = json.loads(lead["job_change"])
            except json.JSONDecodeError:
                lead["job_change"] = None
        elif not isinstance(lead["job_change"], dict):
            lead["job_change"] = None
    
    return {
        "status": "success",
        "data": lead
    }


# Calling functionality endpoints
@app.post("/api/companies/{company_id}/calls/start", response_model=CallInDB)
async def start_call(
    company_id: UUID,
    lead_id: UUID,
    product_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get the lead and product details
    lead = await get_lead_by_id(lead_id)
    if not lead or str(lead["company_id"]) != str(company_id):
        raise HTTPException(status_code=404, detail="Lead not found or does not belong to this company")
        
    product = await get_product_by_id(product_id)
    if not product or str(product["company_id"]) != str(company_id):
        raise HTTPException(status_code=404, detail="Product not found or does not belong to this company")
    
    # Get company details
    company = await get_company_by_id(company_id)
        
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
        
        # Create call record in database with company_id
        call = await create_call(lead_id, product_id, company_id)
        
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

@app.post("/api/calls/webhook")
async def handle_bland_webhook(payload: BlandWebhookPayload):
    try:
        # Extract required fields from the payload
        bland_call_id = payload.call_id
        duration = payload.corrected_duration
        sentiment = payload.analysis.get('sentiment', 'neutral')
        summary = payload.summary
        
        # Update the call record in the database
        updated_call = await update_call_webhook_data(
            bland_call_id=bland_call_id,
            duration=duration,
            sentiment=sentiment,
            summary=summary
        )
        
        if not updated_call:
            raise HTTPException(
                status_code=404,
                detail="Call record not found"
            )
            
        return {"status": "success", "message": "Call details updated"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}"
        ) 

@app.get("/api/companies/{company_id}/calls", response_model=List[CallInDB])
async def get_company_calls(
    company_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    return await get_calls_by_company_id(company_id)

@app.post("/api/companies/{company_id}/email-campaigns", response_model=EmailCampaignInDB)
async def create_company_email_campaign(
    company_id: UUID,
    campaign: EmailCampaignCreate,
    current_user: dict = Depends(get_current_user)
):
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    return await create_email_campaign(
        company_id=company_id,
        name=campaign.name,
        description=campaign.description,
        email_subject=campaign.email_subject,
        email_body=campaign.email_body
    )

@app.get("/api/companies/{company_id}/email-campaigns", response_model=List[EmailCampaignInDB])
async def get_company_email_campaigns(
    company_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    return await get_email_campaigns_by_company(company_id)

@app.get("/api/email-campaigns/{campaign_id}", response_model=EmailCampaignInDB)
async def get_email_campaign(
    campaign_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    # Get the campaign
    campaign = await get_email_campaign_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Email campaign not found")
    
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(campaign["company_id"]) for company in companies):
        raise HTTPException(status_code=404, detail="Email campaign not found")
    
    return campaign 

async def send_campaign_emails(campaign_id: UUID):
    """Background task to send campaign emails"""
    logger.info(f"Starting to send campaign emails for campaign_id: {campaign_id}")
    settings = get_settings()
    
    try:
        # Get campaign details
        campaign = await get_email_campaign_by_id(campaign_id)
        if not campaign:
            logger.error(f"Campaign not found: {campaign_id}")
            return
        
        # Get company details for SMTP configuration
        company = await get_company_by_id(campaign["company_id"])
        if not company:
            logger.error(f"Company not found for campaign: {campaign_id}")
            return
        
        if not company.get("account_email") or not company.get("account_password"):
            logger.error(f"Company {campaign['company_id']} missing email credentials")
            return
            
        if not company.get("account_type"):
            logger.error(f"Company {campaign['company_id']} missing email provider type")
            return
            
        if not company.get("name"):
            logger.error(f"Company {campaign['company_id']} missing company name")
            return
        
        # Decrypt the password
        try:
            decrypted_password = decrypt_password(company["account_password"])
        except Exception as e:
            logger.error(f"Failed to decrypt email password: {str(e)}")
            return
        
        # Initialize SMTP client
        try:
            async with SMTPClient(
                account_email=company["account_email"],
                account_password=decrypted_password,  # Use decrypted password
                provider=company["account_type"]
            ) as smtp_client:
                # Get all leads for the campaign
                leads = await get_leads_for_campaign(campaign_id)
                logger.info(f"Found {len(leads)} leads for campaign")
                
                # Send emails to each lead
                for lead in leads:
                    try:
                        if lead.get('email'):  # Only send if lead has email
                            logger.info(f"Processing email for lead: {lead['email']}")
                            
                            # Send email using SMTP client
                            try:
                                # Create email log first to get the ID for reply-to
                                email_log = await create_email_log(
                                    campaign_id=campaign_id,
                                    lead_id=lead['id'],
                                    sent_at=datetime.now(timezone.utc)
                                )
                                logger.info(f"Created email_log with id: {email_log['id']}")

                                # Send email with reply-to header
                                await smtp_client.send_email(
                                    to_email=lead['email'],
                                    subject=campaign['email_subject'],
                                    html_content=campaign['email_body'],
                                    from_name=company["name"],
                                    email_log_id=email_log['id']
                                )
                                logger.info(f"Successfully sent email to {lead['email']}")
                                
                                # Create email log detail
                                if email_log:
                                    await create_email_log_detail(
                                        email_logs_id=email_log['id'],
                                        message_id=None,
                                        email_subject=campaign['email_subject'],
                                        email_body=campaign['email_body'],
                                        sender_type='assistant',
                                        sent_at=datetime.now(timezone.utc),
                                        from_name=company['name'],
                                        from_email=company['account_email'],
                                        to_email=lead['email']
                                    )
                                    logger.info(f"Created email log detail for email_log_id: {email_log['id']}")
                            except Exception as e:
                                logger.error(f"Error creating email logs: {str(e)}")
                                continue
                            
                    except Exception as e:
                        logger.error(f"Failed to process email for {lead.get('email')}: {str(e)}")
                        continue
        except Exception as e:
            logger.error(f"Failed to initialize SMTP client: {str(e)}")
            return
            
    except Exception as e:
        logger.error(f"Unexpected error in send_campaign_emails: {str(e)}")
        return

@app.post("/api/email-campaigns/{campaign_id}/run")
async def run_email_campaign(
    campaign_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    logger.info(f"Running email campaign {campaign_id}")
    
    # Get the campaign
    campaign = await get_email_campaign_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Email campaign not found")
    
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(campaign["company_id"]) for company in companies):
        raise HTTPException(status_code=404, detail="Email campaign not found")
    
    # Get company details and validate email credentials
    company = await get_company_by_id(campaign["company_id"])
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    if not company.get("account_email") or not company.get("account_password"):
        logger.error(f"Company {campaign['company_id']} missing credentials - email: {company.get('account_email')!r}, has_password: {bool(company.get('account_password'))}")
        raise HTTPException(
            status_code=400,
            detail="Company email credentials not configured. Please set up email account credentials first."
        )
        
    if not company.get("account_type"):
        raise HTTPException(
            status_code=400,
            detail="Email provider type not configured. Please set up email provider type first."
        )
    
    # Add email sending to background tasks
    background_tasks.add_task(send_campaign_emails, campaign_id)
    
    return {"message": "Email campaign started successfully"} 

@app.post("/api/generate-campaign", response_model=CampaignGenerationResponse)
async def generate_campaign(
    request: CampaignGenerationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate campaign content using OpenAI based on achievement text."""
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    prompt = f"""Based on the following achievement or success story, generate compelling campaign content.
    
    Achievement: {request.achievement_text}
    
    Generate four components and return them in a JSON object with the following structure:
    {{
        "campaign_name": "A short, memorable name for the campaign (3-5 words)",
        "description": "A brief campaign description (2-3 sentences)",
        "email_subject": "An attention-grabbing email subject line (1 line)",
        "email_body": "A persuasive email body (2-3 paragraphs)"
    }}

    Important guidelines:
    1. Do not use any placeholders or variables (e.g., no [Name], [Company], etc.)
    2. Write the content in a way that works without personalization
    3. Use inclusive language that works for any recipient
    4. For email body, write complete content that can be sent as-is without any modifications
    5. For company references, use general terms like 'we', 'our team', or 'our company'
    6. The campaign name should be concise and memorable, reflecting the achievement or offer

    Ensure the response is a valid JSON object with these exact field names.
    Do not include any other text or formatting outside the JSON object."""
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert marketing copywriter specializing in B2B campaigns. Generate content without placeholders or variables that would need replacement. Always respond with valid JSON."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
            response_format={ "type": "json_object" }
        )
        
        content = response.choices[0].message.content.strip()
        campaign_content = json.loads(content)
        
        return CampaignGenerationResponse(
            campaign_name=campaign_content["campaign_name"],
            description=campaign_content["description"],
            email_subject=campaign_content["email_subject"],
            email_body=campaign_content["email_body"]
        )
        
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON response: {str(e)}")
        logging.error(f"Raw content: {content}")
        raise HTTPException(
            status_code=500,
            detail="Failed to parse campaign content"
        )
    except Exception as e:
        logging.error(f"Error generating campaign content: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate campaign content"
        ) 

@app.get("/api/companies/{company_id}/cronofy-auth", response_model=CronofyAuthResponse)
async def cronofy_auth(
    company_id: UUID,
    code: str = Query(..., description="Authorization code from Cronofy"),
    redirect_url: str = Query(..., description="Redirect URL used in the authorization request"),
    current_user: dict = Depends(get_current_user)
):
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")

    settings = get_settings()
    cronofy = pycronofy.Client(
        client_id=settings.cronofy_client_id,
        client_secret=settings.cronofy_client_secret
    )
    
    auth = cronofy.get_authorization_from_code(code, redirect_uri=redirect_url)
    
    # Get user info and profiles
    user_info = cronofy.userinfo()
    logger.info(f"Cronofy user info: {user_info}")
    
    # Get profile and calendar information from userinfo
    cronofy_data = user_info.get('cronofy.data', {})
    profiles = cronofy_data.get('profiles', [])
    
    if not profiles:
        raise HTTPException(status_code=400, detail="No calendar profiles found")
    
    first_profile = profiles[0]
    
    # Find primary calendar ID and name from userinfo
    default_calendar_id = None
    default_calendar_name = None
    for calendar in first_profile.get('profile_calendars', []):
        if calendar.get('calendar_primary'):
            default_calendar_id = calendar['calendar_id']
            default_calendar_name = calendar['calendar_name']
            break
    
    if not default_calendar_id:
        raise HTTPException(status_code=400, detail="No primary calendar found")
    
    # Update company with Cronofy profile information
    await update_company_cronofy_profile(
        company_id=company_id,
        provider=first_profile['provider_name'],
        linked_email=user_info['email'],
        default_calendar=default_calendar_id,
        default_calendar_name=default_calendar_name,
        access_token=auth['access_token'],
        refresh_token=auth['refresh_token']
    )
    
    return CronofyAuthResponse(message="Successfully connected to Cronofy") 

@app.delete("/api/companies/{company_id}/calendar", response_model=CronofyAuthResponse)
async def disconnect_calendar(
    company_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get company to get the access token
    company = await get_company_by_id(company_id)
    if not company or not company.get('cronofy_access_token'):
        raise HTTPException(status_code=400, detail="No Cronofy connection found")
    
    # Initialize Cronofy client and revoke authorization
    settings = get_settings()
    cronofy = pycronofy.Client(
        client_id=settings.cronofy_client_id,
        client_secret=settings.cronofy_client_secret,
        access_token=company['cronofy_access_token']
    )
    
    try:
        cronofy.revoke_authorization()
    except Exception as e:
        logger.error(f"Error revoking Cronofy authorization: {str(e)}")
        # Continue with clearing data even if revoke fails
    
    # Clear all Cronofy-related data
    await clear_company_cronofy_data(company_id)
    
    return CronofyAuthResponse(message="Successfully disconnected calendar") 

# Background task for processing leads
async def process_leads_upload(
    company_id: UUID,
    file_url: str,
    user_id: UUID,
    task_id: UUID
):
    try:
        # Initialize Supabase client with service role
        settings = get_settings()
        supabase: Client = create_client(
            settings.supabase_url,
            settings.SUPABASE_SERVICE_KEY  # Use service role key
        )
        
        # Update task status to processing
        await update_task_status(task_id, "processing")
        
        # Download file from Supabase
        try:
            storage = supabase.storage.from_("leads-uploads")
            response = storage.download(file_url)
            if not response:
                raise Exception("No data received from storage")
                
            csv_text = response.decode('utf-8')
            csv_data = csv.DictReader(io.StringIO(csv_text))
            
            # Validate CSV structure
            if not csv_data.fieldnames:
                raise Exception("CSV file has no headers")
                
        except Exception as download_error:
            logger.error(f"Error downloading file: {str(download_error)}")
            await update_task_status(task_id, "failed", f"Failed to download file: {str(download_error)}")
            return
        
        lead_count = 0
        skipped_count = 0
        unmapped_headers = set()
        
        # Get CSV headers
        headers = csv_data.fieldnames
        if not headers:
            await update_task_status(task_id, "failed", "CSV file has no headers")
            return
        
        # Initialize OpenAI client
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Create a prompt to map headers
        prompt = f"""Map the following CSV headers to our database fields. Return a JSON object where keys are the CSV headers and values are the corresponding database field names.

CSV Headers: {', '.join(headers)}

Database fields and their types:
- name (text, required) - Should be constructed from First Name and Last Name if available
- first_name (text, required) - should be first name if available. 
- last_name (text, required) - should be last name if available
- email (text, required)
- company (text) - Map from Company Name
- phone_number (text, required) - Should use Mobile if available, else Direct, else Office
- company_size (text)
- job_title (text)
- lead_source (text)
- education (text)
- personal_linkedin_url (text)
- country (text)
- city (text)
- state (text)
- mobile (text)
- direct_phone (text)
- office_phone (text)
- hq_location (text)
- website (text)
- headcount (integer)
- industries (text array)
- department (text)
- sic_code (text)
- isic_code (text)
- naics_code (text)
- company_address (text)
- company_city (text)
- company_zip (text)
- company_state (text)
- company_country (text)
- company_hq_address (text)
- company_hq_city (text)
- company_hq_zip (text)
- company_hq_state (text)
- company_hq_country (text)
- company_linkedin_url (text)
- company_type (text)
- company_description (text)
- technologies (text array)
- financials (jsonb)
- company_founded_year (integer)
- seniority (text)
- first_name (text)
- last_name (text)

Special handling instructions:
1. Map "First Name" and "Last Name" to first_name and last_name respectively
2. Map "Company Name" to company
3. Map "Mobile", "Direct", and "Office" to mobile, direct_phone, and office_phone respectively
4. Map "Industries" to industries (will be converted to array)
5. Map "Technologies" to technologies (will be converted to array)
6. Map "Company Founded Year" to company_founded_year (will be converted to integer)
7. Map "Headcount" to headcount (will be converted to integer)

Return ONLY a valid JSON object mapping CSV headers to database field names. If a header doesn't map to any field, map it to null.
Example format: {{"First Name": "first_name", "Last Name": "last_name", "Unmatched Header": null}}"""

        # Get header mapping from OpenAI
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a helpful assistant that maps CSV headers to database field names. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ]
        )
        
        try:
            header_mapping = json.loads(response.choices[0].message.content.strip())
        except json.JSONDecodeError:
            await update_task_status(task_id, "failed", "Failed to parse header mapping")
            return
        
        # Process each row
        for row in csv_data:
            lead_data = {}
            
            # Map CSV data to database fields using the header mapping
            for csv_header, db_field in header_mapping.items():
                if db_field and csv_header in row:
                    value = row[csv_header].strip() if row[csv_header] else None
                    if value:
                        # Handle special cases
                        if db_field == "industries":
                            lead_data[db_field] = [ind.strip() for ind in value.split(",")]
                        elif db_field == "technologies":
                            lead_data[db_field] = [tech.strip() for tech in value.split(",")]
                        elif db_field == "headcount":
                            try:
                                lead_data[db_field] = int(value.replace(",", ""))
                            except ValueError:
                                lead_data[db_field] = None
                        elif db_field == "company_founded_year":
                            try:
                                lead_data[db_field] = int(value)
                            except ValueError:
                                lead_data[db_field] = None
                        else:
                            lead_data[db_field] = value
            
            # Handle name fields
            first_name = lead_data.get('first_name', '').strip()
            last_name = lead_data.get('last_name', '').strip()
            
            # If name is already set but first_name/last_name are not, try to split it
            if lead_data.get('name') and not (first_name or last_name):
                name_parts = lead_data['name'].split(' ', 1)
                if len(name_parts) >= 2:
                    first_name = name_parts[0].strip()
                    last_name = name_parts[1].strip()
                else:
                    first_name = name_parts[0].strip()
                    last_name = ""
            
                lead_data['first_name'] = first_name
                lead_data['last_name'] = last_name
            # If first_name/last_name are set but name is not, combine them
            elif (first_name or last_name) and not lead_data.get('name'):
                lead_data['name'] = f"{first_name} {last_name}".strip()
                lead_data['first_name'] = first_name
                lead_data['last_name'] = last_name
            
            # Skip record if name is empty
            if not lead_data.get('name'):
                logger.info(f"Skipping record due to missing name: {row}")
                skipped_count += 1
                continue
            
            # Ensure first_name and last_name are always set
            if not lead_data.get('first_name') and not lead_data.get('last_name'):
                name_parts = lead_data['name'].split(' ', 1)
                if len(name_parts) >= 2:
                    lead_data['first_name'] = name_parts[0].strip()
                    lead_data['last_name'] = name_parts[1].strip()
                else:
                    lead_data['first_name'] = name_parts[0].strip()
                    lead_data['last_name'] = ""
            
            # Handle phone number priority (Mobile > Direct > Office)
            phone_number = lead_data.get('mobile', '').strip()
            if not phone_number:
                phone_number = lead_data.get('direct_phone', '').strip()
            if not phone_number:
                phone_number = lead_data.get('office_phone', '').strip()
            lead_data['phone_number'] = phone_number
            
            # Handle hiring positions
            hiring_positions = []
            for i in range(1, 6):  # Process all 5 hiring positions
                title = row.get(f"Hiring Title {i}")
                if title:  # Only add if there's a title
                    hiring_positions.append({
                        "title": title,
                        "url": row.get(f"Hiring URL {i}"),
                        "location": row.get(f"Hiring Location {i}"),
                        "date": row.get(f"Hiring Date {i}")
                    })
            if hiring_positions:
                lead_data["hiring_positions"] = hiring_positions
            
            # Handle location move
            if any(row.get(key) for key in ["Location Move - From Country", "Location Move - To Country"]):
                lead_data["location_move"] = {
                    "from": {
                        "country": row.get("Location Move - From Country"),
                        "state": row.get("Location Move - From State")
                    },
                    "to": {
                        "country": row.get("Location Move - To Country"),
                        "state": row.get("Location Move - To State")
                    },
                    "date": row.get("Location Move Date")
                }
            
            # Handle job change
            if any(row.get(key) for key in ["Job Change - Previous Company", "Job Change - New Company"]):
                lead_data["job_change"] = {
                    "previous": {
                        "company": row.get("Job Change - Previous Company"),
                        "title": row.get("Job Change - Previous Title")
                    },
                    "new": {
                        "company": row.get("Job Change - New Company"),
                        "title": row.get("Job Change - New Title")
                    },
                    "date": row.get("Job Change Date")
                }
            
            # Create the lead
            try:
                print(lead_data)
                await create_lead(company_id, lead_data)
                lead_count += 1
            except Exception as e:
                logger.error(f"Error creating lead: {str(e)}")
                logger.error(f"Lead data: {lead_data}")
                skipped_count += 1
                continue
        
        # Update task status with results
        await update_task_status(
            task_id,
            "completed",
            json.dumps({
                "leads_saved": lead_count,
                "leads_skipped": skipped_count,
                "unmapped_headers": list(unmapped_headers)
            })
        )
        
    except Exception as e:
        logger.error(f"Error processing leads upload: {str(e)}")
        await update_task_status(task_id, "failed", str(e))

# Task status endpoint
@app.get("/api/tasks/{task_id}")
async def get_task_status(
    task_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Get the status of a background task"""
    task = await get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Verify user has access to the company
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(task["company_id"]) for company in companies):
        raise HTTPException(status_code=403, detail="Not authorized to access this task")
        
    return task 

@app.post("/api/companies/{company_id}/account-credentials", response_model=CompanyInDB)
async def update_account_credentials(
    company_id: UUID,
    credentials: AccountCredentialsUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update account credentials for a company
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Currently only supporting 'gmail' type
    if credentials.type != 'gmail':
        raise HTTPException(status_code=400, detail="Currently only 'gmail' account type is supported")
    
    # Test both SMTP and IMAP connections before saving
    try:
        await SMTPClient.test_connections(
            account_email=credentials.account_email,
            account_password=credentials.account_password,
            provider=credentials.type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to email servers: {str(e)}")
    
    # If we get here, both connections were successful - update the credentials
    updated_company = await update_company_account_credentials(
        company_id,
        credentials.account_email,
        credentials.account_password,
        credentials.type  # Save the account type
    )
    
    if not updated_company:
        raise HTTPException(status_code=404, detail="Failed to update account credentials")
    
    return updated_company 

@app.post("/api/auth/forgot-password", response_model=ResetPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """Request a password reset link"""
    return await request_password_reset(request.email)

@app.post("/api/auth/reset-password", response_model=ResetPasswordResponse)
async def reset_password_endpoint(request: ResetPasswordRequest):
    """Reset password using the reset token"""
    return await reset_password(reset_token=request.token, new_password=request.new_password) 