from supabase import create_client, Client
from src.config import get_settings
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime, timezone
from fastapi import HTTPException
from src.utils.encryption import encrypt_password
import logging
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

settings = get_settings()
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)

async def get_user_by_email(email: str):
    response = supabase.table('users').select('*').eq('email', email).execute()
    return response.data[0] if response.data else None

async def create_user(email: str, password_hash: str):
    user_data = {'email': email, 'password_hash': password_hash}
    response = supabase.table('users').insert(user_data).execute()
    return response.data[0]

async def update_user(user_id: UUID, update_data: dict):
    """
    Update user details in the database
    
    Args:
        user_id: UUID of the user to update
        update_data: Dictionary containing the fields to update
        
    Returns:
        Dict containing the updated user record
    """
    response = supabase.table('users').update(update_data).eq('id', str(user_id)).execute()
    return response.data[0] if response.data else None

async def get_companies_by_user_id(user_id: UUID):
    response = supabase.table('companies').select('*').eq('user_id', str(user_id)).execute()
    return response.data

async def db_create_company(
    user_id: UUID, 
    name: str, 
    address: Optional[str], 
    industry: Optional[str], 
    website: Optional[str] = None,
    overview: Optional[str] = None,
    background: Optional[str] = None,
    products_services: Optional[str] = None
):
    company_data = {
        'user_id': str(user_id),
        'name': name,
        'address': address,
        'industry': industry,
        'website': website,
        'overview': overview,
        'background': background,
        'products_services': products_services
    }
    response = supabase.table('companies').insert(company_data).execute()
    return response.data[0]

async def db_create_product(company_id: UUID, product_name: str, file_name: Optional[str] = None, original_filename: Optional[str] = None, description: Optional[str] = None):
    product_data = {
        'company_id': str(company_id),
        'product_name': product_name,
        'file_name': file_name,
        'original_filename': original_filename,
        'description': description
    }
    response = supabase.table('products').insert(product_data).execute()
    return response.data[0]

async def get_products_by_company(company_id: UUID):
    response = supabase.table('products').select('*').eq('company_id', str(company_id)).execute()
    return response.data

async def create_lead(company_id: UUID, lead_data: dict):
    lead_data['company_id'] = str(company_id)
    response = supabase.table('leads').insert(lead_data).execute()
    return response.data[0]

async def get_leads_by_company(company_id: UUID):
    response = supabase.table('leads').select('*').eq('company_id', str(company_id)).execute()
    return response.data

async def create_call(lead_id: UUID, product_id: UUID, company_id: UUID):
    call_data = {
        'lead_id': str(lead_id),
        'product_id': str(product_id),
        'company_id': str(company_id)
    }
    response = supabase.table('calls').insert(call_data).execute()
    return response.data[0]

async def update_call_summary(call_id: UUID, duration: int, sentiment: str, summary: str):
    call_data = {
        'duration': duration,
        'sentiment': sentiment,
        'summary': summary
    }
    response = supabase.table('calls').update(call_data).eq('id', str(call_id)).execute()
    return response.data[0]

async def get_call_summary(call_id: UUID):
    response = supabase.table('calls').select('*').eq('id', str(call_id)).execute()
    return response.data[0] if response.data else None

async def get_lead_by_id(lead_id: UUID):
    response = supabase.table('leads').select('*').eq('id', str(lead_id)).execute()
    return response.data[0] if response.data else None

async def get_product_by_id(product_id: UUID):
    response = supabase.table('products').select('*').eq('id', str(product_id)).execute()
    if not response.data:
        return None
    return response.data[0]

async def update_call_details(call_id: UUID, bland_call_id: str):
    call_data = {
        'bland_call_id': bland_call_id
    }
    response = supabase.table('calls').update(call_data).eq('id', str(call_id)).execute()
    return response.data[0]

async def get_company_by_id(company_id: UUID):
    response = supabase.table('companies').select('*').eq('id', str(company_id)).execute()
    return response.data[0] if response.data else None

