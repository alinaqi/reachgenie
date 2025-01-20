from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Request, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import RedirectResponse
from datetime import timedelta, datetime
import csv
import io
import logging
from typing import List, Dict, Optional
from uuid import UUID
from openai import AsyncOpenAI
import json
import pycronofy
import uuid
import asyncio

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from src.models import (
    UserCreate, CompanyCreate, ProductCreate, LeadCreate,
    CompanyInDB, ProductInDB, LeadInDB, CallInDB, Token,
    BlandWebhookPayload, EmailCampaignCreate, EmailCampaignInDB,
    CampaignGenerationRequest, CampaignGenerationResponse,
    LeadsUploadResponse, CronofyAuthResponse
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
    get_company_by_id,
    update_call_webhook_data,
    get_calls_by_company_id,
    create_email_campaign,
    get_email_campaigns_by_company,
    get_email_campaign_by_id,
    get_leads_for_campaign,
    create_email_log,
    update_email_log_sentiment,
    create_email_log_detail,
    get_email_conversation_history,
    update_company_cronofy_tokens,
    update_company_cronofy_profile,
    clear_company_cronofy_data,
    get_company_id_from_email_log,
    update_product_details
)
from src.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, settings
)
from src.perplexity_enrichment import PerplexityEnricher
from src.config import get_settings
from src.bland_client import BlandClient
from src.mailjet_client import MailjetClient

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
    access_token = create_access_token(
        data={"sub": user["email"]}
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
    
    return await update_product_details(product_id, product.product_name, product.description)

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
@app.post("/api/companies/{company_id}/leads/upload", response_model=LeadsUploadResponse)
async def upload_leads(
    company_id: UUID,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    contents = await file.read()
    csv_text = contents.decode()
    csv_data = csv.DictReader(io.StringIO(csv_text))
    lead_count = 0
    skipped_count = 0
    unmapped_headers = set()
    
    # Get CSV headers
    headers = csv_data.fieldnames
    if not headers:
        raise HTTPException(status_code=400, detail="CSV file has no headers")
    
    # Initialize OpenAI client
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    # Create a prompt to map headers to expected fields
    prompt = f"""Map the following CSV headers to the expected lead data fields. Return a JSON object where keys are the CSV headers and values are the corresponding expected field names.

CSV Headers: {', '.join(headers)}

Expected fields:
- name (for full name)
- email (for email address)
- company (for company name)
- phone_number (for phone number)
- company_size (for number of employees)
- job_title (for job title/position)
- company_facebook (for Facebook URL)
- company_twitter (for Twitter URL)
- company_revenue (for company revenue)

Return ONLY a valid JSON object mapping CSV headers to expected field names. If a header doesn't map to any expected field, map it to null.
Example format: {{"CSV Header 1": "name", "CSV Header 2": "email", "Unmatched Header": null}}"""

    # Get header mapping from OpenAI
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that maps CSV headers to expected field names. Respond only with valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=500
    )
    
    try:
        header_mapping = json.loads(response.choices[0].message.content.strip())
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse header mapping")
    
    # Log unmapped headers
    for header, mapped_field in header_mapping.items():
        if mapped_field is None:
            unmapped_headers.add(header)
            logger.info(f"Unmapped header found: {header}")
    
    # Initialize Perplexity enricher
    enricher = PerplexityEnricher(settings.perplexity_api_key)
    
    # Process each row with the mapped headers
    for row in csv_data:
        lead_data = {}
        
        # Map CSV data to expected fields using the header mapping
        for csv_header, expected_field in header_mapping.items():
            if expected_field and csv_header in row:
                lead_data[expected_field] = row[csv_header]
        
        # Skip record if name is not present
        if not lead_data.get('name'):
            logger.info(f"Skipping record due to missing name field: {row}")
            skipped_count += 1
            continue
        
        # Enrich lead data with Perplexity if any required fields are missing
        if not all([lead_data.get(field) for field in ["email", "phone_number", "job_title", "company_size", "company_revenue", "company_facebook", "company_twitter"]]):
            lead_data = await enricher.enrich_lead_data(lead_data)
        
        await create_lead(company_id, lead_data)
        lead_count += 1
    
    return LeadsUploadResponse(
        message="Leads upload completed",
        leads_saved=lead_count,
        leads_skipped=skipped_count,
        unmapped_headers=list(unmapped_headers)
    )

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
    
    # Initialize Mailjet client
    mailjet = MailjetClient(
        api_key=settings.mailjet_api_key,
        api_secret=settings.mailjet_api_secret,
        sender_email=settings.mailjet_sender_email,
        sender_name=settings.mailjet_sender_name
    )
    
    # Get campaign details
    campaign = await get_email_campaign_by_id(campaign_id)
    if not campaign:
        logger.error(f"Campaign not found: {campaign_id}")
        return
    
    # Get all leads for the campaign
    leads = await get_leads_for_campaign(campaign_id)
    logger.info(f"Found {len(leads)} leads for campaign")
    
    # Send emails to each lead
    for lead in leads:
        try:
            if lead.get('email'):  # Only send if lead has email
                logger.info(f"Processing email for lead: {lead['email']}")
                
                # Create email log first and wait for it to complete
                try:
                    email_log = await create_email_log(
                        campaign_id=campaign_id,
                        lead_id=lead['id'],
                        sent_at=datetime.utcnow().isoformat()
                    )
                    logger.info(f"Created email_log with id: {email_log['id']}")
                except Exception as e:
                    logger.error(f"Error creating email log: {str(e)}")
                    continue
                # Log the data we're about to send
                logger.info(f"Preparing to send email with custom_id: {str(email_log['id'])}")
                
                # Only proceed with sending email after email_log is created
                try:
                    await mailjet.send_email(
                        to_email=lead['email'],
                        to_name=lead['name'],
                        subject=campaign['email_subject'],
                        html_content=campaign['email_body'],
                        email_log_id=email_log['id'],
                        sender_type='assistant'
                    )
                    logger.info(f"Successfully sent email to {lead['email']} with custom_id: {str(email_log['id'])}")
                except Exception as e:
                    logger.error(f"Error sending email: {str(e)}")
                    continue
                
        except Exception as e:
            logger.error(f"Failed to process email for {lead.get('email')}: {str(e)}")
            continue

@app.post("/api/email-campaigns/{campaign_id}/run")
async def run_email_campaign(
    campaign_id: UUID,
    background_tasks: BackgroundTasks,
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
    
    # Add email sending to background tasks
    background_tasks.add_task(send_campaign_emails, campaign_id)
    
    return {"message": "Email campaign started successfully"} 

async def book_appointment(company_id: UUID, email: str, start_time: datetime, email_subject: str = "Sales Discussion") -> Dict[str, str]:
    """
    Create a calendar event using Cronofy
    
    Args:
        company_id: UUID of the company
        email: Lead's email address
        start_time: datetime for when the meeting should start
        email_subject: Subject line to use for the event summary
        
    Returns:
        Dict containing the event details
    """
    settings = get_settings()
    
    # Clean up the subject line by removing 'Re:' prefix
    cleaned_subject = email_subject.strip()
    if cleaned_subject.lower().startswith('re:'):
        cleaned_subject = cleaned_subject[3:].strip()
    
    logger.info(f"Company ID: {company_id}")
    logger.info(f"Attendee/Lead Email: {email}")
    logger.info(f"Meeting start time: {start_time}")
    logger.info(f"Event summary: {cleaned_subject}")

    # Get company to get Cronofy credentials
    company = await get_company_by_id(company_id)
    if not company or not company.get('cronofy_access_token'):
        raise HTTPException(status_code=400, detail="No Cronofy connection found")
    
    # Initialize Cronofy client
    cronofy = pycronofy.Client(
        client_id=settings.cronofy_client_id,
        client_secret=settings.cronofy_client_secret,
        access_token=company['cronofy_access_token'],
        refresh_token=company['cronofy_refresh_token']
    )
    
    end_time = start_time + timedelta(minutes=30)
    
    # Format times in ISO 8601 format with Z suffix for UTC
    start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    event = {
        'event_id': str(uuid.uuid4()),
        'summary': cleaned_subject,
        'start': start_time_str,
        'end': end_time_str,
        'attendees': {
            'invite': [{'email': email}]
        }
    }
    
    try:
        cronofy.upsert_event(
            calendar_id=company['cronofy_default_calendar_id'],
            event=event
        )
        
        return {
            "message": f"Meeting scheduled for {start_time.strftime('%Y-%m-%d %H:%M')} UTC"
        }
    except pycronofy.exceptions.PyCronofyRequestError as e:
        if getattr(e.response, 'status_code', None) == 401:
            try:
                # Refresh the token
                logger.info("Refreshing Cronofy token")
                auth = cronofy.refresh_authorization()
                
                # Update company with new tokens
                await update_company_cronofy_tokens(
                    company_id=company_id,
                    access_token=auth['access_token'],
                    refresh_token=auth['refresh_token']
                )
                
                # Retry the event creation with new token
                cronofy = pycronofy.Client(
                    client_id=settings.cronofy_client_id,
                    client_secret=settings.cronofy_client_secret,
                    access_token=auth['access_token']
                )
                
                cronofy.upsert_event(
                    calendar_id=company['cronofy_default_calendar_id'],
                    event=event
                )
                
                return {
                    "message": f"Meeting scheduled for {start_time.strftime('%Y-%m-%d %H:%M')} UTC"
                }
            except Exception as refresh_error:
                logger.error(f"Error refreshing token: {str(refresh_error)}")
                raise HTTPException(status_code=500, detail="Failed to refresh calendar authorization")
        else:
            logger.error(f"Error creating Cronofy event: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to schedule meeting")
    except Exception as e:
        logger.error(f"Error creating Cronofy event: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to schedule meeting")

@app.post("/api/incoming-email")
async def handle_mailjet_webhook(
    request: Request,
    secret: str = Query(..., description="Webhook secret key for authentication")
):
    """
    Handle incoming email webhook from Mailjet
    """
    settings = get_settings()
    
    # Initialize OpenAI client at the start
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    # Validate webhook secret
    if secret != settings.mailjet_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    
    # Get webhook payload
    payload = await request.json()
    logger.info(f"Received webhook payload: {json.dumps(payload, indent=2)}")
        
    email_text = payload.get('Text-part', '')
    headers = payload.get('Headers', {})
    from_email = payload.get('Sender', '')  # Get sender's email
    from_field = payload.get('From', '')    # Get the full From field
    recipient_email = payload.get('Recipient', '')  # Get the Recipient field
    
    # Extract email_log_id from Recipient field
    try:
        # Format: prefix+email_log_id@domain
        email_log_id_str = recipient_email.split('+')[1].split('@')[0]
        email_log_id = UUID(email_log_id_str)
        logger.info(f"Extracted email_log_id from Recipient field: {email_log_id}")
    except (IndexError, ValueError) as e:
        logger.error(f"Failed to extract valid email_log_id from Recipient field: {recipient_email}")
        raise HTTPException(status_code=400, detail="Invalid or missing email_log_id in Recipient field")
    
    # Extract name from From field (format: "Name <email@domain.com>")
    recipient_name = from_email.split('@')[0]  # Default to email username
    if from_field:
        try:
            # Try to extract name from "Name <email>" format
            if '<' in from_field and '>' in from_field:
                recipient_name = from_field.split('<')[0].strip()
        except Exception as e:
            logger.error(f"Error extracting name from From field: {str(e)}")
    
    # Get Message-ID from headers (could be 'Message-Id' or 'Message-ID')
    message_id = headers.get('Message-Id') or headers.get('Message-ID', '')
    subject = payload.get('Subject', '')
        
    try:
        # Create email_log_details record for the incoming email
        if message_id:
            try:
                logger.info(f"Attempting to create email_log_detail with message_id: {message_id}")
                await create_email_log_detail(
                    email_logs_id=email_log_id,
                    message_id=message_id,
                    email_subject=subject,
                    email_body=email_text,
                    sender_type='user'  # This is a user reply
                )
                logger.info(f"Successfully created email_log_detail for message_id: {message_id}")
                
                # Get the conversation history
                conversation_history = await get_email_conversation_history(email_log_id)
                logger.info(f"Found {len(conversation_history)} messages in conversation history")
                
                # Get company_id from email_log
                company_id = await get_company_id_from_email_log(email_log_id)
                if not company_id:
                    raise HTTPException(status_code=400, detail="Could not find company for this conversation")
                
                # Get company to check Cronofy credentials
                company = await get_company_by_id(company_id)
                
                # Initialize functions list
                functions = []
                
                # Only add book_appointment function if company has Cronofy integration
                if company and company.get('cronofy_access_token') and company.get('cronofy_refresh_token'):
                    functions.append({
                        "name": "book_appointment",
                        "description": """Schedule a sales meeting with the customer. Use this function when:
1. The customer explicitly asks to schedule a meeting/call
2. The customer asks about availability for a discussion
3. The customer shows strong interest in learning more and suggests a live conversation
4. The customer mentions wanting to talk to someone directly
5. The customer asks about demo or product demonstration
6. The customer expresses interest in discussing pricing or specific features in detail

The function will schedule a 30-minute meeting at the specified time.""",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "company_id": {
                                    "type": "string",
                                    "description": "UUID of the company - use the exact company_id provided in the system prompt"
                                },
                                "email": {
                                    "type": "string",
                                    "description": "Email address of the attendee - use the exact from_email provided in the system prompt"
                                },
                                "start_time": {
                                    "type": "string",
                                    "description": "ISO 8601 formatted date-time string for when the meeting should start (e.g. '2024-03-20T14:30:00Z')",
                                    "format": "date-time"
                                },
                                "email_subject": {
                                    "type": "string",
                                    "description": "Use the exact email_subject provided in the system prompt"
                                }
                            },
                            "required": ["company_id", "email", "start_time", "email_subject"]
                        }
                    })
                
                # Format conversation for OpenAI
                messages = [
                    {
                        "role": "system",
                        "content": f"""You are an AI sales assistant. Your goal is to engage with potential customers professionally and helpfully.
                        
                        Guidelines for responses:
                        1. Keep responses concise and focused on addressing the customer's needs and concerns
                        2. If a customer expresses disinterest, acknowledge it politely and end the conversation
                        3. If a customer shows interest or asks questions, provide relevant information and guide them towards the next steps
                        4. When handling meeting requests:
                           {
                           f'''- If a customer asks for a meeting without specifying a time, ask them for their preferred date and time
                           - If they only mention a date (e.g., "tomorrow" or "next week"), ask them for their preferred time
                           - Only use the book_appointment function when you have both a specific date AND time
                           - Use the book_appointment function with:
                             * company_id: "{str(company_id)}"
                             * email: "{from_email}"
                             * email_subject: "{subject}"
                             * start_time: the ISO 8601 formatted date-time specified by the customer''' if company and company.get('cronofy_access_token') and company.get('cronofy_refresh_token') else
                           '- If a customer asks for a meeting, politely inform them that our calendar system is not currently set up and ask them to suggest a few time slots via email'
                           }
                        5. Always maintain a professional and courteous tone
                        
                        Format your responses with proper structure:
                        - Start with a greeting on a new line
                        - Use paragraphs to separate different points
                        - Add a line break between paragraphs
                        - End with a professional signature on a new line
                        
                        Example format:
                        Hello [Name],
                        
                        [First point or response to their question]
                        
                        [Additional information or next steps if needed]
                        
                        Best regards,
                        Sales Team"""
                    }
                ]
                
                # Add conversation history
                for msg in conversation_history:
                    messages.append({
                        "role": msg['sender_type'],  # Use the stored sender_type
                        "content": msg['email_body']
                    })

                logger.info(f"OpenAI RequestMessages: {messages}")
                
                # Prepare OpenAI API call parameters
                openai_params = {
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 500
                }
                
                # Only include functions if we have any
                if functions:
                    openai_params["functions"] = functions
                    openai_params["function_call"] = "auto"
                
                # Get AI response
                response = await client.chat.completions.create(**openai_params)
                
                response_message = response.choices[0].message
                
                # Handle function calling if present
                booking_info = None
                if response_message.function_call:
                    if response_message.function_call.name == "book_appointment":
                        # Parse the function arguments
                        function_args = json.loads(response_message.function_call.arguments)

                        logger.info("Calling book_appointment function")
                        
                        # Call the booking function
                        booking_info = await book_appointment(
                            company_id=UUID(function_args["company_id"]),
                            email=function_args["email"],
                            start_time=datetime.fromisoformat(function_args["start_time"].replace('Z', '+00:00')),
                            email_subject=function_args["email_subject"]
                        )
                        
                        # Add the function response to the messages
                        messages.append({
                            "role": "function",
                            "name": "book_appointment",
                            "content": json.dumps(booking_info)
                        })
                        
                        # Get the final response with the booking information
                        final_response = await client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=messages,
                            temperature=0.7,
                            max_tokens=500
                        )
                        
                        ai_reply = final_response.choices[0].message.content.strip()
                else:
                    ai_reply = response_message.content.strip()
                
                # Format AI reply with HTML
                html_template = """
                <div style="font-family: Arial, sans-serif; line-height: 1.6;">
                    {}
                </div>
                """
                formatted_reply = html_template.format(ai_reply.replace('\n', '<br>'))
                
                # Initialize Mailjet client for sending the response
                mailjet = MailjetClient(
                    api_key=settings.mailjet_api_key,
                    api_secret=settings.mailjet_api_secret,
                    sender_email=settings.mailjet_sender_email,
                    sender_name=settings.mailjet_sender_name
                )
                
                # Send AI's response using the same email_log_id
                response_subject = f"Re: {subject}" if not subject.startswith('Re:') else subject
                await mailjet.send_email(
                    to_email=from_email,
                    to_name=recipient_name,
                    subject=response_subject,
                    html_content=formatted_reply,
                    email_log_id=email_log_id,    # Use the same email_log_id
                    sender_type='assistant',      # This is an assistant response
                    in_reply_to=message_id        # Pass the Message-ID from the incoming email
                )
                logger.info(f"Sent AI response to {from_email} ({recipient_name})")
                
            except Exception as e:
                logger.error(f"Failed to create email_log_detail or send response: {str(e)}")
                logger.error(f"email_log_id: {email_log_id}, message_id: {message_id}")
                raise  # Re-raise to be caught by outer try-except
        else:
            logger.error("No Message-ID found in headers")
            return {"status": "error", "message": "No Message-ID found in headers"}        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        logger.exception("Full traceback:")
        return {"status": "error", "message": str(e)}
    
    return {"status": "success"}

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