from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Request, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import RedirectResponse
from datetime import timedelta, datetime
import csv
import io
import logging
from typing import List, Dict
from uuid import UUID
from openai import AsyncOpenAI
import json

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
    LeadsUploadResponse
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
    get_email_conversation_history
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
                logger.info(f"Sending email to {lead['email']}")
                # Create email log first
                email_log = await create_email_log(
                    campaign_id=campaign_id,
                    lead_id=lead['id'],
                    sent_at=datetime.utcnow().isoformat()
                )
                logger.info(f"Created email_log with id: {email_log['id']}")
                
                # Send email with log ID as CustomID and for email_log_details
                await mailjet.send_email(
                    to_email=lead['email'],
                    to_name=lead['name'],
                    subject=campaign['email_subject'],
                    html_content=campaign['email_body'],
                    custom_id=str(email_log['id']),
                    email_log_id=email_log['id'],
                    sender_type='assistant'  # This is an assistant-initiated email
                )
                logger.info(f"Successfully sent email to {lead['email']}")
        except Exception as e:
            logger.error(f"Failed to send email to {lead.get('email')}: {str(e)}")
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

async def book_appointment(email: str, name: str) -> Dict[str, str]:
    """
    Create a Calendly scheduling link for the lead
    
    Args:
        email: Lead's email address
        name: Lead's name
        
    Returns:
        Dict containing the Calendly scheduling link
    """
    settings = get_settings()
    
    # Using Calendly direct scheduling link
    # The URL parameters will pre-fill the booking form
    calendly_url = f"https://calendly.com/{settings.calendly_username}/30min"
    scheduling_url = f"{calendly_url}?name={name}&email={email}"
    
    return {
        "booking_url": scheduling_url,
        "message": "You can schedule a meeting at your preferred time using this link."
    }

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
    logger.info(f"Received webhook payload: {payload}")
    
    # Extract CustomID, email content and headers
    custom_id = payload.get('CustomID')
    email_text = payload.get('Text-part', '')
    headers = payload.get('Headers', {})
    from_email = payload.get('Sender', '')  # Get sender's email
    from_field = payload.get('From', '')    # Get the full From field
    
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
    
    if not custom_id:
        raise HTTPException(status_code=400, detail="Missing CustomID")
    
    try:
        email_log_id = UUID(custom_id)
        
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
                
                # Define the function for OpenAI
                functions = [
                    {
                        "name": "book_appointment",
                        "description": "Book a meeting or appointment with the lead",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "email": {
                                    "type": "string",
                                    "description": "Lead's email address"
                                },
                                "name": {
                                    "type": "string",
                                    "description": "Lead's name"
                                }
                            },
                            "required": ["email", "name"]
                        }
                    }
                ]
                
                # Format conversation for OpenAI
                messages = [
                    {
                        "role": "system",
                        "content": """You are an AI sales assistant. Your goal is to engage with potential customers professionally and helpfully.
                        
                        Guidelines for responses:
                        1. Keep responses concise and focused on addressing the customer's needs and concerns
                        2. If a customer expresses disinterest, acknowledge it politely and end the conversation
                        3. If a customer shows interest or asks questions, provide relevant information and guide them towards the next steps
                        4. If the customer asks to schedule a meeting or shows strong interest in discussing further, use the book_appointment function
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
                        [Your name]
                        Sales Team"""
                    }
                ]
                
                # Add conversation history
                for msg in conversation_history:
                    messages.append({
                        "role": msg['sender_type'],  # Use the stored sender_type
                        "content": msg['email_body']
                    })
                
                # Get AI response with function calling
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    functions=functions,
                    function_call="auto",
                    temperature=0.7,
                    max_tokens=500
                )
                
                response_message = response.choices[0].message
                
                # Handle function calling if present
                booking_info = None
                if response_message.function_call:
                    if response_message.function_call.name == "book_appointment":
                        # Parse the function arguments
                        function_args = json.loads(response_message.function_call.arguments)
                        
                        # Call the booking function
                        booking_info = await book_appointment(
                            email=function_args["email"],
                            name=function_args["name"]
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
                    custom_id=str(email_log_id),  # Use the same email_log_id
                    email_log_id=email_log_id,    # Use the same email_log_id
                    sender_type='assistant'       # This is an assistant response
                )
                logger.info(f"Sent AI response to {from_email} ({recipient_name})")
                
            except Exception as e:
                logger.error(f"Failed to create email_log_detail or send response: {str(e)}")
                logger.error(f"email_log_id: {email_log_id}, message_id: {message_id}")
                raise  # Re-raise to be caught by outer try-except
        else:
            logger.error("No Message-ID found in headers")
            return {"status": "error", "message": "No Message-ID found in headers"}
        
        # Analyze sentiment using OpenAI
        prompt = f"""Based on the following email reply, categorize the sentiment as one of: Positive, Neutral, or Negative.
        Positive: Indicates interest or willingness to proceed.
        Neutral: Requests more information or clarification.
        Negative: Indicates disinterest or rejection.
        
        Email reply:
        {email_text}
        
        Respond with only one word: Positive, Neutral, or Negative."""
        
        sentiment_response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that categorizes email sentiment."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=10
        )
        
        sentiment = sentiment_response.choices[0].message.content.strip()
        
        # Update email log with sentiment
        await update_email_log_sentiment(email_log_id, sentiment.lower())
        logger.info(f"Updated email_log sentiment to: {sentiment}")
        
    except ValueError:
        logger.error(f"Invalid UUID in CustomID: {custom_id}")
        return {"status": "error", "message": "Invalid UUID in CustomID"}
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