async def update_call_webhook_data(bland_call_id: str, duration: str, sentiment: str, summary: str):
    call_data = {
        'duration': int(float(duration)),
        'sentiment': sentiment,
        'summary': summary
    }
    response = supabase.table('calls').update(call_data).eq('bland_call_id', bland_call_id).execute()
    return response.data[0] if response.data else None

async def get_calls_by_companies(company_ids: List[str]):
    # Get all leads for the companies
    leads_response = supabase.table('leads').select('id').in_('company_id', company_ids).execute()
    lead_ids = [lead['id'] for lead in leads_response.data]
    
    # Get all products for the companies
    products_response = supabase.table('products').select('id').in_('company_id', company_ids).execute()
    product_ids = [product['id'] for product in products_response.data]
    
    # Get calls that match either lead_id or product_id
    if not lead_ids and not product_ids:
        return []
        
    # Get calls with their related data
    response = supabase.table('calls').select(
        '*,leads(*),products(*)'
    ).in_('lead_id', lead_ids).execute()
    
    # Get calls for products if there are any product IDs
    if product_ids:
        product_response = supabase.table('calls').select(
            '*,leads(*),products(*)'
        ).in_('product_id', product_ids).execute()
        response.data.extend(product_response.data)
    
    # Remove duplicates and add lead_name and product_name
    seen_ids = set()
    unique_calls = []
    for call in response.data:
        if call['id'] not in seen_ids:
            seen_ids.add(call['id'])
            # Add lead_name and product_name to the call record
            call['lead_name'] = call['leads']['name'] if call.get('leads') else None
            call['product_name'] = call['products']['product_name'] if call.get('products') else None
            unique_calls.append(call)
    
    return unique_calls 

async def get_calls_by_company_id(company_id: UUID):
    # Get calls with their related data
    response = supabase.table('calls').select(
        'id,lead_id,product_id,duration,sentiment,summary,bland_call_id,created_at,leads(*),products(*)'
    ).eq('company_id', str(company_id)).order('created_at', desc=True).execute()
    
    # Add lead_name and product_name to each call record
    calls = []
    for call in response.data:
        call['lead_name'] = call['leads']['name'] if call.get('leads') else None
        call['product_name'] = call['products']['product_name'] if call.get('products') else None
        calls.append(call)
    
    return calls 

async def create_email_campaign(company_id: UUID, name: str, description: Optional[str], email_subject: str, email_body: str):
    campaign_data = {
        'company_id': str(company_id),
        'name': name,
        'description': description,
        'email_subject': email_subject,
        'email_body': email_body
    }
    response = supabase.table('email_campaigns').insert(campaign_data).execute()
    return response.data[0]

async def get_email_campaigns_by_company(company_id: UUID):
    response = supabase.table('email_campaigns').select('*').eq('company_id', str(company_id)).execute()
    return response.data

async def get_email_campaign_by_id(campaign_id: UUID):
    response = supabase.table('email_campaigns').select('*').eq('id', str(campaign_id)).execute()
    return response.data[0] if response.data else None

async def create_email_log(campaign_id: UUID, lead_id: UUID, sent_at: datetime):
    log_data = {
        'campaign_id': str(campaign_id),
        'lead_id': str(lead_id),
        'sent_at': sent_at.isoformat()
    }
    response = supabase.table('email_logs').insert(log_data).execute()
    return response.data[0]

async def get_leads_for_campaign(campaign_id: UUID):
    # First get the campaign to get company_id
    campaign = await get_email_campaign_by_id(campaign_id)
    if not campaign:
        return []
    
    # Get only leads that have an email address (not null and not empty)
    response = supabase.table('leads')\
        .select('*')\
        .eq('company_id', campaign['company_id'])\
        .neq('email', None)\
        .neq('email', '')\
        .execute()
    
    return response.data

async def update_email_log_sentiment(email_log_id: UUID, reply_sentiment: str) -> Dict:
    """
    Update the reply_sentiment for an email log
    
    Args:
        email_log_id: UUID of the email log record
        reply_sentiment: The sentiment category (positive, neutral, negative)
        
    Returns:
        Dict containing the updated record
    """
    response = supabase.table('email_logs').update({
        'reply_sentiment': reply_sentiment
    }).eq('id', str(email_log_id)).execute()
    
    return response.data[0] if response.data else None 

