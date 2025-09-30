from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Query, Form, Body, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import RedirectResponse, Response
from datetime import datetime, timezone, timedelta
import csv
import io
import logging
import bugsnag
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from openai import AsyncOpenAI
import json
import pycronofy
import uuid
from pydantic import BaseModel
from supabase import create_client, Client
from src.utils.smtp_client import SMTPClient
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.services.campaigns import run_test_email_campaign, run_test_call_campaign
from src.routes.web_agent import router as web_agent_router
from src.routes.partner_applications import router as partner_applications_router
from src.routes.do_not_email import router as do_not_email_router, check_router as do_not_email_check_router
from src.routes.email_queues import router as email_queues_router
from src.routes.campaign_retry import router as campaign_retry_router
from src.routes.linkedin import router as linkedin_router
from src.routes.unipile_webhooks import router as unipile_webhooks_router
from src.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, settings, request_password_reset, reset_password,
    update_user
)
from src.database import (
    create_user,
    get_user_by_email,
    get_campaign_runs,
    get_email_conversation_history,
    update_company_voice_agent_settings,
    soft_delete_product,
    update_product_details,
    get_user_company_roles,
    get_user_company_profile_by_id,
    get_user_company_profile,
    get_company_email_logs,
    get_company_users,
    delete_user_company_profile,
    get_company_users,
    get_company_users,
    get_leads_with_email,
    get_leads_with_phone,
    create_campaign_run,
    get_campaign_by_id,
    get_active_campaign_runs_count,
    get_user_company_profile,
    create_user_company_profile,
    soft_delete_company,
    get_product_icps,
    update_product_icps,
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
    create_campaign,
    get_campaigns_by_company,
    update_task_status,
    create_upload_task,
    get_task_status,
    delete_lead,
    update_email_log_has_opened,
    update_lead_enrichment, update_campaign_run_status,get_leads_with_email,get_leads_with_phone,create_campaign_run, get_campaign_by_id,
    get_user_company_profile,
    update_company_account_credentials,
    add_email_to_queue,
    get_email_throttle_settings,
    update_email_throttle_settings,
    update_queue_item_status,
    create_unverified_user,
    create_invite_token,
    get_valid_invite_token,
    mark_invite_token_used,
    clear_company_cronofy_data,
    update_company_cronofy_profile,
    get_email_queues_by_campaign_run,
    get_campaign_run,
    add_call_to_queue,
    update_call_queue_item_status,
    get_email_log_by_id,
    check_existing_call_queue_record,
    update_email_reminder_eligibility,
    get_call_log_by_bland_id,
    get_campaign_lead_count,
    check_user_access_status,
    check_user_campaign_access,
    has_pending_upload_tasks,
    create_skipped_row_record,
    update_campaign_run_celery_task_id,
    delete_skipped_rows_by_task
)
from src.ai_services.anthropic_service import AnthropicService
from src.services.email_service import email_service
from src.models import (
    UserCreate, UserInDB, Token, UserUpdate, 
    CompanyCreate, CompanyInDB, ProductCreate, ProductInDB,
    PaginatedLeadResponse, LeadResponse,
    CallInDB, BlandWebhookPayload, EmailCampaignCreate,
    EmailCampaignInDB, AccountCredentialsUpdate, EmailVerificationRequest, EmailVerificationResponse,
    ResendVerificationRequest, ForgotPasswordRequest, ResetPasswordRequest, ResetPasswordResponse,
    CampaignGenerationRequest, CampaignGenerationResponse, CronofyAuthResponse,
    CompanyInviteRequest, CompanyInviteResponse, InvitePasswordRequest, InviteTokenResponse,
    EmailLogDetailResponse, LeadSearchResponse, CompanyUserResponse,
    VoiceAgentSettings, CreateLeadRequest, CallScriptResponse, EmailScriptResponse, TestRunCampaignRequest,
    EmailThrottleSettings,TaskResponse, PaginatedEmailQueueResponse, PaginatedCallResponse, PaginatedEmailLogResponse, PaginatedCampaignRunResponse  # Add these imports
)
from src.config import get_settings
from src.bland_client import BlandClient
import secrets
from src.services.perplexity_service import perplexity_service
import os
from src.utils.file_parser import FileParser
from src.utils.calendar_utils import book_appointment as calendar_book_appointment
from bugsnag.handlers import BugsnagHandler
from src.perplexity_enrichment import PerplexityEnricher
from src.services.email_generation import generate_company_insights, generate_email_content, get_or_generate_insights_for_lead
from src.services.call_generation import generate_call_script
from src.routes import email_queues, call_queues
from src.services.bland_calls import update_call_queue_on_error
from src.routes.call_queue_status import router as call_queue_status_router
from src.routes.calendar import calendar_router
from src.services.email_open_detector import EmailOpenDetector
from src.routes.accounts import accounts_router
from src.routes.subscriptions import router as subscriptions_router
from src.routes.checkout_sessions import router as checkout_sessions_router
from src.routes.stripe_webhooks import router as stripe_webhooks_router
from src.services.stripe_service import StripeService
import chardet
from email_validator import validate_email, EmailNotValidError
from src.utils.string_utils import validate_phone_number
from src.routes.upload_tasks import router as upload_tasks_router
from src.routes.skipped_rows import router as skipped_rows_router
from src.routes.file_downloads import router as file_downloads_router
from src.database import TRIAL_PLAN_LEAD_LIMIT
from src.routes.companies import companies_router

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Bugsnag
bugsnag.configure(
    api_key=settings.bugsnag_api_key,
    #project_root="/",
    release_stage=settings.environment,
    #asynchronous=True,
    #auto_capture_sessions=True
)

handler = BugsnagHandler()
# send only ERROR-level logs and above
handler.setLevel(logging.ERROR)
logger.addHandler(handler)

class BookAppointmentRequest(BaseModel):
    company_uuid: UUID
    call_log_id: UUID
    email: str
    start_time: datetime
    email_subject: str

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
@app.post("/api/auth/signup", response_model=dict, tags=["Authentication"])
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
        # Log error with full exception details 
        logger.error(f"Failed to send verification email to {user.email}: {repr(e)} - {str(e)}")
        bugsnag.notify(
            e,
            context="signup_verification_email",
            metadata={
                "user_email": user.email,
                "user_id": created_user["id"],
                "error": str(e),
                "error_type": type(e).__name__
            }
        )
        # Don't fail signup, but let user know they need to request a new verification email
        return {
            "message": "Account created successfully, but verification email could not be sent. Please use the resend verification endpoint."
        }
    
    return {"message": "Account created successfully. Please check your email to verify your account."}

@app.post("/api/auth/verify", response_model=EmailVerificationResponse, tags=["Authentication"])
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

@app.post("/api/auth/resend-verification", response_model=dict, tags=["Authentication"])
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

@app.post("/api/auth/login", response_model=Token, tags=["Authentication"])
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