async def create_email_log_detail(
    email_logs_id: UUID, 
    message_id: str, 
    email_subject: str, 
    email_body: str, 
    sender_type: str, 
    sent_at: Optional[datetime] = None,
    from_name: Optional[str] = None,
    from_email: Optional[str] = None,
    to_email: Optional[str] = None
):
    # Create base log detail data without sent_at
    log_detail_data = {
        'email_logs_id': str(email_logs_id),
        'message_id': message_id,
        'email_subject': email_subject,
        'email_body': email_body,
        'sender_type': sender_type,
        'from_name': from_name,
        'from_email': from_email,
        'to_email': to_email
    }
    
    # Only add sent_at if provided
    if sent_at:
        log_detail_data['sent_at'] = sent_at.isoformat()
    
    #logger.info(f"Inserting email_log_detail with data: {log_detail_data}")
    response = supabase.table('email_log_details').insert(log_detail_data).execute()
    return response.data[0]

async def get_email_conversation_history(email_logs_id: UUID):
    """
    Get all email messages for a given email_log_id ordered by creation time
    """
    response = supabase.table('email_log_details').select(
        'message_id,email_subject,email_body,sender_type,created_at'
    ).eq('email_logs_id', str(email_logs_id)).order('created_at', desc=False).execute()
    
    return response.data 

async def update_company_cronofy_tokens(company_id: UUID, access_token: str, refresh_token: str):
    response = supabase.table('companies').update({
        'cronofy_access_token': access_token,
        'cronofy_refresh_token': refresh_token
    }).eq('id', str(company_id)).execute()
    return response.data[0] if response.data else None 

async def update_company_cronofy_profile(
    company_id: UUID,
    provider: str,
    linked_email: str,
    default_calendar: str,
    default_calendar_name: str,
    access_token: str,
    refresh_token: str
):
    response = supabase.table('companies').update({
        'cronofy_provider': provider,
        'cronofy_linked_email': linked_email,
        'cronofy_default_calendar_id': default_calendar,
        'cronofy_default_calendar_name': default_calendar_name,
        'cronofy_access_token': access_token,
        'cronofy_refresh_token': refresh_token
    }).eq('id', str(company_id)).execute()
    return response.data[0] if response.data else None 

async def clear_company_cronofy_data(company_id: UUID):
    response = supabase.table('companies').update({
        'cronofy_provider': None,
        'cronofy_linked_email': None,
        'cronofy_default_calendar_id': None,
        'cronofy_default_calendar_name': None,
        'cronofy_access_token': None,
        'cronofy_refresh_token': None
    }).eq('id', str(company_id)).execute()
    return response.data[0] if response.data else None 

async def get_company_id_from_email_log(email_log_id: UUID) -> Optional[UUID]:
    """Get company_id from email_log through campaign and company relationship"""
    response = supabase.table('email_logs')\
        .select('campaign_id,email_campaigns(company_id)')\
        .eq('id', str(email_log_id))\
        .execute()
    
    if response.data and response.data[0].get('email_campaigns'):
        return UUID(response.data[0]['email_campaigns']['company_id'])
    return None 

async def update_product_details(product_id: UUID, product_name: str):
    product_data = {
        'product_name': product_name
    }
    response = supabase.table('products').update(product_data).eq('id', str(product_id)).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Product not found")
    return response.data[0] 

# Task management functions
async def create_upload_task(task_id: UUID, company_id: UUID, user_id: UUID, file_url: str):
    """Create a new upload task record"""
    data = {
        'id': str(task_id),
        'company_id': str(company_id),
        'user_id': str(user_id),
        'file_url': file_url,
        'status': 'pending',
        'created_at': datetime.now().isoformat()
    }
    response = supabase.table('upload_tasks').insert(data).execute()
    return response.data[0] if response.data else None

async def update_task_status(task_id: UUID, status: str, result: str = None):
    """Update task status and result"""
    data = {
        'status': status,
        'result': result,
        'updated_at': datetime.now().isoformat()
    }
    response = supabase.table('upload_tasks').update(data).eq('id', str(task_id)).execute()
    return response.data[0] if response.data else None