@app.get("/api/users/me", response_model=UserInDB, tags=["Users"])
async def get_current_user_details(
    show_subscription_details: bool = Query(False, description="Whether to include subscription details in the response"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get details of the currently authenticated user
    """
    user = await get_user_by_email(current_user["email"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user["plan_type"] == "trial":
        user['lead_tier'] = TRIAL_PLAN_LEAD_LIMIT

    # Get user's company roles
    company_roles = await get_user_company_roles(UUID(user["id"]))
    user["company_roles"] = company_roles
    
    if user["plan_type"] == "trial":
        # Check whether the user is on a trial plan and whether it has expired or not
        has_access, error_message = await check_user_access_status(UUID(user["id"]))
        
        # if user is on a trial plan and the trial has expired, set the message for the user
        if not has_access:
            user["upgrade_message"] = error_message
    
    # Get subscription details if user has a Stripe customer ID and show_subscription_details is True
    if show_subscription_details and user.get("stripe_customer_id"):
        try:
            stripe_service = StripeService()
            subscription_details = await stripe_service.get_subscription_details(user["id"])
            user["subscription_details"] = subscription_details
        except Exception as e:
            logger.error(f"Error fetching subscription details: {str(e)}")
            user["subscription_details"] = {
                "has_subscription": False,
                "message": str(e)
            }

    return user

# Company Management endpoints
@app.post(
    "/api/companies", 
    response_model=CompanyInDB,
    tags=["Companies"]
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

    # Create the company
    created_company = await db_create_company(
        current_user["id"],
        company.name,
        address,
        industry,
        company.website,
        overview,
        background,
        products_services
    )

    # Create user-company profile with admin role
    try:
        await create_user_company_profile(
            user_id=UUID(current_user["id"]),
            company_id=UUID(created_company["id"]),
            role="admin"
        )
    except Exception as e:
        logger.error(f"Error creating user-company profile: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Company created but failed to set up admin access"
        )

    return created_company

@app.get("/api/companies/{company_id}/products/{product_id}", response_model=ProductInDB, tags=["Products"])
async def get_product(
    company_id: UUID,
    product_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific product by ID.
    
    Args:
        company_id: UUID of the company
        product_id: UUID of the product to retrieve
        current_user: Current authenticated user
        
    Returns:
        Product information
        
    Raises:
        404: Product not found or company not found
        403: User doesn't have access to this company
    """
    # Verify user has access to the company
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get the product
    product = await get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Verify product belongs to the specified company
    if str(product["company_id"]) != str(company_id):
        raise HTTPException(status_code=404, detail="Product not found in this company")
    
    return product

@app.get("/api/companies/{company_id}/products", response_model=List[ProductInDB], tags=["Products"])
async def get_products(
    company_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    return await get_products_by_company(company_id)

@app.post("/api/companies/{company_id}/products", response_model=ProductInDB, tags=["Products"])
async def create_product(
    company_id: UUID,
    product_name: str = Form(...),
    product_url: Optional[str] = Form(None),
    file: UploadFile = File(...),  # Made file mandatory by removing Optional and None default
    current_user: dict = Depends(get_current_user)
):
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get company details for enrichment
    company = await get_company_by_id(company_id)
    company_name = company.get("name", "")
    
    file_name = None
    original_filename = None
    description = None  # Will be set from file content
    enriched_information = None
    
    # Process file (now mandatory)
    # Validate file extension
    allowed_extensions = {'.docx', '.pdf', '.txt'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        bugsnag.notify(
            Exception("Invalid file type uploaded"),
            context="create_product_validation",
            metadata={
                "file_name": file.filename,
                "file_extension": file_ext,
                "allowed_extensions": list(allowed_extensions),
                "company_id": str(company_id),
                "user_id": current_user["id"]
            }
        )
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types are: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Generate unique filename
        file_name = f"{uuid.uuid4()}{file_ext}"
        original_filename = file.filename
        
        # Read and parse file content
        file_content = await file.read()
        try:
            # Parse file content and use it as description
            description = FileParser.parse_file(file_content, file_ext)
            if not description:
                raise HTTPException(status_code=400, detail="Could not extract content from file")
        except ValueError as e:
            logger.error(f"Error parsing file: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")
        
        # Initialize Supabase client with service role
        settings = get_settings()
        supabase: Client = create_client(
            settings.supabase_url,
            settings.SUPABASE_SERVICE_KEY
        )
        
        # Upload file to Supabase storage
        storage = supabase.storage.from_("product-files")
        storage.upload(
            path=file_name,
            file=file_content,
            file_options={"content-type": file.content_type}
        )
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process file")
    
    # Enrich product data using Perplexity if URL is provided
    if product_url:
        try:
            settings = get_settings()
            perplexity_api_key = settings.perplexity_api_key
            
            if perplexity_api_key:
                perplexity_enricher = PerplexityEnricher(perplexity_api_key)
                enriched_information = await perplexity_enricher.enrich_product_data(company_name, product_url)
                logger.info(f"Enriched product information: {json.dumps(enriched_information, indent=2)}")
            else:
                logger.warning("Perplexity API key not found, skipping product enrichment")
        except Exception as e:
            logger.error(f"Error enriching product data: {str(e)}")
            # Continue without enrichment if it fails
    
    # Create product with all available information
    return await db_create_product(
        company_id=company_id,
        product_name=product_name,
        file_name=file_name,
        original_filename=original_filename,
        description=description,
        product_url=product_url,
        enriched_information=enriched_information
    )

@app.put("/api/companies/{company_id}/products/{product_id}", response_model=ProductInDB, tags=["Products"])
async def update_product(
    company_id: UUID,
    product_id: UUID,
    product: ProductCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a product's details including name, description, and URL.
    
    Args:
        company_id: UUID of the company
        product_id: UUID of the product to update
        product: Updated product data
        current_user: Current authenticated user
        
    Returns:
        Updated product information
        
    Raises:
        404: Product not found or company not found
        403: User doesn't have access to this company or product doesn't belong to company
    """
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
    
    return await update_product_details(
        product_id=product_id, 
        product_name=product.product_name,
        description=product.description,
        product_url=product.product_url
    )

@app.delete("/api/companies/{company_id}/products/{product_id}", response_model=dict, tags=["Products"])
async def delete_product(
    company_id: UUID,
    product_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get the product to ensure it exists and belongs to the company
    product = await get_product_by_id(product_id)
    if str(product['company_id']) != str(company_id):
        raise HTTPException(
            status_code=403, 
            detail="This product does not belong to the specified company"
        )
    
    # Soft delete the product
    await soft_delete_product(product_id)
    
    return {"message": "Product deleted successfully"}

@app.get("/api/companies/{company_id}/products/{product_id}/icp", response_model=List[Dict[str, Any]], tags=["Products"])
async def get_product_icp(
    company_id: UUID,
    product_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the ideal customer profiles for a product.
    
    Args:
        company_id: UUID of the company
        product_id: UUID of the product
        
    Returns:
        List of ideal customer profiles
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get the product to ensure it exists and belongs to the company
    product = await get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    if str(product['company_id']) != str(company_id):
        raise HTTPException(
            status_code=403, 
            detail="This product does not belong to the specified company"
        )
    
    try:
        # Get the ICPs for the product
        icps = await get_product_icps(product_id)
        
        # If no ICPs exist, return an empty list
        if not icps:
            return []
            
        # Ensure each ICP has an ID if missing (backward compatibility)
        import uuid
        for icp in icps:
            if "id" not in icp:
                icp["id"] = str(uuid.uuid4())
            
            # Ensure there's a name in the ICP (backward compatibility)
            if "idealCustomerProfile" in icp and "name" not in icp["idealCustomerProfile"]:
                # Generate a name based on company attributes if possible
                try:
                    industries = icp["idealCustomerProfile"]["companyAttributes"]["industries"]
                    company_size = icp["idealCustomerProfile"]["companyAttributes"]["companySize"]["employees"]
                    
                    # Create a name like "Enterprise Software Companies" or "Small Healthcare Organizations"
                    size_desc = "Enterprise" if company_size["max"] > 500 else "Mid-Market" if company_size["max"] > 100 else "Small"
                    industry = industries[0] if industries else "Companies"
                    
                    icp["idealCustomerProfile"]["name"] = f"{size_desc} {industry}"
                except:
                    # Fallback name if we can't extract meaningful information
                    icp["idealCustomerProfile"]["name"] = f"ICP #{icps.index(icp) + 1}"
        
        return icps
    except Exception as e:
        logger.error(f"Error retrieving product ICPs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve ideal customer profiles: {str(e)}"
        )

@app.post("/api/companies/{company_id}/products/{product_id}/icp", response_model=List[Dict[str, Any]], tags=["Products"])
async def generate_and_set_icp(
    company_id: UUID,
    product_id: UUID,
    icp_input: Optional[str] = Query(None, description="Optional user instructions to focus ICP generation"),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate and set ideal customer profiles for a product using Anthropic's Claude API.
    Generates at least 3 atomic ICPs, each focusing on a single specific customer type.
    
    Args:
        company_id: UUID of the company
        product_id: UUID of the product
        icp_input: Optional user instructions to focus ICP generation on specific criteria
        
    Returns:
        List of generated ideal customer profiles
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get the product to ensure it exists and belongs to the company
    product = await get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    if str(product['company_id']) != str(company_id):
        raise HTTPException(
            status_code=403, 
            detail="This product does not belong to the specified company"
        )
    
    # Get the company information
    company = await get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    try:
        # Print debug info
        logger.info(f"Product data: {product}")
        logger.info(f"Company data: {company}")
        if icp_input:
            logger.info(f"Custom ICP focus: {icp_input}")
        
        # Initialize Anthropic service
        anthropic_service = AnthropicService()
        
        # Generate ICPs using Claude - use product_name instead of name
        generated_icps = await anthropic_service.generate_ideal_customer_profile(
            product_name=product.get('product_name', 'Unnamed Product'),
            product_description=product.get('description', '') or "",
            company_info=company,
            enriched_information=product.get('enriched_information', {}),
            icp_input=icp_input  # Pass the optional user instructions
        )
        
        # Store the generated ICPs
        if generated_icps and len(generated_icps) > 0:
            try:
                # Get any existing ICPs
                existing_icps = await get_product_icps(product_id)
                
                # Make sure existing_icps is a list
                if existing_icps is None:
                    existing_icps = []
                
                # Check for duplicate names and modify if needed
                for icp in generated_icps:
                    if "idealCustomerProfile" in icp and "name" in icp["idealCustomerProfile"]:
                        icp_name = icp["idealCustomerProfile"]["name"]
                        name_count = 1
                        original_name = icp_name
                        
                        # Check if name already exists in any existing ICP
                        while any(existing_icp.get("idealCustomerProfile", {}).get("name") == icp_name 
                                for existing_icp in existing_icps):
                            icp_name = f"{original_name} #{name_count}"
                            name_count += 1
                        
                        # Update name if it was changed
                        if icp_name != original_name:
                            icp["idealCustomerProfile"]["name"] = icp_name
                
                # Add the new ICPs to the list
                updated_icps = existing_icps + generated_icps
                
                # Log the number of generated ICPs
                logger.info(f"Generated {len(generated_icps)} new ICPs for product {product_id}")
                
                # Update the product with the new ICPs
                await update_product_icps(product_id, updated_icps)
                
                return updated_icps
            except Exception as e:
                logger.error(f"Error updating product ICPs: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to save ideal customer profiles: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate ideal customer profiles"
            )
    except Exception as e:
        logger.error(f"Error generating ICPs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate ideal customer profiles: {str(e)}"
        )

@app.get("/api/companies", response_model=List[CompanyInDB], tags=["Companies"])
async def get_companies(
    show_stats: bool = Query(False, description="Include products in the response"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all companies that the user has access to, through user_company_profiles.
    Optionally include products in the response if show_stats is True.
    """
    try:
        user_id = current_user.get("id")
        if not user_id:
            logger.error(f"No user ID found in current_user: {current_user}")
            return []
        
        # Log the request details
        logger.info(f"=== GET /api/companies request ===")
        logger.info(f"User ID: {user_id}")
        logger.info(f"User Email: {current_user.get('email', 'N/A')}")
        logger.info(f"Show Stats: {show_stats}")
        
        companies = await get_companies_by_user_id(user_id, show_stats)
        
        logger.info(f"Returned {len(companies)} companies for user {user_id}")
        
        if companies is None:
            logger.warning(f"get_companies_by_user_id returned None for user {user_id}")
            return []
        
        return companies
    except Exception as e:
        logger.error(f"Error in get_companies for user {current_user.get('id')}: {str(e)}", exc_info=True)
        # Return empty list instead of None to satisfy response model
        return [] 

@app.get("/api/debug/companies", tags=["Debug"])
async def debug_companies(
    current_user: dict = Depends(get_current_user)
):
    """Debug endpoint to check company data"""
    try:
        user_id = current_user.get("id")
        
        # Get company roles
        company_roles = await get_user_company_roles(UUID(user_id))
        
        # Get user company profiles
        from src.database import supabase
        profiles_response = supabase.table('user_company_profiles')\
            .select('*')\
            .eq('user_id', str(user_id))\
            .execute()
        
        # Get companies with join
        companies_response = supabase.table('user_company_profiles')\
            .select('role, user_id, companies!inner(*)')\
            .eq('user_id', str(user_id))\
            .execute()
        
        return {
            "user_id": user_id,
            "company_roles": company_roles,
            "user_company_profiles_count": len(profiles_response.data),
            "user_company_profiles": profiles_response.data,
            "companies_with_join_count": len(companies_response.data),
            "companies_with_join": companies_response.data
        }
    except Exception as e:
        logger.error(f"Error in debug_companies: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 

@app.get("/api/companies/{company_id}", response_model=CompanyInDB, tags=["Companies"])
async def get_company(
    company_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    companies = await get_companies_by_user_id(UUID(current_user["id"]))
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    company = await get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return company

@app.delete("/api/companies/{company_id}", response_model=dict, tags=["Companies"])
async def delete_company(
    company_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Soft delete a company by setting deleted = TRUE
    Only users with admin role can delete a company.
    
    Args:
        company_id: UUID of the company to delete
        current_user: Current authenticated user
        
    Returns:
        Dict with success message
        
    Raises:
        404: Company not found
        403: User doesn't have access to this company or is not an admin
    """
    # Verify user has access to the company
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check if user has admin role for this company
    user_profile = await get_user_company_profile(UUID(current_user["id"]), company_id)
    if not user_profile or user_profile["role"] != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Only company administrators can delete a company"
        )
    
    # Soft delete the company
    success = await soft_delete_company(company_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete company")
    
    return {"status": "success", "message": "Company deleted successfully"}

# Lead Management endpoints
@app.post("/api/companies/{company_id}/leads/upload", response_model=TaskResponse, tags=["Leads"])
async def upload_leads(
    company_id: UUID,
    current_user: dict = Depends(get_current_user),
    file: UploadFile = File(...)
):
    """
    Upload leads from CSV file. The processing will be done in the background.
    The file will be processed asynchronously using a Celery task.

    Args:
        company_id: UUID of the company
        current_user: Current authenticated user
        file: CSV file containing lead data
    Returns:
        Task ID for tracking the upload progress
    """
    try:
        # Get company details
        company = await get_company_by_id(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # Check if the company owner user is on an active subscription, or has a trial that is still valid
        has_access, error_message = await check_user_access_status(UUID(company["user_id"]))
        # if user is neither on an active subscription, nor has a trial that is still valid, return an error
        if not has_access:
            raise HTTPException(status_code=403, detail=error_message)
        # Validate company access
        companies = await get_companies_by_user_id(current_user["id"])
        if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
            raise HTTPException(status_code=403, detail="Not authorized to access this company")

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
        await create_upload_task(
            task_id=task_id,
            company_id=company_id,
            user_id=current_user["id"],
            file_url=file_name,
            file_name=file.filename,
            type='leads'
        )

        # Queue the Celery task
        from src.celery_app.tasks.process_leads import celery_process_leads
        result = celery_process_leads.delay(
            company_id=str(company_id),
            file_url=file_name,
            user_id=str(current_user["id"]),
            task_id=str(task_id)
        )

        # Update only the celery task ID
        await update_task_status(
            task_id=task_id,
            status=None,  # Don't update status
            result=None,
            celery_task_id=result.id
        )

        return TaskResponse(
            task_id=task_id,
            message="File upload started. Use the task ID to check the status."
        )
    except Exception as e:
        logger.error(f"Error in upload_leads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/companies/{company_id}/leads", response_model=PaginatedLeadResponse, tags=["Leads"])
async def get_leads(
    company_id: UUID,
    page_number: int = Query(default=1, ge=1, description="Page number to fetch"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    search_term: Optional[str] = Query(default=None, description="Search term to filter leads by name, email, company or job title"),
    current_user: dict = Depends(get_current_user)
):
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    return await get_leads_by_company(company_id, page_number=page_number, limit=limit, search_term=search_term)

@app.get("/api/companies/{company_id}/leads/{lead_id}", response_model=LeadResponse, tags=["Leads"])
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
    
    # Handle enriched_data field
    if lead.get("enriched_data"):
        if isinstance(lead["enriched_data"], str):
            try:
                lead["enriched_data"] = json.loads(lead["enriched_data"])
            except json.JSONDecodeError:
                lead["enriched_data"] = None
        elif not isinstance(lead["enriched_data"], dict):
            lead["enriched_data"] = None
    
    return {
        "status": "success",
        "data": lead
    }

@app.delete("/api/companies/{company_id}/leads/{lead_id}", response_model=dict, tags=["Leads"])
async def delete_lead_endpoint(
    company_id: UUID,
    lead_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a lead by ID.
    
    Args:
        company_id: UUID of the company
        lead_id: UUID of the lead to delete
        current_user: Current authenticated user
        
    Returns:
        Dict with success message
        
    Raises:
        404: Lead not found
        403: User doesn't have access to this lead
    """
    # Get lead data first to verify ownership
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
    
    # Delete the lead
    success = await delete_lead(lead_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete lead")
    
    return {"status": "success", "message": "Lead deleted successfully"}

@app.post("/api/companies/{company_id}/leads", response_model=LeadResponse, tags=["Leads"])
async def create_lead_endpoint(
    company_id: UUID,
    lead_data: CreateLeadRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a single lead for a company.

    Args:
        company_id: UUID of the company
        lead_data: Lead information
        current_user: Current authenticated user
        
    Returns:
        Created lead details
        
    Raises:
        404: Company not found
        403: User doesn't have access to this company
    """
    try:
        # Validate company access
        companies = await get_companies_by_user_id(current_user["id"])
        if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Get company details
        company = await get_company_by_id(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # Check if the company owner user is on an active subscription, or has a trial that is still valid
        has_access, error_message = await check_user_access_status(UUID(company["user_id"]))

        # if user is neither on an active subscription, nor has a trial that is still valid, return an error
        if not has_access:
            raise HTTPException(status_code=403, detail=error_message)
        # Convert lead data to dict
        lead_dict = lead_data.dict(exclude_unset=True)

        # Handle name fields
        if not lead_dict.get('name') and (lead_dict.get('first_name') or lead_dict.get('last_name')):
            first_name = lead_dict.get('first_name', '')
            last_name = lead_dict.get('last_name', '')
            lead_dict['name'] = f"{first_name} {last_name}".strip()
        elif lead_dict.get('name') and not (lead_dict.get('first_name') or lead_dict.get('last_name')):
            # Split full name into first and last name
            name_parts = lead_dict['name'].split(' ', 1)
            if len(name_parts) >= 2:
                lead_dict['first_name'] = name_parts[0]
                lead_dict['last_name'] = name_parts[1]
            else:
                lead_dict['first_name'] = name_parts[0]
                lead_dict['last_name'] = ""
        
        # Validate email format
        email = lead_dict.get('email', '').strip()
        try:
            # Validate and normalize the email
            email_info = validate_email(email, check_deliverability=False)
            lead_dict['email'] = email_info.normalized
        except EmailNotValidError as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid email format: {str(e)}"
            )

        # Handle phone number priority and validation (optional)
        phone_number = None
        phone_fields = ['phone_number', 'mobile', 'direct_phone', 'office_phone']
        
        # Try each phone field in priority order
        for field in phone_fields:
            if lead_dict.get(field):
                is_valid, formatted_number = validate_phone_number(lead_dict[field])
                if is_valid:
                    phone_number = formatted_number
                    break
        
        # If a phone number was provided but invalid, warn but don't fail
        if any(lead_dict.get(field) for field in phone_fields) and not phone_number:
            logger.warning(f"Invalid phone number provided for lead {lead_dict.get('name', 'Unknown')}")
        
        # Update the lead data with the validated phone number (or None)
        lead_dict['phone_number'] = phone_number
    
        # Create/Update the lead in the database
        created_lead = await create_lead(company_id, lead_dict)
        
        # Get the created lead with all details
        lead = await get_lead_by_id(created_lead['id'])
        
        # Enrich the lead with company insights and update
        await get_or_generate_insights_for_lead(lead, force_creation=True)
        # Continue with the created lead even if enrichment fails
        
        # Get the created lead with all details so we can get the updated enriched_data
        lead = await get_lead_by_id(created_lead['id'])

        # Process fields for response
        if lead.get("industries") and isinstance(lead["industries"], str):
            lead["industries"] = [ind.strip() for ind in lead["industries"].split(",")]
        
        if lead.get("technologies") and isinstance(lead["technologies"], str):
            lead["technologies"] = [tech.strip() for tech in lead["technologies"].split(",")]
        
        if lead.get("financials") and isinstance(lead["financials"], str):
            try:
                lead["financials"] = json.loads(lead["financials"])
            except json.JSONDecodeError:
                lead["financials"] = {"value": lead["financials"]}
                
        # Process JSON fields
        for field in ["hiring_positions", "location_move", "job_change", "enriched_data"]:
            if lead.get(field) and isinstance(lead[field], str):
                try:
                    lead[field] = json.loads(lead[field])
                except json.JSONDecodeError:
                    lead[field] = None
        
        return {
            "status": "success",
            "data": lead
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating lead: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create lead: {str(e)}")

# Calling functionality endpoints
@app.post("/api/companies/{company_id}/calls/start", response_model=CallInDB, tags=["Calls"])
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
    
    # Check if lead has a phone number
    if not lead.get('phone_number'):
        raise HTTPException(status_code=400, detail="Cannot start call: Lead does not have a phone number")
        
    product = await get_product_by_id(product_id)
    if not product or str(product["company_id"]) != str(company_id):
        raise HTTPException(status_code=404, detail="Product not found or does not belong to this company")
    
    # Get company details
    company = await get_company_by_id(company_id)
    
    # Get or create a default campaign for direct calls
    try:
        # Check if there's already a default campaign for direct calls
        campaigns = await get_campaigns_by_company(company_id)
        default_campaign = None
        
        # Look for an existing "Direct Calls" campaign
        for campaign in campaigns:
            if campaign.get("name") == "Direct Calls":
                default_campaign = campaign
                break
                
        # If no default campaign exists, create one
        if not default_campaign:
            logger.info(f"Creating default 'Direct Calls' campaign for company {company_id}")
            default_campaign = await create_campaign(
                company_id=company_id,
                name="Direct Calls",
                description="Campaign for direct calls initiated from the UI",
                product_id=product_id,
                type="call"
            )
            
        campaign_id = default_campaign["id"]
        logger.info(f"Using campaign ID {campaign_id} for direct call")
    except Exception as campaign_error:
        logger.error(f"Error creating or finding default campaign: {str(campaign_error)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error preparing campaign for call: {str(campaign_error)}"
        )
        
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
        webhook_base_url=settings.webhook_base_url,
        bland_tool_id=settings.bland_tool_id,
        bland_secret_key=settings.bland_secret_key
    )
    
    try:
        # Create call record in database with company_id and script
        try:
            current_time = datetime.now(timezone.utc)
            call = await create_call(lead_id, product_id, campaign_id, script=script, last_called_at=current_time)
            logger.info(f"Created call record with ID: {call['id']} and last_called_at: {current_time}")
        except Exception as db_error:
            logger.error(f"Error creating call record in database: {str(db_error)}")
            logger.exception("Database error traceback:")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create call record in database: {str(db_error)}"
            )
        
        # Make the call to Bland API
        try:
            bland_response = await bland_client.start_call(
                phone_number=lead['phone_number'],
                script=script,
                request_data={
                    "company_uuid": str(company_id), 
                    "call_log_id": str(call['id']),
                    "email": lead['email'],
                    "email_subject": f"'{product['product_name']}' Discovery Call!"
                },
                company=company
            )
            
            # Update call with Bland call ID if the call was successfully initiated
            if bland_response and bland_response.get('call_id'):
                try:
                    await update_call_details(call['id'], bland_call_id=bland_response['call_id'], last_called_at=current_time)
                    logger.info(f"Updated call record with Bland call ID: {bland_response['call_id']} and last_called_at: {current_time}")
                except Exception as update_error:
                    # If database update fails, just log the error
                    logger.error(f"Failed to update call record with Bland call ID: {str(update_error)}")
                    # But still return the call record
            
            logger.info(f"Call successfully initiated with Bland API: {bland_response.get('call_id', 'Unknown ID')}")
            return call
            
        except Exception as call_error:
            logger.error(f"Error making call to Bland API but call record was created: {str(call_error)}")
            logger.exception("API error traceback:")
            # Return the call record anyway, since we've already created it
            return call
        
    except Exception as e:
        logger.error(f"Unexpected error in start_call endpoint: {str(e)}")
        logger.exception("Full exception traceback:")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error initiating call: {str(e)}"
        )

@app.get("/api/calls/{call_id}", response_model=CallInDB, tags=["Calls"])
async def get_call_details(
    call_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    call = await get_call_summary(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call 

@app.post("/api/calls/webhook", tags=["Calls"])
async def handle_bland_webhook(payload: BlandWebhookPayload):
    try:
        # Extract required fields from the payload
        bland_call_id = payload.call_id
        duration = payload.corrected_duration
        analysis = payload.analysis
        sentiment = analysis.get('sentiment') if analysis is not None else None
        reminder_eligible = analysis.get('reminder_eligible') if analysis is not None else False
        summary = payload.summary
        transcripts = payload.transcripts
        recording_url = payload.recording_url
        error_message = payload.error_message
        
        # Log the incoming webhook data for debugging
        logger.info(f"Processing webhook for call {bland_call_id}")
        logger.debug(f"Webhook payload: {payload}")
        
        # Update the call record in the database
        updated_call = await update_call_webhook_data(
            bland_call_id=bland_call_id,
            duration=duration,
            sentiment=sentiment,
            summary=summary,
            transcripts=transcripts,
            recording_url=recording_url,
            reminder_eligible=reminder_eligible,
            error_message=error_message
        )

        # If there is an error message, update the call queue on error, so it can be retried again if needed
        if error_message:
            await update_call_queue_on_error(bland_call_id=bland_call_id, error_message=error_message)

        if not updated_call:
            logger.error(f"Call record not found for bland_call_id: {bland_call_id}")
            raise HTTPException(
                status_code=404,
                detail="Call record not found"
            )

        call_log = await get_call_log_by_bland_id(bland_call_id)
        if not call_log:
            logger.error(f"Call log not found for bland_call_id: {bland_call_id}")
            raise HTTPException(
                status_code=404,
                detail="Call log not found"
            )

        campaign = await get_campaign_by_id(call_log['campaign_id'])
        if not campaign:
            logger.error(f"Campaign not found for campaign_id: {call_log['campaign_id']}")
            raise HTTPException(
                status_code=404,
                detail="Campaign not found"
            )

        lead = await get_lead_by_id(call_log['lead_id'])
        if not lead:
            logger.error(f"Lead not found for lead_id: {call_log['lead_id']}")
            raise HTTPException(
                status_code=404,
                detail="Lead not found"
            )

        # If the campaign is an "email_and_call" campaign, update the has_replied to True in the 'email_logs' table for that particular lead, so that the email reminder is not sent, 
        # since the person has already been contacted via call
        if campaign['type'] == 'email_and_call' and not reminder_eligible and not error_message:
            await update_email_reminder_eligibility(
                campaign_id=campaign['id'],
                campaign_run_id=call_log['campaign_run_id'],
                lead_id=lead['id'],
                has_replied=True
            )

        return {"status": "success", "message": "Call details updated"}
        
    except HTTPException as he:
        # Re-raise HTTP exceptions as they already have proper error details
        raise he
    except Exception as e:
        # Log the full error details
        logger.error(f"Failed to process webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}. Please check server logs for more details."
        )

@app.get("/api/companies/{company_id}/calls", response_model=PaginatedCallResponse, tags=["Calls"])
async def get_company_calls(
    company_id: UUID,
    campaign_id: Optional[UUID] = Query(None, description="Filter calls by campaign ID"),
    campaign_run_id: Optional[UUID] = Query(None, description="Filter calls by campaign run ID"),
    lead_id: Optional[UUID] = Query(None, description="Filter calls by lead ID"),
    sentiment: Optional[str] = Query(None, description="Filter calls by sentiment (positive or negative)"),
    has_meeting_booked: Optional[bool] = Query(None, description="Filter calls by meeting booked status"),
    from_date: Optional[datetime] = Query(None, description="Filter calls created from this date (inclusive)"),
    to_date: Optional[datetime] = Query(None, description="Filter calls created up to this date (inclusive)"),
    page_number: int = Query(default=1, ge=1, description="Page number to fetch"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get paginated list of calls for a company, optionally filtered by campaign ID, campaign run ID, lead ID, sentiment, meeting booked status, or date range
    
    Args:
        company_id: UUID of the company
        campaign_id: Optional UUID of the campaign to filter by
        campaign_run_id: Optional UUID of the campaign run to filter by
        lead_id: Optional UUID of the lead to filter by
        sentiment: Optional string to filter by sentiment (positive or negative)
        has_meeting_booked: Optional boolean to filter by meeting booked status
        from_date: Optional datetime to filter calls created from this date (inclusive)
        to_date: Optional datetime to filter calls created up to this date (inclusive)
        page_number: Page number to fetch (default: 1)
        limit: Number of items per page (default: 20)
        current_user: Current authenticated user
        
    Returns:
        Paginated list of calls
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # If campaign_id is provided, validate it belongs to the company
    if campaign_id:
        campaign = await get_campaign_by_id(campaign_id)
        if not campaign or str(campaign["company_id"]) != str(company_id):
            raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Validate sentiment value if provided
    if sentiment and sentiment.lower() not in ['positive', 'negative']:
        raise HTTPException(status_code=400, detail="Sentiment must be either 'positive' or 'negative'")
    
    # Validate date range if provided
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date must be before or equal to to_date")
    
    return await get_calls_by_company_id(
        company_id=company_id,
        campaign_id=campaign_id,
        campaign_run_id=campaign_run_id,
        lead_id=lead_id,
        sentiment=sentiment.lower() if sentiment else None,
        has_meeting_booked=has_meeting_booked,
        from_date=from_date,
        to_date=to_date,
        page_number=page_number,
        limit=limit
    )

@app.post("/api/companies/{company_id}/campaigns", response_model=EmailCampaignInDB, tags=["Campaigns & Emails"])
async def create_company_campaign(
    company_id: UUID,
    campaign: EmailCampaignCreate,
    current_user: dict = Depends(get_current_user)
):
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get company details
    company = await get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Check user's access to create this type of campaign
    has_access, error_message = await check_user_campaign_access(
        user_id=UUID(company["user_id"]),
        campaign_type=campaign.type.value
    )
    if not has_access:
        raise HTTPException(status_code=403, detail=error_message)
    
    # Validate that the product exists and belongs to the company
    product = await get_product_by_id(campaign.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if str(product["company_id"]) != str(company_id):
        raise HTTPException(status_code=403, detail="Product does not belong to this company")
    
    # Check for email credentials if it's a scheduled email campaign
    if (campaign.type.value == 'email' or campaign.type.value == 'email_and_call') and campaign.scheduled_at:
        if not company.get("account_email") or not company.get("account_password"):
            logger.error(f"Company {company_id} missing email account credentials")
            raise HTTPException(
                status_code=400,
                detail="Company email credentials not configured. Please set up email account credentials first."
            )
            
        if not company.get("account_type"):
            raise HTTPException(
                status_code=400,
                detail="Email provider type not configured. Please set up email provider type first."
            )
    
    return await create_campaign(
        company_id=company_id,
        name=campaign.name,
        description=campaign.description,
        product_id=campaign.product_id,
        type=campaign.type.value,  # Convert enum to string value
        template=campaign.template,
        number_of_reminders=campaign.number_of_reminders,
        days_between_reminders=campaign.days_between_reminders,
        phone_number_of_reminders=campaign.phone_number_of_reminders,
        phone_days_between_reminders=campaign.phone_days_between_reminders,
        auto_reply_enabled=campaign.auto_reply_enabled,
        trigger_call_on=campaign.trigger_call_on,
        scheduled_at=campaign.scheduled_at
    )

@app.get("/api/companies/{company_id}/campaigns", response_model=List[EmailCampaignInDB], tags=["Campaigns & Emails"])
async def get_company_campaigns(
    company_id: UUID,
    type: List[str] = Query(['all'], description="Filter campaigns by type: ['email', 'call', 'email_and_call'] or ['all']"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all campaigns for a company, optionally filtered by type
    """
    # Validate campaign types
    valid_types = {'email', 'call', 'email_and_call', 'all'}
    if not all(t in valid_types for t in type):
        raise HTTPException(status_code=400, detail="Invalid campaign type. Must be 'email', 'call', 'email_and_call', or 'all'")
    
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # If 'all' is in the types list, don't filter by type
    campaign_types = None if 'all' in type else type
    return await get_campaigns_by_company(company_id, campaign_types)

@app.get("/api/companies/{company_id}/emails", response_model=PaginatedEmailLogResponse, tags=["Campaigns & Emails"])
async def get_company_emails(
    company_id: UUID,
    campaign_id: Optional[UUID] = Query(None, description="Filter emails by campaign ID"),
    lead_id: Optional[UUID] = Query(None, description="Filter emails by lead ID"),
    campaign_run_id: Optional[UUID] = Query(None, description="Filter emails by campaign run ID"),
    status: Optional[str] = Query(None, description="Filter emails by status: 'opened', 'replied', or 'meeting_booked'"),
    page_number: int = Query(default=1, ge=1, description="Page number to fetch"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get paginated email logs for a company, optionally filtered by campaign ID, lead ID, campaign run ID, or status
    
    Args:
        company_id: UUID of the company
        campaign_id: Optional UUID of the campaign to filter by
        lead_id: Optional UUID of the lead to filter by
        campaign_run_id: Optional UUID of the campaign run to filter by
        status: Optional status to filter by ('opened', 'replied', or 'meeting_booked')
        page_number: Page number to fetch (default: 1)
        limit: Number of items per page (default: 20)
        current_user: Current authenticated user
        
    Returns:
        Paginated list of email logs
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Validate status parameter if provided
    valid_statuses = {'opened', 'replied', 'meeting_booked'}
    if status is not None and status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail="Invalid status. Must be one of: 'opened', 'replied', or 'meeting_booked'"
        )
    
    # Get email logs with pagination
    email_logs_response = await get_company_email_logs(
        company_id=company_id, 
        campaign_id=campaign_id, 
        lead_id=lead_id, 
        campaign_run_id=campaign_run_id,
        status=status,
        page_number=page_number,
        limit=limit
    )
    
    # Transform the response to match EmailLogResponse model
    transformed_logs = []
    for log in email_logs_response['items']:
        transformed_log = {
            'id': log['id'],
            'campaign_id': log['campaign_id'],
            'lead_id': log['lead_id'],
            'sent_at': log['sent_at'],
            'has_opened': log['has_opened'],
            'has_replied': log['has_replied'],
            'has_meeting_booked': log['has_meeting_booked'],
            'campaign_name': log['campaigns']['name'] if log['campaigns'] else None,
            'lead_name': log['leads']['name'] if log['leads'] else None,
            'lead_email': log['leads']['email'] if log['leads'] else None
        }
        transformed_logs.append(transformed_log)
    
    # Return paginated response
    return {
        'items': transformed_logs,
        'total': email_logs_response['total'],
        'page': email_logs_response['page'],
        'page_size': email_logs_response['page_size'],
        'total_pages': email_logs_response['total_pages']
    }

@app.get("/api/campaigns/{campaign_id}", response_model=EmailCampaignInDB, tags=["Campaigns & Emails"])
async def get_campaign(
    campaign_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    # Get the campaign
    campaign = await get_campaign_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(campaign["company_id"]) for company in companies):
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return campaign

@app.post("/api/campaigns/{campaign_id}/run", tags=["Campaigns & Emails"])
async def run_campaign(
    campaign_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    try:
        logger.info(f"Running campaign {campaign_id}")

        # Check for active runs
        active_runs_count = await get_active_campaign_runs_count(campaign_id)
        if active_runs_count > 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot start a new run. Campaign is already running."
            )
        
        # Get campaign details
        campaign = await get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
            
        # Get company details
        company = await get_company_by_id(campaign['company_id'])
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
            
        # Check if the company owner user is on an active subscription, or has a trial that is still valid
        has_access, error_message = await check_user_access_status(UUID(company["user_id"]))
        if not has_access:
            raise Exception(error_message)
    
        # Validate company access
        companies = await get_companies_by_user_id(current_user["id"])
        if not companies or not any(str(company["id"]) == str(campaign["company_id"]) for company in companies):
            raise HTTPException(status_code=404, detail="Campaign not found")
            
        # Check for pending upload tasks
        if await has_pending_upload_tasks(UUID(campaign['company_id'])):
            raise HTTPException(
                status_code=400,
                detail="Cannot run campaign at this time. There are leads being processed from recent file uploads. Please wait for all lead processing to complete before running the campaign."
            )
        
        # Only validate email credentials if campaign type is email or email_and_call
        if campaign['type'] == 'email' or campaign['type'] == 'email_and_call':
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
        # Get total leads count based on campaign type
        lead_count = await get_campaign_lead_count(campaign)

        # Create a new campaign run record
        campaign_run = await create_campaign_run(
            campaign_id=campaign_id,
            status="idle",
            leads_total=lead_count
        )
        
        if not campaign_run:
            raise HTTPException(
                status_code=500,
                detail="Failed to create campaign run record"
            )
        
        logger.info(f"Created campaign run {campaign_run['id']} with {lead_count} leads")
        
        # Replace background_tasks with Celery task
        from src.celery_app.tasks.run_campaign import celery_run_company_campaign
        
        # Queue the task and get the AsyncResult
        result = celery_run_company_campaign.delay(
            campaign_id=str(campaign_id), 
            campaign_run_id=str(campaign_run['id'])
        )
        
        # Store the Celery task ID immediately
        await update_campaign_run_celery_task_id(UUID(campaign_run['id']), result.id)
        
        return {"message": "Campaign request initiated successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unable to run campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 

@app.post("/api/generate-campaign", response_model=CampaignGenerationResponse, tags=["Campaigns & Emails"])
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

@app.get("/api/companies/{company_id}/cronofy-auth", response_model=CronofyAuthResponse, tags=["Calendar"])
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

    # Check if user has admin role for this company
    user_profile = await get_user_company_profile(UUID(current_user["id"]), company_id)
    if not user_profile or user_profile["role"] != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Only company administrators can connect to calendar"
        )

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

@app.delete("/api/companies/{company_id}/calendar", response_model=CronofyAuthResponse, tags=["Calendar"])
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
        # Delete existing skipped rows for this task to make it idempotent
        await delete_skipped_rows_by_task(task_id)
        
        # Initialize Supabase client with service role
        settings = get_settings()
        supabase: Client = create_client(
            settings.supabase_url,
            settings.SUPABASE_SERVICE_KEY
        )
        
        # Update task status to processing
        await update_task_status(task_id, "processing")
        
        # Download file from Supabase
        try:
            logger.info(f"Downloading file from Supabase: {file_url}")
            storage = supabase.storage.from_("leads-uploads")
            response = storage.download(file_url)
            if not response:
                raise Exception("No data received from storage")
            
            # Detect the file encoding
            raw_data = response
            result = chardet.detect(raw_data)
            detected_encoding = result['encoding']
            confidence = result['confidence']
            
            logger.info(f"Detected file encoding: {detected_encoding} with confidence: {confidence}")
            
            # If confidence is low or encoding is None, fallback to common encodings
            if not detected_encoding or confidence < 0.6:
                encodings_to_try = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            else:
                encodings_to_try = [detected_encoding]
            
            # Try different encodings
            csv_text = None
            for encoding in encodings_to_try:
                try:
                    csv_text = raw_data.decode(encoding)
                    logger.info(f"Successfully decoded file using {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    logger.warning(f"Failed to decode with {encoding} encoding, trying next...")
                    continue
            
            if csv_text is None:
                raise Exception("Failed to decode file with any known encoding")
                
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
        
        # Check if we have numbered columns (1,2,3...) or regular headers
        is_numbered_columns = all(str(i) == header for i, header in enumerate(headers, 1))
        
        if is_numbered_columns:
            # For numbered columns, get the first row which contains the actual headers
            headers_row = next(csv_data)
            # Create a mapping from numbered columns to actual header names
            column_to_header = {str(i): headers_row[str(i)] for i in range(1, len(headers_row) + 1)}
            actual_headers = list(column_to_header.values())
            #print("\nDetected numbered columns. Column to header mapping:")
            #print(column_to_header)
        else:
            # For regular headers, use them directly
            actual_headers = headers
            column_to_header = {header: header for header in headers}
            #print("\nDetected regular headers:")
            #print(actual_headers)
        
        # Create a prompt to map headers
        prompt = f"""Map the following CSV headers to our database fields. Return a JSON object where keys are the CSV headers and values are the corresponding database field names.
The mapping should be case-insensitive and handle special characters (like accents, hyphens).

CSV Headers: {', '.join(actual_headers)}

Database fields and their types:
- name (text, required) - Should be constructed from First Name and Last Name if available
- first_name (text, required) - should map from "First Name", "FirstName", "FIRST NAME" etc
- last_name (text, required) - should map from "Last Name", "LastName", "LAST NAME" etc
- email (text, required)
- company (text) - Map from Company Name
- phone_number (text) - Should map from phone_number, mobile, direct_phone, or office_phone
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

Special handling instructions:
1. Map "First Name", "FirstName", "FIRST NAME" etc to first_name
2. Map "Last Name", "LastName", "LAST NAME" etc to last_name
3. Map "Company Name", "CompanyName", "COMPANY NAME" etc to company
4. Map "phone_number", "Phone Number", "PHONE NUMBER" etc directly to phone_number field
5. Map "Mobile", "Direct", and "Office" to mobile, direct_phone, and office_phone respectively
6. Map "Industries" to industries (will be converted to array)
7. Map "Technologies" to technologies (will be converted to array)
8. Map "Company Founded Year" to company_founded_year (will be converted to integer)
9. Map "Headcount" to headcount (will be converted to integer)
10. The mapping should be case-insensitive and handle special characters

Return ONLY a valid JSON object mapping CSV headers to database field names. If a header doesn't map to any field, map it to null.
Example format: {{"First Name": "first_name", "Last Name": "last_name", "phone_number": "phone_number", "Unmatched Header": null}}"""

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
            #print("\nHeader mapping results:")
            #print(header_mapping)
            
            if is_numbered_columns:
                # For numbered columns, map from number to db field via header
                column_to_db_field = {col: header_mapping.get(header, None) 
                                    for col, header in column_to_header.items()}
            else:
                # For regular headers, map directly
                column_to_db_field = header_mapping
                
            #logger.info("\nColumn to database field mapping:")
            #logger.info(column_to_db_field)
            
        except json.JSONDecodeError:
            await update_task_status(task_id, "failed", "Failed to parse header mapping")
            return
        
        # Process each row
        row_counter = 0
        for row in csv_data:
            row_counter += 1
            logger.info(f"Processing lead {row_counter}")
            lead_data = {}
            
            # Debug print raw row data
            #print("\nProcessing row:")
            #print(row)
            
            # Map CSV data to database fields using the column mapping
            for col, db_field in column_to_db_field.items():
                if db_field and col in row:
                    value = row[col].strip() if row[col] else None
                    if value:
                        print(f"Mapping column {col} ({column_to_header[col]}) -> {db_field}: {value}")
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
            
            # Add raw data for debugging
            #print("\nRaw row data:")
            #print(row)
            #print("\nMapped lead_data before name handling:")
            #print(lead_data)
            
            # Handle name fields - directly set name if it exists in row
            if 'name' in row and row['name'].strip():
                lead_data['name'] = row['name'].strip()
            
            # Rest of name handling
            first_name = lead_data.get('first_name', '').strip()
            last_name = lead_data.get('last_name', '').strip()
            full_name = lead_data.get('name', '').strip()

            # If we have a full name but no first/last name, split it
            if full_name and not (first_name or last_name):
                name_parts = full_name.split(' ', 1)
                if len(name_parts) >= 2:
                    first_name = name_parts[0].strip()
                    last_name = name_parts[1].strip()
                
                lead_data['first_name'] = first_name
                lead_data['last_name'] = last_name
            
            # If we have first/last name but no full name, combine them
            elif (first_name or last_name) and not full_name:
                lead_data['name'] = f"{first_name} {last_name}".strip()
            
            # Ensure all name fields are set
            if not lead_data.get('name'):
                lead_data['name'] = f"{first_name} {last_name}".strip()
            if not lead_data.get('first_name'):
                lead_data['first_name'] = first_name or (lead_data['name'].split(' ')[0] if lead_data.get('name') else '')
            if not lead_data.get('last_name'):
                lead_data['last_name'] = last_name or (' '.join(lead_data['name'].split(' ')[1:]) if lead_data.get('name') else '')

            # Skip if required fields are missing
            if not lead_data.get('name'):
                #logger.info(f"Skipping record due to missing name: {row}")
                await create_skipped_row_record(
                    upload_task_id=task_id,
                    category="missing_name",
                    row_data=row
                )
                skipped_count += 1
                continue

            # Validate email format
            email = lead_data.get('email','').strip()
            try:
                # Validate and normalize the email
                email_info = validate_email(email, check_deliverability=False)
                lead_data['email'] = email_info.normalized
            except EmailNotValidError as e:
                #logger.info(f"Skipping record - invalid email format: {email}")
                #logger.info(f"Email validation error: {str(e)}")
                await create_skipped_row_record(
                    upload_task_id=task_id,
                    category="invalid_email",
                    row_data=row
                )
                skipped_count += 1
                continue

            # Handle phone number priority and validation (optional)
            phone_number = None
            phone_fields = ['phone_number', 'mobile', 'direct_phone', 'office_phone']
            
            # Try each phone field in priority order
            for field in phone_fields:
                if lead_data.get(field):
                    is_valid, formatted_number = validate_phone_number(lead_data[field])
                    if is_valid:
                        phone_number = formatted_number
                        break
            
            # If a phone number was provided but invalid, log it but don't skip the record
            if any(lead_data.get(field) for field in phone_fields) and not phone_number:
                logger.warning(f"Invalid phone number provided for lead {lead_data.get('name', 'Unknown')}, continuing without phone")
            
            # Update the lead data with the validated phone number (or None)
            lead_data['phone_number'] = phone_number

            # Skip if either company or website is missing
            if not lead_data.get('company') or not lead_data.get('website'):
                #logger.info(f"Skipping record - missing required field: company or website")
                #logger.info(f"Skipping record due to missing company or website: {row}")
                await create_skipped_row_record(
                    upload_task_id=task_id,
                    category="missing_company_name_or_website",
                    row_data=row
                )
                skipped_count += 1
                continue
            
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
                #print("\nFinal lead_data before database insert:")
                #print(lead_data)
                created_lead = await create_lead(company_id, lead_data, task_id)
                #print("\nCreated lead response:")
                #print(created_lead)
                lead_count += 1
                
                # Get complete lead data
                lead = await get_lead_by_id(created_lead['id'])

                # Enrich the lead with company insights
                await get_or_generate_insights_for_lead(lead, force_creation=True)
                # Continue processing other leads even if enrichment fails
                    
            except Exception as e:
                logger.error(f"Error creating lead: {str(e)}")
                logger.error(f"Lead data that failed: {lead_data}")
                await create_skipped_row_record(
                    upload_task_id=task_id,
                    category=f"lead_creation_error: {str(e)}",
                    row_data=row
                )
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
@app.get("/api/tasks/{task_id}", tags=["Tasks"])
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

@app.post("/api/companies/{company_id}/account-credentials", response_model=CompanyInDB, tags=["Companies"])
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
    
    # Check if user has admin role for this company
    user_profile = await get_user_company_profile(UUID(current_user["id"]), company_id)
    if not user_profile or user_profile["role"] != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Only company administrators can update account credentials"
        )

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

@app.post("/api/auth/forgot-password", response_model=ResetPasswordResponse, tags=["Authentication"])
async def forgot_password(request: ForgotPasswordRequest):
    """Request a password reset link"""
    return await request_password_reset(request.email)

@app.post("/api/auth/reset-password", response_model=ResetPasswordResponse, tags=["Authentication"])
async def reset_password_endpoint(request: ResetPasswordRequest):
    """Reset password using the reset token"""
    return await reset_password(reset_token=request.token, new_password=request.new_password)

async def run_email_campaign(campaign: dict, company: dict, campaign_run_id: UUID):
    """Handle email campaign processing by queuing emails instead of sending immediately"""
    try:
        # Validate company settings
        if not company.get("account_email") or not company.get("account_password"):
            logger.error(f"Company {campaign['company_id']} missing credentials")
            await update_campaign_run_status(campaign_run_id=campaign_run_id, status="failed", failure_reason="Missing email account credentials")
            return
                
        if not company.get("account_type"):
            logger.error(f"Company {campaign['company_id']} missing email provider type")
            await update_campaign_run_status(campaign_run_id=campaign_run_id, status="failed", failure_reason="Missing email provider type")
            return
                
        if not company.get("name"):
            logger.error(f"Company {campaign['company_id']} missing company name")
            await update_campaign_run_status(campaign_run_id=campaign_run_id, status="failed", failure_reason="Missing company name")
            return    
        
        # Get campaign template
        template = campaign.get('template')
        if not template:
            logger.error(f"Campaign {campaign['id']} missing email template")
            await update_campaign_run_status(campaign_run_id=campaign_run_id, status="failed", failure_reason="Missing campaign email template")
            return
        
        # Get total count of leads with emails
        total_leads = await get_leads_with_email(campaign['id'], count=True)
        logger.info(f"Found {total_leads} total leads with emails for campaign {campaign['id']}")

        # Update campaign run with status running
        await update_campaign_run_status(
            campaign_run_id=campaign_run_id,
            status="running"
        )

        # Process leads using keyset pagination
        leads_queued = 0
        last_id = None
        page_size = 50
        
        while True:
            # Get leads for current page
            leads_response = await get_leads_with_email(
                campaign_id=campaign['id'],
                last_id=last_id,
                limit=page_size
            )
            
            leads = leads_response['items']
            if not leads:
                break  # No more leads to process
                
            # Update last_id for next iteration - convert string to UUID if needed
            last_lead_id = leads[-1]['id']
            if isinstance(last_lead_id, str):
                last_id = UUID(last_lead_id)
            else:
                last_id = UUID(str(last_lead_id))  # Convert asyncpg UUID to Python UUID
            
            # Queue emails for each lead in this page
            for lead in leads:
                try:
                    if lead.get('email'):  # Only queue if lead has email
                        logger.info(f"Processing lead {leads_queued + 1}/{total_leads}: {lead['email']}")
                        logger.info(f"Queueing email for lead: {lead['email']}")

                        try:
                            subject = ""
                            body = ""

                            insights = await get_or_generate_insights_for_lead(lead)
                                
                            # Generate personalized email content
                            if insights:
                                subject, body = await generate_email_content(lead, campaign, company, insights)
                            else:
                                #logger.error(f"Failed to generate insights for lead {lead['email']}")
                                response = await add_email_to_queue(
                                    company_id=campaign['company_id'],
                                    campaign_id=campaign['id'],
                                    campaign_run_id=campaign_run_id,
                                    lead_id=lead['id'],
                                    subject=subject,
                                    body=body
                                )

                                await update_queue_item_status(
                                    queue_id=UUID(response['id']),
                                    status='failed',
                                    processed_at=datetime.now(timezone.utc),
                                    error_message="Failed to generate insights for lead"
                                )

                                leads_queued += 1
                                continue

                            if not subject or not body:
                                logger.error(f"Failed to generate email content for lead {lead['email']}")

                                response = await add_email_to_queue(
                                    company_id=campaign['company_id'],
                                    campaign_id=campaign['id'],
                                    campaign_run_id=campaign_run_id,
                                    lead_id=lead['id'],
                                    subject=subject,
                                    body=body
                                )

                                await update_queue_item_status(
                                    queue_id=UUID(response['id']),
                                    status='failed',
                                    processed_at=datetime.now(timezone.utc),
                                    error_message="Failed to generate email content for lead"
                                )
                                
                                leads_queued += 1
                                continue

                            #logger.info(f"Generated email content for lead: {lead['email']}")
                            #logger.info(f"Email Subject: {subject}")
                            # Replace {email_body} placeholder in template with generated body
                            final_body = template.replace("{email_body}", body)

                        except Exception as e:
                            logger.error(f"Error processing email for lead {lead['email']}: {str(e)}")
                            continue

                        # Add to queue
                        await add_email_to_queue(
                            company_id=campaign['company_id'],
                            campaign_id=campaign['id'],
                            campaign_run_id=campaign_run_id,
                            lead_id=lead['id'],
                            subject=subject,
                            body=final_body
                        )
                        leads_queued += 1
                        logger.info(f"Email for lead {lead['email']} added to queue")
                    else:
                        logger.warning(f"Skipping lead with no email: {lead.get('id')}")
                except Exception as e:
                    logger.error(f"Failed to queue email for {lead.get('email')}: {str(e)}")
                    continue
            
            if not leads_response['has_more']:
                break
                
        logger.info(f"Completed processing. Queued {leads_queued} emails for campaign {campaign['id']}")
        # Note: We don't mark the campaign as completed here
        # It will be done by the queue processor when all emails have been processed
    except Exception as e:
        logger.error(f"Error in run_email_campaign: {str(e)}")
        await update_campaign_run_status(
            campaign_run_id=campaign_run_id,
            status="failed",
            failure_reason=f"Campaign execution failed: {str(e)}"
        )
        raise

async def run_company_campaign(campaign_id: UUID, campaign_run_id: UUID):
    """Background task to run campaign of the company"""
    logger.info(f"Starting to run campaign_id: {campaign_id}")
    
    try:
        # Get campaign details
        campaign = await get_campaign_by_id(campaign_id)
        if not campaign:
            logger.error(f"Campaign not found: {campaign_id}")
            return
        
        # Get company details
        company = await get_company_by_id(campaign["company_id"])
        if not company:
            logger.error(f"Company not found for campaign: {campaign_id}")
            return
        
        # Process campaign based on type
        if campaign['type'] == 'email' or campaign['type'] == 'email_and_call':
            await run_email_campaign(campaign, company, campaign_run_id)
        elif campaign['type'] == 'call':
            await run_call_campaign(campaign, company, campaign_run_id)
            
    except Exception as e:
        logger.error(f"Unexpected error in run_company_campaign: {str(e)}")
        return

async def run_call_campaign(campaign: dict, company: dict, campaign_run_id: UUID):
    """Handle call campaign processing"""
    try:
        # Get total count of leads with phone numbers
        total_leads = await get_leads_with_phone(campaign['id'], count=True)
        logger.info(f"Found {total_leads} total leads with phone number")

        # Update campaign run with status running and total leads
        await update_campaign_run_status(
            campaign_run_id=campaign_run_id,
            status="running"
        )

        # Process leads using keyset pagination
        leads_queued = 0
        last_id = None
        page_size = 50
        
        while True:
            # Get leads for current page
            leads_response = await get_leads_with_phone(
                campaign_id=campaign['id'],
                last_id=last_id,
                limit=page_size
            )
            
            leads = leads_response['items']
            if not leads:
                break  # No more leads to process
                
            # Update last_id for next iteration - convert string to UUID if needed
            last_lead_id = leads[-1]['id']
            if isinstance(last_lead_id, str):
                last_id = UUID(last_lead_id)
            else:
                last_id = UUID(str(last_lead_id))  # Convert asyncpg UUID to Python UUID
                
            # Queue records for each lead in this page
            for lead in leads:
                call_script = ""
                
                try:
                    if not lead.get('phone_number'):
                        continue  # Skip if no phone number

                    logger.info(f"Processing lead {leads_queued + 1}/{total_leads}: {lead['phone_number']}")
                    
                    insights = await get_or_generate_insights_for_lead(lead)

                    if insights:
                        #logger.info(f"Using insights for lead: {lead['phone_number']}")

                        # Generate personalized call script
                        call_script = await generate_call_script(lead, campaign, company, insights)
                        
                        logger.info(f"Generated call script for lead: {lead['phone_number']}")
                        #logger.info(f"Call Script: {call_script}")

                        if call_script:
                            # Add to queue
                            await add_call_to_queue(
                                company_id=campaign['company_id'],
                                campaign_id=campaign['id'],
                                campaign_run_id=campaign_run_id,
                                lead_id=lead['id'],
                                call_script=call_script
                            )
                            leads_queued += 1
                            logger.info(f"Call for lead {lead['phone_number']} added to queue")

                        else:
                            logger.error(f"Failed to generate call script for lead: {lead['phone_number']}")

                            response = await add_call_to_queue(
                                    company_id=campaign['company_id'],
                                    campaign_id=campaign['id'],
                                    campaign_run_id=campaign_run_id,
                                    lead_id=lead['id'],
                                    call_script=call_script
                                )

                            await update_call_queue_item_status(
                                queue_id=UUID(response['id']),
                                status='failed',
                                processed_at=datetime.now(timezone.utc),
                                error_message="Failed to generate call script for lead"
                            )
                            
                            leads_queued += 1
                            continue

                    else:
                        #logger.error(f"Failed to generate insights for lead {lead['phone_number']}")
                        response = await add_call_to_queue(
                            company_id=campaign['company_id'],
                            campaign_id=campaign['id'],
                            campaign_run_id=campaign_run_id,
                            lead_id=lead['id'],
                            call_script=call_script
                        )

                        await update_call_queue_item_status(
                            queue_id=UUID(response['id']),
                            status='failed',
                            processed_at=datetime.now(timezone.utc),
                            error_message="Failed to generate insights for lead"
                        )

                        leads_queued += 1
                        continue

                except Exception as e:
                    logger.error(f"Failed to process call for {lead.get('phone_number')}: {str(e)}")
                    continue

            if not leads_response['has_more']:
                break

        logger.info(f"Queued {leads_queued} calls for campaign {campaign['id']}")
        # Note: We don't mark the campaign as completed here
        # It will be done by the queue processor when all calls have been processed
    except Exception as e:
        logger.error(f"Error in run_call_campaign: {str(e)}")
        await update_campaign_run_status(
            campaign_run_id=campaign_run_id,
            status="failed",
            failure_reason=f"Campaign execution failed: {str(e)}"
        )
        raise

async def verify_bland_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Verify the Bland tool secret token"""
    
    token = credentials.credentials
    logger.info(f"Received token: {token}")
    logger.info(f"Expected token: {settings.bland_secret_key}")

    #temporary hack
    return
    
    if token != settings.bland_secret_key:
        raise HTTPException(status_code=401, detail="Invalid secret token")

@app.post("/api/calls/book-appointment", tags=["Calls"])
async def book_appointment(
    request: BookAppointmentRequest,
    _: None = Depends(verify_bland_token)
):
    """
    Endpoint for Bland AI's book appointment tool.
    Requires Bearer token authentication.
    """
    try:
        await calendar_book_appointment(
            company_id=request.company_uuid,
            log_id=request.call_log_id,
            email=request.email,
            start_time=request.start_time,
            email_subject=request.email_subject,
            campaign_type="call"
        )
        return {"message": "Appointment booked successfully"}
    except Exception as e:
        logger.error(f"Failed to book appointment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/register-bland-tool", tags=["System"])
async def register_tool():
    settings = get_settings()
    bland_client = BlandClient(
        api_key=settings.bland_api_key,
        base_url=settings.bland_api_url,
        webhook_base_url=settings.webhook_base_url,
        bland_tool_id=settings.bland_tool_id,
        bland_secret_key=settings.bland_secret_key
    )

    tool = await bland_client.create_book_appointment_tool()
    logger.info(f"Tool registered: {tool}")

@app.get("/api/companies/{company_id}/emails/{email_log_id}", response_model=List[EmailLogDetailResponse], tags=["Campaigns & Emails"])
async def get_email_log_details(
    company_id: UUID,
    email_log_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all email messages for a specific email log in ascending order.
    
    Args:
        company_id: UUID of the company
        email_log_id: UUID of the email log
        current_user: Current authenticated user
        
    Returns:
        List of email log details ordered by creation time
        
    Raises:
        404: Company not found or user doesn't have access
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get email log details
    email_details = await get_email_conversation_history(email_log_id)
    
    return email_details

@app.put("/api/companies/{company_id}/voice_agent_settings", response_model=CompanyInDB, tags=["Voice Agent"])
async def update_voice_agent_settings(
    company_id: UUID,
    settings: VoiceAgentSettings,
    current_user: dict = Depends(get_current_user)
):
    """
    Update voice agent settings for a company. This will replace the entire voice_agent_settings object.
    
    Args:
        company_id: UUID of the company
        settings: Complete voice agent settings to replace existing settings, including:
            - prompt: Script template for the agent
            - voice: Voice type to use
            - background_track: Background audio track
            - temperature: AI temperature setting (0.0-1.0)
            - language: Language code
            - transfer_phone_number (optional): Phone number to transfer calls to
            - voice_settings (optional): Additional voice configuration parameters
            - noise_cancellations (optional): Whether to enable noise cancellation
            - phone_number (optional): Custom phone number to use for outbound calls
            - record (optional): Whether to record the call
        current_user: Current authenticated user
        
    Returns:
        Updated company record
        
    Raises:
        404: Company not found
        403: User doesn't have access to this company
    """
    logger.info(f"Updating voice agent settings for company {company_id}")
    logger.info(f"Received settings: {settings.model_dump()}")
    
    # Verify user has access to the company
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check if user has admin role for this company
    user_profile = await get_user_company_profile(UUID(current_user["id"]), company_id)
    if not user_profile or user_profile["role"] != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Only company administrators can update voice agent settings"
        )

    # Get current company data for comparison
    current_company = await get_company_by_id(company_id)
    if current_company and current_company.get('voice_agent_settings'):
        logger.info(f"Current voice_agent_settings: {current_company['voice_agent_settings']}")
    
    # Dump the model to a dictionary
    settings_dict = settings.model_dump()
    logger.info(f"Settings dict to be sent to database: {settings_dict}")
    
    # Update voice agent settings
    updated_company = await update_company_voice_agent_settings(
        company_id=company_id,
        settings=settings_dict
    )
    
    if not updated_company:
        logger.error("Failed to update voice agent settings")
        raise HTTPException(
            status_code=500,
            detail="Failed to update voice agent settings"
        )
    
    logger.info(f"Updated company: {updated_company}")
    return updated_company

@app.post("/api/companies/{company_id}/invite", response_model=CompanyInviteResponse, tags=["Companies"])
async def invite_users_to_company(
    company_id: UUID,
    invite_request: CompanyInviteRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Invite users to join a company. For each user:
    - If they don't exist, create them and send invite
    - If they exist, just add them to the company
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check if user has admin role for this company
    user_profile = await get_user_company_profile(UUID(current_user["id"]), company_id)
    if not user_profile or user_profile["role"] != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Only company administrators can invite users"
        )

    # Get company details for the email
    company = await get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Track results
    results = []
    
    for invite in invite_request.invites:
        try:
            # Check if user exists
            existing_user = await get_user_by_email(invite.email)
            
            if existing_user:
                # Check if user is already in the company
                existing_profile = await get_user_company_profile(UUID(existing_user["id"]), company_id)
                if existing_profile:
                    results.append({
                        "email": invite.email,
                        "status": "skipped",
                        "message": "User already exists in company"
                    })
                    continue
                
                # Add existing user to company
                profile = await create_user_company_profile(
                    user_id=UUID(existing_user["id"]),
                    company_id=company_id,
                    role=invite.role
                )
                
                # Send welcome email to existing user
                try:
                    inviter_name = current_user.get('name') if current_user.get('name') and current_user['name'].strip() else current_user['email'].split('@')[0]
                    user_name = existing_user.get('name') if existing_user.get('name') and existing_user['name'].strip() else existing_user['email'].split('@')[0]
                    await email_service.send_company_addition_email(
                        to_email=existing_user['email'],
                        user_name=user_name,
                        company_name=company["name"],
                        inviter_name=inviter_name
                    )
                except Exception as e:
                    logger.error(f"Failed to send company addition email to {existing_user['email']}: {str(e)}")
                    # Don't fail the process if email sending fails
                
                results.append({
                    "email": invite.email,
                    "status": "success",
                    "message": "Added existing user to company"
                })
                
            else:
                # Create new user
                new_user = await create_unverified_user(
                    email=invite.email,
                    name=invite.name
                )
                
                if not new_user:
                    results.append({
                        "email": invite.email,
                        "status": "error",
                        "message": "Failed to create user"
                    })
                    continue
                
                # Create user-company profile
                profile = await create_user_company_profile(
                    user_id=UUID(new_user["id"]),
                    company_id=company_id,
                    role=invite.role
                )
                
                # Create invite token
                invite_token = await create_invite_token(UUID(new_user["id"]))
                if not invite_token:
                    results.append({
                        "email": invite.email,
                        "status": "error",
                        "message": "Failed to create invite token"
                    })
                    continue
                
                # Send invite email
                try:
                    inviter_name = current_user.get('name') if current_user.get('name') and current_user['name'].strip() else current_user['email'].split('@')[0]
                    await email_service.send_invite_email(
                        to_email=invite.email,
                        company_name=company["name"],
                        invite_token=invite_token["token"],
                        inviter_name=inviter_name,
                        recipient_name=invite.name if invite.name and invite.name.strip() else invite.email.split('@')[0],
                        personalize=True
                    )
                    
                    results.append({
                        "email": invite.email,
                        "status": "success",
                        "message": "Created user and sent invite"
                    })
                except Exception as e:
                    results.append({
                        "email": invite.email,
                        "status": "partial_success",
                        "message": f"User created but failed to send invite: {str(e)}"
                    })
                    
        except Exception as e:
            results.append({
                "email": invite.email,
                "status": "error",
                "message": str(e)
            })
    
    return {
        "message": "Processed all invites",
        "results": results
    }

@app.post("/api/auth/invite-password", response_model=dict, tags=["Authentication"])
async def set_invite_password(request: InvitePasswordRequest):
    """
    Set password for a user invited to join a company.
    Validates the invite token and updates the user's password.
    
    Args:
        request: Contains the invite token and new password
        
    Returns:
        dict: A message indicating success
        
    Raises:
        HTTPException: If token is invalid or already used
    """
    # Verify token
    token_data = await get_valid_invite_token(request.token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used invite token"
        )
    
    # Hash new password
    password_hash = get_password_hash(request.password)
    
    # Update user's password and mark as verified
    await update_user(
        user_id=UUID(token_data["user_id"]),
        update_data={
            "password_hash": password_hash,
            "verified": True
        }
    )
    
    # Mark token as used
    await mark_invite_token_used(request.token)
    
    return {"message": "Password set successfully. You can now log in."}

@app.get("/api/auth/invite-token/{token}", response_model=InviteTokenResponse, tags=["Authentication"])
async def get_invite_token_info(token: str):
    """
    Get user email associated with an invite token.
    
    Args:
        token: The invite token string
        
    Returns:
        InviteTokenResponse: Contains the email of the user associated with the token
        
    Raises:
        HTTPException: If token is invalid, already used, or user not found
    """
    # Verify token exists and is valid
    token_data = await get_valid_invite_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used invite token"
        )
    
    # Get user info
    user = await get_user_by_id(UUID(token_data["user_id"]))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"email": user["email"]}

@app.get("/api/companies/{company_id}/users", response_model=List[CompanyUserResponse], tags=["Companies"])
async def get_company_users_endpoint(
    company_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all users associated with a company
    
    Args:
        company_id: UUID of the company
        current_user: Current authenticated user
        
    Returns:
        List of users with their roles in the company
        
    Raises:
        404: Company not found or user doesn't have access
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get all users for the company
    users = await get_company_users(company_id)
    return users

@app.delete("/api/user_company_profile/{user_company_profile_id}", response_model=dict, tags=["Users"])
async def delete_user_company_profile_endpoint(
    user_company_profile_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a user-company profile. Only company admins can delete profiles.
    The admin cannot delete their own profile.
    """
    # First get the profile to be deleted to get the company_id
    profile_to_delete = await get_user_company_profile_by_id(user_company_profile_id)
    if not profile_to_delete:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Get current user's profile for this company to check if they're an admin
    current_user_profile = await get_user_company_profile(
        UUID(current_user["id"]), 
        UUID(profile_to_delete["company_id"])
    )
    
    # Check if current user is an admin of the company
    if not current_user_profile or current_user_profile["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only company administrators can delete user profiles"
        )
    
    # Prevent admin from deleting their own profile
    if str(user_company_profile_id) == str(current_user_profile["id"]):
        raise HTTPException(
            status_code=400,
            detail="Administrators cannot delete their own profile"
        )
    
    # Delete the profile
    success = await delete_user_company_profile(user_company_profile_id)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete user profile"
        )
    
    return {"message": "User profile deleted successfully"}

@app.get("/api/track-email/{email_log_id}", tags=["Campaigns & Emails"])
async def track_email(email_log_id: UUID, request: Request):
    try:
        # Get User-Agent
        user_agent = request.headers.get("user-agent", "").lower()
        
        is_valid = EmailOpenDetector.is_valid_email_open(user_agent)
        email_log = await get_email_log_by_id(email_log_id)

        if email_log is None:
            logger.warning(f"Email log not found for ID {email_log_id}")
            return _return_tracking_pixel()

        if is_valid:
            logger.info(f"User initiated request detected for email_log_id {email_log_id} inside campaign_run_id {email_log.get('campaign_run_id')}. User-Agent: {user_agent}")

            # Update the email_log has_opened status using the database function
            await update_email_log_has_opened(email_log_id)

            # Get the campaign and lead            
            campaign = await get_campaign_by_id(email_log.get('campaign_id'))
            if campaign is None:
                logger.warning(f"Campaign not found for email log {email_log_id}")
                return _return_tracking_pixel()

            lead = await get_lead_by_id(email_log.get('lead_id'))
            if lead is None:
                logger.warning(f"Lead not found for email log {email_log_id}")
                return _return_tracking_pixel()

            company = await get_company_by_id(campaign.get('company_id'))
            if company is None:
                logger.warning(f"Company not found for campaign {campaign.get('id')}")
                return _return_tracking_pixel()

            # If the campaign is an "email_and_call" campaign and the trigger_call_on is after_email_open, add the call to the queue
            if (campaign.get('type') == 'email_and_call' and 
                campaign.get('trigger_call_on') == 'after_email_open' and 
                lead.get('phone_number')):
                
                call_queue_exists = await check_existing_call_queue_record(
                    company_id=campaign['company_id'],
                    campaign_id=campaign['id'],
                    campaign_run_id=email_log['campaign_run_id'],
                    lead_id=lead['id']
                )
                
                if not call_queue_exists:
                    logger.info(f"Adding call to queue for lead: {lead['name']} ({lead['phone_number']})")

                    insights = await get_or_generate_insights_for_lead(lead)
                    call_script = await generate_call_script(lead, campaign, company, insights)

                    # Add to call queue
                    await add_call_to_queue(
                        company_id=campaign['company_id'],
                        campaign_id=campaign['id'],
                        campaign_run_id=email_log['campaign_run_id'],
                        lead_id=lead['id'],
                        call_script=call_script
                    )
        else:
            logger.warning(f"Automated request detected for email_log_id {email_log_id} inside campaign_run_id {email_log.get('campaign_run_id')}, ignoring it. User-Agent: {user_agent}")
        
        return _return_tracking_pixel()

    except Exception as e:
        logger.error(f"Error tracking email open for log {email_log_id}: {str(e)}")
        return _return_tracking_pixel()

def _return_tracking_pixel():
    """Helper function to return a tracking pixel with appropriate headers"""
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    return Response(
        content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b',
        media_type='image/gif',
        headers=headers
    )

@app.get("/api/leads/search", response_model=LeadSearchResponse, tags=["Leads"])
async def search_lead(
    email: Optional[str] = Query(None, description="Email address to search for"),
    phone: Optional[str] = Query(None, description="Phone number to search for"),
    current_user: dict = Depends(get_current_user)
):
    """
    Search for a lead by email or phone number and return complete lead details with communication history.
    At least one of email or phone must be provided.
    """
    if not email and not phone:
        raise HTTPException(status_code=400, detail="Either email or phone number must be provided")

    # Try to find lead by email first
    lead = None
    if email:
        lead = await get_lead_by_email(email)

    # If not found by email, try phone
    if not lead and phone:
        lead = await get_lead_by_phone(phone)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Check if user has access to the lead's company
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(lead["company_id"]) for company in companies):
        raise HTTPException(status_code=403, detail="Not authorized to access this lead")

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
    
    # Handle enriched_data field
    if lead.get("enriched_data"):
        if isinstance(lead["enriched_data"], str):
            try:
                lead["enriched_data"] = json.loads(lead["enriched_data"])
            except json.JSONDecodeError:
                lead["enriched_data"] = None
        elif not isinstance(lead["enriched_data"], dict):
            lead["enriched_data"] = None
    
    # Get communication history
    history = await get_lead_communication_history(lead["id"])

    # Return success response with lead data and history
    return {
        "status": "success",
        "data": {
            "lead": lead,
            "communication_history": history
        }
    }

@app.delete("/api/companies/{company_id}/products/{product_id}/icp/{icp_id}", response_model=dict, tags=["Products"])
async def delete_product_icp(
    company_id: UUID,
    product_id: UUID,
    icp_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a specific ICP from a product by its ID.
    
    Args:
        company_id: UUID of the company
        product_id: UUID of the product
        icp_id: ID of the ICP to delete
        
    Returns:
        Success message
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get the product to ensure it exists and belongs to the company
    product = await get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    if str(product['company_id']) != str(company_id):
        raise HTTPException(
            status_code=403, 
            detail="This product does not belong to the specified company"
        )
    
    try:
        # Get existing ICPs
        existing_icps = await get_product_icps(product_id)
        
        # Look for the ICP with the specified ID
        icp_found = False
        updated_icps = []
        
        for icp in existing_icps:
            if icp.get('id') != icp_id:
                updated_icps.append(icp)
            else:
                icp_found = True
        
        if not icp_found:
            raise HTTPException(
                status_code=404,
                detail="ICP not found for this product"
            )
        
        # Update the product with the filtered list of ICPs
        await update_product_icps(product_id, updated_icps)
        
        return {"message": "ICP deleted successfully"}
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error deleting product ICP: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete ICP: {str(e)}"
        )

@app.delete("/api/companies/{company_id}/products/{product_id}/icp", response_model=dict, tags=["Products"])
async def delete_all_product_icps(
    company_id: UUID,
    product_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete all ICPs from a product.
    
    Args:
        company_id: UUID of the company
        product_id: UUID of the product
        
    Returns:
        Success message
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get the product to ensure it exists and belongs to the company
    product = await get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    if str(product['company_id']) != str(company_id):
        raise HTTPException(
            status_code=403, 
            detail="This product does not belong to the specified company"
        )
    
    try:
        # Update the product with an empty list of ICPs
        await update_product_icps(product_id, [])
        
        return {"message": "All ICPs deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting all product ICPs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete ICPs: {str(e)}"
        )

@app.get("/api/companies/{company_id}/campaign-runs", response_model=PaginatedCampaignRunResponse, tags=["Campaigns & Emails"])
async def get_company_campaign_runs(
    company_id: UUID,
    campaign_id: Optional[UUID] = Query(None, description="Filter runs by campaign ID"),
    page_number: int = Query(default=1, ge=1, description="Page number to fetch"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get paginated campaign runs for a company, optionally filtered by campaign ID.
    
    Args:
        company_id: UUID of the company
        campaign_id: Optional UUID of the campaign to filter runs by
        page_number: Page number to fetch (default: 1)
        limit: Number of items per page (default: 20)
        current_user: Current authenticated user
        
    Returns:
        Paginated list of campaign runs
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # If campaign_id is provided, validate it belongs to the company
    if campaign_id:
        campaign = await get_campaign_by_id(campaign_id)
        if not campaign or str(campaign["company_id"]) != str(company_id):
            raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get paginated campaign runs
    return await get_campaign_runs(company_id, campaign_id, page_number, limit)

@app.post("/api/campaigns/{campaign_id}/test-run", tags=["Campaigns & Emails"], deprecated=True)
async def run_test_campaign(
    campaign_id: UUID,
    campaign: TestRunCampaignRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    logger.info(f"Running test campaign {campaign_id}")
    
    lead_contact = campaign.lead_contact
    if not lead_contact:
        raise HTTPException(status_code=400, detail="Lead contact is required")
    
    # Get the campaign
    campaign = await get_campaign_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(campaign["company_id"]) for company in companies):
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get company details and validate email credentials
    company = await get_company_by_id(campaign["company_id"])
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Only validate email credentials if campaign type is email or email_and_call
    if campaign['type'] == 'email' or campaign['type'] == 'email_and_call':
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
    
    # Add campaign test run execution to background tasks
    background_tasks.add_task(run_company_test_campaign, campaign_id, lead_contact)
    
    return {"message": "Campaign test run request initiated successfully"}

async def run_company_test_campaign(campaign_id: UUID, lead_contact: str):
    """Background task to run test campaign of the company"""
    logger.info(f"Starting to run test campaign_id: {campaign_id}")
    
    try:
        # Get campaign details
        campaign = await get_campaign_by_id(campaign_id)
        if not campaign:
            logger.error(f"Campaign not found: {campaign_id}")
            return
        
        # Get company details
        company = await get_company_by_id(campaign["company_id"])
        if not company:
            logger.error(f"Company not found for campaign: {campaign_id}")
            return
        
        # Process campaign based on type
        if campaign['type'] == 'email' or campaign['type'] == 'email_and_call':
            await run_test_email_campaign(campaign, company, lead_contact)
        elif campaign['type'] == 'call':
            await run_test_call_campaign(campaign, company, lead_contact)
            
    except Exception as e:
        if isinstance(e, HTTPException):
            logger.error(f"Unexpected error in run_company_test_campaign: {e.detail}")
        else:
            logger.error(f"Unexpected error in run_company_test_campaign: {str(e)}", exc_info=True)
        return

@app.post("/api/companies/{company_id}/leads/{lead_id}/enrich", response_model=dict, tags=["Leads"])
async def enrich_lead(
    company_id: UUID,
    lead_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Enrich a lead with company insights from Perplexity API and save the data.
    
    Args:
        company_id: UUID of the company
        lead_id: UUID of the lead to enrich
        current_user: Current authenticated user
        
    Returns:
        Updated lead data with enrichment information
        
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
    
    await get_or_generate_insights_for_lead(lead)
    
    # Get updated lead data
    lead = await get_lead_by_id(lead_id)
    
    # Process enriched_data field to ensure it's a JSON object
    if lead.get("enriched_data"):
        if isinstance(lead["enriched_data"], str):
            try:
                lead["enriched_data"] = json.loads(lead["enriched_data"])
            except json.JSONDecodeError:
                lead["enriched_data"] = None
    
    return {"status": "success", "data": lead}

@app.get("/api/companies/{company_id}/leads/{lead_id}/callscript", response_model=CallScriptResponse, tags=["Leads"])
async def get_lead_call_script(
    company_id: UUID,
    lead_id: UUID,
    product_id: UUID = Query(..., description="Product ID to generate the call script for"),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a call script for a specific lead.
    
    Args:
        company_id: UUID of the company
        lead_id: UUID of the lead
        product_id: UUID of the product to generate the script for
        current_user: Current authenticated user
        
    Returns:
        Generated call script for the lead
        
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
    
    # Get company details
    company = await get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Create a mock campaign object for the script generation
    campaign = {
        "id": str(uuid4()),
        "company_id": str(company_id),
        "product_id": str(product_id)
    }
    
    # Process lead data to ensure proper format
    process_lead_data_for_response(lead)
    
    # Check if lead already has enriched data
    insights = None
    if lead.get('enriched_data'):
        logger.info(f"Lead {lead_id} already has enriched data, using existing insights")
        # We have enriched data, use it directly
        if isinstance(lead['enriched_data'], str):
            try:
                enriched_data = json.loads(lead['enriched_data'])
                insights = json.dumps(enriched_data)
            except json.JSONDecodeError:
                insights = lead['enriched_data']
        else:
            insights = json.dumps(lead['enriched_data'])
    
    # Generate company insights if we don't have any
    if not insights:
        logger.info(f"Generating new insights for lead: {lead_id}")
        insights = await generate_company_insights(lead, perplexity_service)
        
        # Save the insights to the lead's enriched_data if we generated new ones
        if insights:
            try:
                # Parse the insights JSON if it's a string
                enriched_data = {}
                if isinstance(insights, str):
                    # Try to extract JSON from the string response
                    insights_str = insights.strip()
                    # Check if the response is already in JSON format
                    try:
                        enriched_data = json.loads(insights_str)
                    except json.JSONDecodeError:
                        # If not, look for JSON within the string (common with LLM responses)
                        import re
                        json_match = re.search(r'```json\s*([\s\S]*?)\s*```|{[\s\S]*}', insights_str)
                        if json_match:
                            potential_json = json_match.group(1) if json_match.group(1) else json_match.group(0)
                            enriched_data = json.loads(potential_json)
                        else:
                            # If we can't extract structured JSON, store as raw text
                            enriched_data = {"raw_insights": insights_str}
                else:
                    enriched_data = insights
                
                # Update the lead with enriched data
                await update_lead_enrichment(lead['id'], enriched_data)
                logger.info(f"Updated lead {lead_id} with new enriched data")
            except Exception as e:
                logger.error(f"Error storing insights for lead {lead_id}: {str(e)}")
    
    if not insights:
        raise HTTPException(status_code=500, detail="Failed to generate insights for lead")
    
    # Generate the call script
    call_script = await generate_call_script(lead, campaign, company, insights)
    if not call_script:
        raise HTTPException(status_code=500, detail="Failed to generate call script")
    
    return {
        "status": "success",
        "data": {
            "script": call_script
        }
    }

@app.get("/api/companies/{company_id}/leads/{lead_id}/emailscript", response_model=EmailScriptResponse, tags=["Leads"])
async def get_lead_email_script(
    company_id: UUID,
    lead_id: UUID,
    product_id: UUID = Query(..., description="Product ID to generate the email script for"),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate an email script for a specific lead.
    
    Args:
        company_id: UUID of the company
        lead_id: UUID of the lead
        product_id: UUID of the product to generate the script for
        current_user: Current authenticated user
        
    Returns:
        Generated email subject and body for the lead
        
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
    
    # Get company details
    company = await get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Create a mock campaign object for the script generation
    campaign = {
        "id": str(uuid4()),
        "company_id": str(company_id),
        "product_id": str(product_id)
    }
    
    # Process lead data to ensure proper format
    process_lead_data_for_response(lead)
    
    # Check if lead already has enriched data
    insights = None
    if lead.get('enriched_data'):
        logger.info(f"Lead {lead_id} already has enriched data, using existing insights")
        # We have enriched data, use it directly
        if isinstance(lead['enriched_data'], str):
            try:
                enriched_data = json.loads(lead['enriched_data'])
                insights = json.dumps(enriched_data)
            except json.JSONDecodeError:
                insights = lead['enriched_data']
        else:
            insights = json.dumps(lead['enriched_data'])
    
    # Generate company insights if we don't have any
    if not insights:
        logger.info(f"Generating new insights for lead: {lead_id}")
        insights = await generate_company_insights(lead, perplexity_service)
        
        # Save the insights to the lead's enriched_data if we generated new ones
        if insights:
            try:
                # Parse the insights JSON if it's a string
                enriched_data = {}
                if isinstance(insights, str):
                    # Try to extract JSON from the string response
                    insights_str = insights.strip()
                    # Check if the response is already in JSON format
                    try:
                        enriched_data = json.loads(insights_str)
                    except json.JSONDecodeError:
                        # If not, look for JSON within the string (common with LLM responses)
                        import re
                        json_match = re.search(r'```json\s*([\s\S]*?)\s*```|{[\s\S]*}', insights_str)
                        if json_match:
                            potential_json = json_match.group(1) if json_match.group(1) else json_match.group(0)
                            enriched_data = json.loads(potential_json)
                        else:
                            # If we can't extract structured JSON, store as raw text
                            enriched_data = {"raw_insights": insights_str}
                else:
                    enriched_data = insights
                
                # Update the lead with enriched data
                await update_lead_enrichment(lead['id'], enriched_data)
                logger.info(f"Updated lead {lead_id} with new enriched data")
            except Exception as e:
                logger.error(f"Error storing insights for lead {lead_id}: {str(e)}")
    
    if not insights:
        raise HTTPException(status_code=500, detail="Failed to generate insights for lead")
    
    # Generate the email content
    email_content = await generate_email_content(lead, campaign, company, insights)
    if not email_content:
        raise HTTPException(status_code=500, detail="Failed to generate email content")
    
    subject, body = email_content
    
    return {
        "status": "success",
        "data": {
            "subject": subject,
            "body": body
        }
    }

@app.post("/api/companies/{company_id}/leads/{lead_id}/simulate-campaign", response_model=dict, tags=["Leads"])
async def simulate_email_campaign(
    company_id: UUID,
    lead_id: UUID,
    request: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Simulate an email campaign for a specific lead, generating the original email and all reminders.
    
    Args:
        company_id: UUID of the company
        lead_id: UUID of the lead
        request: Request body containing product_id and number_of_reminders
        current_user: Current authenticated user
        
    Returns:
        Generated original email and all reminder emails
        
    Raises:
        404: Lead not found
        403: User doesn't have access to this lead
    """
    try:
        # Import here to avoid circular imports
        from src.services.advanced_reminders import generate_enhanced_reminder
        
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
        
        # Get company details
        company = await get_company_by_id(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Extract request data
        product_id = request.get("product_id")
        if not product_id:
            raise HTTPException(status_code=400, detail="product_id is required")
            
        number_of_reminders = min(7, max(1, request.get("number_of_reminders", 7)))
        
        # Create a mock campaign object for the script generation
        campaign = {
            "id": str(uuid4()),
            "company_id": str(company_id),
            "product_id": str(product_id),
            "number_of_reminders": number_of_reminders
        }
        
        # Process lead data to ensure proper format
        process_lead_data_for_response(lead)
        
        # Get or generate insights for the lead
        insights = await get_or_generate_insights_for_lead(lead)
        if not insights:
            raise HTTPException(status_code=500, detail="Failed to generate insights for lead")
        
        # Generate the original email
        original_email = await generate_email_content(lead, campaign, company, insights)
        if not original_email:
            raise HTTPException(status_code=500, detail="Failed to generate original email")
        
        original_subject, original_body = original_email
        
        logger.info(f"Using enhanced reminder system for simulation")
        
        # Generate all reminders
        reminders = []
        
        # Create a mock email log for reminder generation with all necessary fields
        mock_log = {
            'id': str(uuid4()),
            'email_log_id': str(uuid4()),
            'lead_id': str(lead_id),
            'campaign_id': str(campaign['id']),
            'has_opened': False,
            'has_replied': False,
            'sent_at': datetime.now(timezone.utc).isoformat(),
            'last_reminder_sent': None,
            'last_reminder_sent_at': None
        }
        
        # Generate reminders based on number requested
        # Note: The enhanced system uses None for first reminder, then r1, r2, etc.
        reminder_types = [None] + [f'r{i}' for i in range(1, number_of_reminders)]
        
        for i, reminder_type in enumerate(reminder_types):
            # Simulate increasing engagement for demonstration
            # This helps showcase how the enhanced system adapts to engagement
            if i == 2:  # After second reminder  
                mock_log['has_opened'] = True
                logger.info(f"Simulating email opened for reminder {i+1}")
            elif i == 4:  # After fourth reminder
                mock_log['has_replied'] = True
                logger.info(f"Simulating email replied for reminder {i+1}")
            
            # Update last reminder sent for tracking
            mock_log['last_reminder_sent'] = reminder_type
            mock_log['last_reminder_sent_at'] = datetime.now(timezone.utc).isoformat()
            
            try:
                logger.info(f"Generating reminder {i+1} of {number_of_reminders}, type: {reminder_type}")
                
                # Generate enhanced reminder content
                reminder_subject, reminder_body = await generate_enhanced_reminder(
                    email_log=mock_log,
                    lead_id=str(lead_id),
                    campaign_id=str(campaign['id']),
                    company_id=str(company_id),
                    original_email_body=original_body,
                    reminder_type=reminder_type,
                    campaign=campaign  # Pass the mock campaign directly
                )
                
                if reminder_subject and reminder_body:
                    reminders.append({
                        "subject": reminder_subject,
                        "body": reminder_body
                    })
                    logger.info(f"Successfully generated enhanced reminder {reminder_type}")
            except Exception as e:
                logger.error(f"Error generating enhanced reminder {reminder_type}: {str(e)}")
                # Continue with other reminders even if one fails
                continue
        
        return {
            "status": "success",
            "message": "Campaign simulation generated using enhanced reminder system",
            "data": {
                "original": {
                    "subject": original_subject,
                    "body": original_body
                },
                "reminders": reminders,
                "reminder_system": "enhanced",
                "features": {
                    "behavioral_triggers": True,
                    "dynamic_content": True,
                    "progressive_strategies": True,
                    "engagement_adaptation": True
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in simulate_email_campaign: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/companies/{company_id}/email-throttle", response_model=EmailThrottleSettings, tags=["Campaigns & Emails"])
async def get_company_email_throttle(
    company_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Get email throttle settings for a company.
    
    Args:
        company_id: UUID of the company
        
    Returns:
        Email throttle settings for the company
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get throttle settings
    settings = await get_email_throttle_settings(company_id)
    return settings

@app.put("/api/companies/{company_id}/email-throttle", response_model=EmailThrottleSettings, tags=["Campaigns & Emails"])
async def update_company_email_throttle(
    company_id: UUID,
    throttle_settings: EmailThrottleSettings,
    current_user: dict = Depends(get_current_user)
):
    """
    Update email throttle settings for a company.
    
    Args:
        company_id: UUID of the company
        throttle_settings: New throttle settings
        
    Returns:
        Updated throttle settings
    """
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Update throttle settings
    updated_settings = await update_email_throttle_settings(
        company_id=company_id,
        max_emails_per_hour=throttle_settings.max_emails_per_hour,
        max_emails_per_day=throttle_settings.max_emails_per_day,
        enabled=throttle_settings.enabled
    )
    
    return updated_settings

# Helper function to process lead data for response
def process_lead_data_for_response(lead: dict):
    """Process lead data to ensure proper format for response"""
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
    
    # Handle JSON fields
    for field in ["hiring_positions", "location_move", "job_change"]:
        if lead.get(field) and isinstance(lead[field], str):
            try:
                lead[field] = json.loads(lead[field])
            except json.JSONDecodeError:
                lead[field] = None
    
    # Handle enriched_data field
    if lead.get("enriched_data"):
        if isinstance(lead["enriched_data"], str):
            try:
                lead["enriched_data"] = json.loads(lead["enriched_data"])
            except json.JSONDecodeError:
                lead["enriched_data"] = None
        elif not isinstance(lead["enriched_data"], dict):
            lead["enriched_data"] = None
    
    return lead

# Include web agent router
app.include_router(web_agent_router, prefix="/api")

# Include partner applications router
app.include_router(partner_applications_router)

# Include do-not-email routers
app.include_router(do_not_email_router)
app.include_router(do_not_email_check_router)
app.include_router(email_queues_router)

# Include campaign retry router
app.include_router(campaign_retry_router)

# Include routers
app.include_router(email_queues.router)
app.include_router(call_queues.router)
app.include_router(call_queue_status_router)
app.include_router(calendar_router)
app.include_router(accounts_router)
app.include_router(subscriptions_router)  # Add the new subscriptions router
app.include_router(checkout_sessions_router)
app.include_router(stripe_webhooks_router)  # Add the new stripe webhooks router
app.include_router(upload_tasks_router)
app.include_router(skipped_rows_router)  # Add this line
app.include_router(file_downloads_router)  # Add this line
app.include_router(companies_router)
app.include_router(linkedin_router)  # LinkedIn routes
app.include_router(unipile_webhooks_router)  # Unipile webhook routes

@app.post("/api/campaigns/{campaign_id}/summary-email", response_model=Dict[str, str])
async def send_campaign_summary_email_endpoint(
    campaign_id: UUID,
    request: Dict[str, str] = Body(...),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Send a comprehensive campaign summary email
    
    - **campaign_id**: UUID of the campaign
    - **request**: Body containing recipient_email and optional recipient_first_name
    """
    try:
        # Verify user has permission for this campaign
        campaign = await get_campaign_by_id(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign not found: {campaign_id}"
            )
            
        # Check company association
        if str(campaign['company_id']) not in [role.company_id for role in current_user.company_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this campaign"
            )
            
        # Get the recipient email from the request body
        recipient_email = request.get('recipient_email')
        if not recipient_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="recipient_email is required"
            )
            
        # Get optional recipient first name
        recipient_first_name = request.get('recipient_first_name')
            
        # Import the function to send summary email
        from src.scripts.generate_simple_campaign_summary import send_simple_summary_email
        
        # Send the email asynchronously
        await send_simple_summary_email(campaign_id, recipient_email, recipient_first_name)
        
        return {
            "status": "success",
            "message": f"Campaign summary email sent to {recipient_email}"
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending campaign summary email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send campaign summary email: {str(e)}"
        )

class EmailQueueStatus(str, Enum):
    all = "all"
    sent = "sent"
    failed = "failed"
    skipped = "skipped"
    pending = "pending"
    processing = "processing"

@app.get("/api/campaigns/{campaign_run_id}/email-queues", response_model=PaginatedEmailQueueResponse, tags=["Campaigns & Emails"])
async def get_campaign_run_email_queues(
    campaign_run_id: UUID,
    page_number: int = Query(default=1, ge=1, description="Page number to fetch"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    status: Optional[EmailQueueStatus] = Query(default=EmailQueueStatus.all, description="Filter by email status"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get paginated list of email queues for a specific campaign run
    
    Args:
        campaign_run_id: UUID of the campaign run
        page_number: Page number to fetch (default: 1)
        limit: Number of items per page (default: 20)
        current_user: Current authenticated user
        
    Returns:
        Paginated list of email queues
    """
    # Get the campaign run to verify access
    campaign_run = await get_campaign_run(campaign_run_id)
    if not campaign_run:
        raise HTTPException(status_code=404, detail="Campaign run not found")
    
    # Get the campaign to verify company access
    campaign = await get_campaign_by_id(campaign_run['campaign_id'])
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check if user has access to the company
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(campaign["company_id"]) for company in companies):
        raise HTTPException(status_code=403, detail="Not authorized to access this campaign")
    
    # Get paginated email queues
    return await get_email_queues_by_campaign_run(
        campaign_run_id=campaign_run_id,
        page_number=page_number,
        limit=limit,
        status=status.value if status != EmailQueueStatus.all else None
    )

def main():
    """Main entry point for running ReachGenie server"""
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()