async def get_task_status(task_id: UUID):
    """Get task status and details"""
    response = supabase.table('upload_tasks')\
        .select('*')\
        .eq('id', str(task_id))\
        .execute()
    return response.data[0] if response.data else None 

async def update_company_account_credentials(company_id: UUID, account_email: str, account_password: str, account_type: str):
    """
    Update the account credentials for a company
    
    Args:
        company_id: UUID of the company
        account_email: Email address for the account
        account_password: Password for the account (will be encrypted)
        account_type: Type of the account (e.g., 'gmail')
        
    Returns:
        Dict containing the updated record
    """
    # Encrypt the password before storing
    encrypted_password = encrypt_password(account_password)
    
    # Get current company data to check last_email_processed_at
    company = supabase.table('companies').select('last_email_processed_at').eq('id', str(company_id)).execute()
    update_data = {
        'account_email': account_email,
        'account_password': encrypted_password,
        'account_type': account_type
    }
    
    # Only set last_email_processed_at if it's currently NULL
    if company.data and company.data[0].get('last_email_processed_at') is None:
        update_data['last_email_processed_at'] = datetime.now(timezone.utc).isoformat()
    
    response = supabase.table('companies').update(update_data).eq('id', str(company_id)).execute()
    
    return response.data[0] if response.data else None

async def get_companies_with_email_credentials():
    """Get all companies that have email credentials configured"""
    response = supabase.table('companies').select('*').not_.is_('account_email', 'null').not_.is_('account_password', 'null').execute()
    return response.data

async def update_last_processed_email_date(company_id: UUID, email_date: datetime):
    """Update the last processed email date for a company"""
    response = supabase.table('companies').update({
        'last_email_processed_at': email_date.isoformat()
    }).eq('id', str(company_id)).execute()
    return response.data[0] if response.data else None 

async def create_password_reset_token(user_id: UUID, token: str, expires_at: datetime):
    """Create a new password reset token for a user"""
    token_data = {
        'user_id': str(user_id),
        'token': token,
        'expires_at': expires_at.isoformat(),
        'used': False
    }
    response = supabase.table('password_reset_tokens').insert(token_data).execute()
    return response.data[0]

async def get_valid_reset_token(token: str):
    """Get a valid (not expired and not used) password reset token"""
    now = datetime.now(timezone.utc)
    response = supabase.table('password_reset_tokens')\
        .select('*')\
        .eq('token', token)\
        .eq('used', False)\
        .gte('expires_at', now.isoformat())\
        .execute()
    return response.data[0] if response.data else None

async def invalidate_reset_token(token: str):
    """Mark a password reset token as used"""
    response = supabase.table('password_reset_tokens')\
        .update({'used': True})\
        .eq('token', token)\
        .execute()
    return response.data[0] if response.data else None 

async def create_verification_token(user_id: UUID, token: str, expires_at: datetime):
    """Create a new email verification token for a user"""
    token_data = {
        'user_id': str(user_id),
        'token': token,
        'expires_at': expires_at.isoformat(),
        'used': False
    }
    response = supabase.table('verification_tokens').insert(token_data).execute()
    return response.data[0]

async def get_valid_verification_token(token: str):
    """Get a valid (not expired and not used) verification token"""
    now = datetime.now(timezone.utc)
    response = supabase.table('verification_tokens')\
        .select('*')\
        .eq('token', token)\
        .eq('used', False)\
        .gte('expires_at', now.isoformat())\
        .execute()
    return response.data[0] if response.data else None

async def mark_verification_token_used(token: str):
    """Mark a verification token as used"""
    response = supabase.table('verification_tokens')\
        .update({'used': True})\
        .eq('token', token)\
        .execute()
    return response.data[0] if response.data else None

async def mark_user_as_verified(user_id: UUID):
    """Mark a user as verified"""
    response = supabase.table('users')\
        .update({'verified': True})\
        .eq('id', str(user_id))\
        .execute()
    return response.data[0] if response.data else None 

async def get_user_by_id(user_id: UUID):
    """Get user by ID from the database"""
    response = supabase.table('users').select('*').eq('id', str(user_id)).execute()
    return response.data[0] if response.data else None 