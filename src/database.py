from supabase import create_client, Client
from src.config import get_settings
from typing import Optional, List, Dict, Any, Union, Tuple
from uuid import UUID
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from src.utils.encryption import encrypt_password
import logging
import secrets
import uuid
import json
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

async def db_create_product(
    company_id: UUID, 
    product_name: str, 
    file_name: Optional[str] = None, 
    original_filename: Optional[str] = None, 
    description: Optional[str] = None,
    product_url: Optional[str] = None,
    enriched_information: Optional[Dict] = None
):
    product_data = {
        'company_id': str(company_id),
        'product_name': product_name,
        'file_name': file_name,
        'original_filename': original_filename,
        'description': description,
        'product_url': product_url,
        'enriched_information': enriched_information
    }
    response = supabase.table('products').insert(product_data).execute()
    return response.data[0]

async def get_products_by_company(company_id: UUID):
    response = supabase.table('products').select('*').eq('company_id', str(company_id)).eq('deleted', False).execute()
    return response.data

async def create_lead(company_id: UUID, lead_data: dict):
    try:
        lead_data['company_id'] = str(company_id)
        print("\nAttempting to insert lead with data:")
        print(lead_data)
        response = supabase.table('leads').insert(lead_data).execute()
        print("\nDatabase response:")
        print(response)
        return response.data[0]
    except Exception as e:
        print(f"\nError in create_lead: {str(e)}")
        raise e

async def get_leads_by_company(company_id: UUID):
    response = supabase.table('leads').select('*').eq('company_id', str(company_id)).execute()
    return response.data

async def create_call(lead_id: UUID, product_id: UUID, campaign_id: UUID, script: Optional[str] = None):
    call_data = {
        'lead_id': str(lead_id),
        'product_id': str(product_id),
        'campaign_id': str(campaign_id),
        'script': script
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

async def delete_lead(lead_id: UUID) -> bool:
    """
    Delete a lead from the database and all related records in the correct order:
    1. email_log_details
    2. email_logs
    3. lead
    
    Args:
        lead_id: UUID of the lead to delete
        
    Returns:
        bool: True if lead was deleted successfully, False otherwise
    """
    try:
        # First get all email logs for this lead
        email_logs = supabase.table('email_logs').select('id').eq('lead_id', str(lead_id)).execute()
        
        if email_logs.data:
            # Delete all email_log_details for these email logs
            for log in email_logs.data:
                supabase.table('email_log_details').delete().eq('email_logs_id', str(log['id'])).execute()
        
        # Now delete the email logs
        supabase.table('email_logs').delete().eq('lead_id', str(lead_id)).execute()
        
        # Finally delete the lead
        response = supabase.table('leads').delete().eq('id', str(lead_id)).execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error deleting lead {lead_id}: {str(e)}")
        return False

async def get_product_by_id(product_id: UUID):
    response = supabase.table('products').select('*').eq('id', str(product_id)).eq('deleted', False).execute()
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

async def update_call_webhook_data(bland_call_id: str, duration: str, sentiment: str, summary: str, transcripts: list[dict], recording_url: Optional[str] = None):
    """
    Update call record with webhook data from Bland AI
    
    Args:
        bland_call_id: The Bland AI call ID
        duration: Call duration in seconds
        sentiment: Call sentiment analysis result
        summary: Call summary
        
    Returns:
        Updated call record or None if update fails
    """
    try:
        call_data = {
            'duration': int(float(duration)),
            'sentiment': sentiment,
            'summary': summary,
            'transcripts': transcripts,
            'recording_url': recording_url
        }
        response = supabase.table('calls').update(call_data).eq('bland_call_id', bland_call_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating call webhook data for bland_call_id {bland_call_id}: {str(e)}")
        return None

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

async def get_calls_by_company_id(company_id: UUID, campaign_id: Optional[UUID] = None):
    # Get calls with their related data using a join with campaigns
    query = supabase.table('calls').select(
        'id,lead_id,product_id,duration,sentiment,summary,bland_call_id,has_meeting_booked,transcripts,recording_url,created_at,campaign_id,leads(*),campaigns!inner(*)'
    ).eq('campaigns.company_id', str(company_id))
    
    # Add campaign filter if provided
    if campaign_id:
        query = query.eq('campaign_id', str(campaign_id))
    
    # Execute query with ordering
    response = query.order('created_at', desc=True).execute()
    
    # Add lead_name, lead_phone_number and campaign_name to each call record
    calls = []
    for call in response.data:
        call['lead_name'] = call['leads']['name'] if call.get('leads') else None
        call['lead_phone_number'] = call['leads']['phone_number'] if call.get('leads') else None
        call['campaign_name'] = call['campaigns']['name'] if call.get('campaigns') else None
        calls.append(call)
    
    return calls

async def create_campaign(company_id: UUID, name: str, description: Optional[str], product_id: UUID, type: str = 'email', template: Optional[str] = None):
    campaign_data = {
        'company_id': str(company_id),
        'name': name,
        'description': description,
        'product_id': str(product_id),
        'type': type,
        'template': template
    }
    response = supabase.table('campaigns').insert(campaign_data).execute()
    return response.data[0]

async def get_campaigns_by_company(company_id: UUID, campaign_type: Optional[str] = None):
    """
    Get campaigns for a company, optionally filtered by type
    
    Args:
        company_id: UUID of the company
        campaign_type: Optional type filter ('email', 'call', or None for all)
        
    Returns:
        List of campaigns
    """
    query = supabase.table('campaigns').select('*').eq('company_id', str(company_id))
    
    if campaign_type and campaign_type != 'all':
        query = query.eq('type', campaign_type)
    
    response = query.execute()
    return response.data

async def get_campaign_by_id(campaign_id: UUID):
    response = supabase.table('campaigns').select('*').eq('id', str(campaign_id)).execute()
    return response.data[0] if response.data else None

async def create_email_log(campaign_id: UUID, lead_id: UUID, sent_at: datetime):
    log_data = {
        'campaign_id': str(campaign_id),
        'lead_id': str(lead_id),
        'sent_at': sent_at.isoformat()
    }
    response = supabase.table('email_logs').insert(log_data).execute()
    return response.data[0]

async def get_leads_with_email(campaign_id: UUID):
    # First get the campaign to get company_id
    campaign = await get_campaign_by_id(campaign_id)
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

async def get_leads_with_phone(company_id: UUID):
    # Get only those leads who have phone number (not null and not empty)
    response = supabase.table('leads')\
        .select('*')\
        .eq('company_id', company_id)\
        .neq('phone_number', None)\
        .neq('phone_number', '')\
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
    to_email: Optional[str] = None,
    reminder_type: Optional[str] = None
):
    """
    Create a new email log detail record
    
    Args:
        email_logs_id: UUID of the parent email log
        message_id: Message ID from the email
        email_subject: Subject of the email
        email_body: Body content of the email
        sender_type: Type of sender ('user' or 'assistant')
        sent_at: Optional timestamp when the email was sent
        from_name: Optional sender name
        from_email: Optional sender email
        to_email: Optional recipient email
        reminder_type: Optional type of reminder (e.g., 'r1' for first reminder)
    
    Returns:
        Dict containing the created record
    """
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
        
    # Only add reminder_type if provided
    if reminder_type:
        log_detail_data['reminder_type'] = reminder_type
    
    #logger.info(f"Inserting email_log_detail with data: {log_detail_data}")
    response = supabase.table('email_log_details').insert(log_detail_data).execute()
    return response.data[0]

async def get_email_conversation_history(email_logs_id: UUID):
    """
    Get all email messages for a given email_log_id ordered by creation time
    """
    response = supabase.table('email_log_details').select(
        'message_id,email_subject,email_body,sender_type,sent_at,created_at,from_name,from_email,to_email'
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
        .select('campaign_id,campaigns(company_id)')\
        .eq('id', str(email_log_id))\
        .execute()
    
    if response.data and response.data[0].get('campaigns'):
        return UUID(response.data[0]['campaigns']['company_id'])
    return None 

async def update_product_details(product_id: UUID, product_name: str, description: Optional[str] = None, product_url: Optional[str] = None):
    """
    Update product details including name, description, and URL.
    
    Args:
        product_id: UUID of the product to update
        product_name: New name for the product
        description: Optional new description for the product
        product_url: Optional new URL for the product
        
    Returns:
        Updated product record
    """
    product_data = {
        'product_name': product_name
    }
    
    # Add optional fields if provided
    if description is not None:
        product_data['description'] = description
    
    if product_url is not None:
        product_data['product_url'] = product_url
        
    response = supabase.table('products').update(product_data).eq('id', str(product_id)).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Product not found")
    return response.data[0]

async def soft_delete_product(product_id: UUID) -> bool:
    """
    Soft delete a product by setting deleted = TRUE
    
    Args:
        product_id: UUID of the product to delete
        
    Returns:
        bool: True if product was marked as deleted successfully, False otherwise
    """
    try:
        response = supabase.table('products').update({'deleted': True}).eq('id', str(product_id)).execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error soft deleting product {product_id}: {str(e)}")
        return False

async def update_product_icps(product_id: UUID, ideal_icps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Update the ideal customer profiles for a product.
    
    Args:
        product_id: UUID of the product to update
        ideal_icps: List of ideal customer profile dictionaries
        
    Returns:
        Updated product record
        
    Raises:
        HTTPException: If product not found or update fails
    """
    try:
        response = supabase.table('products').update({'ideal_icps': ideal_icps}).eq('id', str(product_id)).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Product not found")
        return response.data[0]
    except Exception as e:
        logger.error(f"Error updating product ICPs {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update product ICPs: {str(e)}")

async def get_product_icps(product_id: UUID) -> List[Dict[str, Any]]:
    """
    Get the ideal customer profiles for a product.
    
    Args:
        product_id: UUID of the product to get ICPs for
        
    Returns:
        List of ideal customer profile dictionaries
        
    Raises:
        HTTPException: If product not found
    """
    response = supabase.table('products').select('ideal_icps').eq('id', str(product_id)).eq('deleted', False).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Return the ideal_icps field, or an empty list if it's None
    return response.data[0].get('ideal_icps') or []

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

    update_data = {
        'account_email': account_email,
        'account_password': encrypted_password,
        'account_type': account_type
    }
    
    response = supabase.table('companies').update(update_data).eq('id', str(company_id)).execute()
    
    return response.data[0] if response.data else None

async def get_companies_with_email_credentials():
    """Get all companies that have email credentials configured and are not deleted"""
    response = supabase.table('companies')\
        .select('*')\
        .not_.is_('account_email', 'null')\
        .not_.is_('account_password', 'null')\
        .eq('deleted', False)\
        .execute()
    return response.data

async def update_last_processed_uid(company_id: UUID, uid: str):
    """Update the last processed UID for a company"""
    response = supabase.table('companies').update({
        'last_processed_uid': uid
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

async def get_company_email_logs(company_id: UUID, campaign_id: Optional[UUID] = None, lead_id: Optional[UUID] = None):
    """
    Get email logs for a company, optionally filtered by campaign_id and/or lead_id
    
    Args:
        company_id: UUID of the company
        campaign_id: Optional UUID of the campaign to filter by
        lead_id: Optional UUID of the lead to filter by
        
    Returns:
        List of email logs with campaign and lead information
    """
    query = supabase.table('email_logs')\
        .select(
            'id, campaign_id, lead_id, sent_at, has_opened, has_replied, has_meeting_booked, ' +
            'campaigns!inner(name, company_id), ' +  # Using inner join to ensure campaign exists
            'leads(name, email)'
        )\
        .eq('campaigns.company_id', str(company_id))  # Filter by company_id in the join
    
    if campaign_id:
        query = query.eq('campaign_id', str(campaign_id))
    
    if lead_id:
        query = query.eq('lead_id', str(lead_id))
    
    response = query.execute()
    return response.data

async def soft_delete_company(company_id: UUID) -> bool:
    """
    Soft delete a company by setting deleted = TRUE
    
    Args:
        company_id: UUID of the company to delete
        
    Returns:
        bool: True if company was marked as deleted successfully, False otherwise
    """
    try:
        response = supabase.table('companies').update({'deleted': True}).eq('id', str(company_id)).execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error soft deleting company {company_id}: {str(e)}")
        return False 

async def update_company_voice_agent_settings(company_id: UUID, settings: dict) -> Optional[dict]:
    """
    Update voice agent settings for a company
    
    Args:
        company_id: UUID of the company
        settings: Dictionary containing voice agent settings
        
    Returns:
        Updated company record or None if company not found
    """
    try:
        logger.info(f"Updating voice agent settings for company {company_id}")
        logger.info(f"Settings to update: {settings}")
        
        # First, get the current settings to compare
        current = supabase.table('companies').select('voice_agent_settings').eq('id', str(company_id)).execute()
        if current.data:
            logger.info(f"Current voice_agent_settings: {current.data[0].get('voice_agent_settings')}")
        
        response = supabase.table('companies').update({
            'voice_agent_settings': settings
        }).eq('id', str(company_id)).execute()
        
        if response.data:
            logger.info(f"Updated voice_agent_settings: {response.data[0].get('voice_agent_settings')}")
            return response.data[0]
        else:
            logger.error(f"No data returned from update operation")
            return None
    except Exception as e:
        logger.error(f"Error updating voice agent settings: {str(e)}")
        logger.exception("Full exception details:")
        return None

async def get_email_logs_reminder(reminder_type: Optional[str] = None):
    """
    Fetch all email logs that need to be processed for reminders.
    Joins with campaigns and companies to ensure we only get active records.
    Excludes deleted companies.
    Only fetches records where:
    - For first reminder (reminder_type is None):
      - No reminder has been sent yet (last_reminder_sent is NULL)
      - More than 2 days have passed since the initial email was sent
    - For subsequent reminders:
      - last_reminder_sent equals the specified reminder_type
      - More than 2 days have passed since the last reminder was sent
    
    Args:
        reminder_type: Optional type of reminder to filter by (e.g., 'r1' for first reminder)
    
    Returns:
        List of dictionaries containing email log data with campaign and company information
    """
    try:
        # Calculate the date threshold (2 days ago from now)
        two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        
        # Build the base query
        query = supabase.table('email_logs')\
            .select(
                'id, sent_at, has_replied, last_reminder_sent, last_reminder_sent_at, lead_id, ' +
                'campaigns!inner(id, name, company_id, companies!inner(id, name, account_email, account_password, account_type)), ' +
                'leads!inner(email)'
            )\
            .eq('has_replied', False)\
            .eq('campaigns.companies.deleted', False)
            
        # Add reminder type filter
        if reminder_type is None:
            query = query\
                .is_('last_reminder_sent', 'null')\
                .lt('sent_at', two_days_ago)  # Only check sent_at for first reminder
        else:
            query = query\
                .eq('last_reminder_sent', reminder_type)\
                .lt('last_reminder_sent_at', two_days_ago)  # Check last reminder timing
            
        # Execute query with ordering
        response = query.order('sent_at', desc=False).execute()
        
        # Flatten the nested structure to match the expected format
        flattened_data = []
        for record in response.data:
            campaign = record['campaigns']
            company = campaign['companies']
            lead = record['leads']
            
            flattened_record = {
                'email_log_id': record['id'],
                'sent_at': record['sent_at'],
                'has_replied': record['has_replied'],
                'last_reminder_sent': record['last_reminder_sent'],
                'last_reminder_sent_at': record['last_reminder_sent_at'],
                'lead_id': record['lead_id'],
                'lead_email': lead['email'],
                'campaign_id': campaign['id'],
                'campaign_name': campaign['name'],
                'company_id': company['id'],
                'company_name': company['name'],
                'account_email': company['account_email'],
                'account_password': company['account_password'],
                'account_type': company['account_type']
            }
            flattened_data.append(flattened_record)
            
        return flattened_data
    except Exception as e:
        logger.error(f"Error fetching email logs for reminder: {str(e)}")
        return []

async def get_first_email_detail(email_logs_id: UUID):
    """
    Get the first (original) email detail record for a given email_log_id
    
    Args:
        email_logs_id: UUID of the email log
        
    Returns:
        Dict containing the first email detail record or None if not found
    """
    try:
        response = supabase.table('email_log_details')\
            .select('message_id, email_subject, email_body, sent_at')\
            .eq('email_logs_id', str(email_logs_id))\
            .order('sent_at', desc=False)\
            .limit(1)\
            .execute()
            
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching first email detail for log {email_logs_id}: {str(e)}")
        return None 

async def update_reminder_sent_status(email_log_id: UUID, reminder_type: str, last_reminder_sent_at: datetime) -> bool:
    """
    Update the last_reminder_sent field and timestamp for an email log
    
    Args:
        email_log_id: UUID of the email log to update
        reminder_type: Type of reminder sent (e.g., 'r1' for first reminder)
        last_reminder_sent_at: Timestamp when the reminder was sent
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        response = supabase.table('email_logs')\
            .update({
                'last_reminder_sent': reminder_type,
                'last_reminder_sent_at': last_reminder_sent_at.isoformat()
            })\
            .eq('id', str(email_log_id))\
            .execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error updating reminder status for log {email_log_id}: {str(e)}")
        return False 

async def update_email_log_has_replied(email_log_id: UUID) -> bool:
    """
    Update the has_replied field to True for an email log and also set has_opened to True
    since a reply implies the email was opened.
    
    Args:
        email_log_id: UUID of the email log to update
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        response = supabase.table('email_logs')\
            .update({
                'has_replied': True,
                'has_opened': True
            })\
            .eq('id', str(email_log_id))\
            .execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error updating has_replied status for log {email_log_id}: {str(e)}")
        return False 

async def create_unverified_user(email: str, name: Optional[str] = None):
    """Create a new unverified user without password"""
    user_data = {
        'email': email,
        'name': name,
        'password_hash': 'PENDING_INVITE',  # Temporary value that can't be used to log in
        'verified': False
    }
    response = supabase.table('users').insert(user_data).execute()
    return response.data[0] if response.data else None

async def create_user_company_profile(user_id: UUID, company_id: UUID, role: str):
    """Create a user-company profile with specified role"""
    profile_data = {
        'user_id': str(user_id),
        'company_id': str(company_id),
        'role': role
    }
    response = supabase.table('user_company_profiles').insert(profile_data).execute()
    return response.data[0] if response.data else None

async def get_user_company_profile(user_id: UUID, company_id: UUID):
    """Get user-company profile if exists"""
    response = supabase.table('user_company_profiles')\
        .select('*')\
        .eq('user_id', str(user_id))\
        .eq('company_id', str(company_id))\
        .execute()
    return response.data[0] if response.data else None

async def create_invite_token(user_id: UUID):
    """Create a new invite token for a user"""
    token_data = {
        'user_id': str(user_id),
        'token': secrets.token_urlsafe(32),
        'used': False
    }
    response = supabase.table('invite_tokens').insert(token_data).execute()
    return response.data[0] if response.data else None 

async def get_valid_invite_token(token: str):
    """Get a valid (not used) invite token"""
    response = supabase.table('invite_tokens')\
        .select('*')\
        .eq('token', token)\
        .eq('used', False)\
        .execute()
    return response.data[0] if response.data else None

async def mark_invite_token_used(token: str):
    """Mark an invite token as used"""
    response = supabase.table('invite_tokens')\
        .update({'used': True})\
        .eq('token', token)\
        .execute()
    return response.data[0] if response.data else None 

async def get_companies_by_user_id(user_id: UUID, show_stats: bool = False):
    """
    Get all companies that a user has access to through user_company_profiles,
    including their products (with campaign counts and total calls) and total leads count if show_stats is True
    
    Args:
        user_id: UUID of the user
        show_stats: bool, if True includes products (with campaign and call counts) and total leads count in the response
        
    Returns:
        List of companies the user has access to, optionally including array of products (with campaign and call counts) and total leads
    """
    # Build the select statement based on show_stats
    select_fields = 'role, user_id, companies!inner(id, name, address, industry, website, deleted, created_at'
    if show_stats:
        select_fields += ', products(id, product_name, deleted)'  # Include deleted column for filtering
    select_fields += ')'

    response = supabase.table('user_company_profiles')\
        .select(select_fields)\
        .eq('user_id', str(user_id))\
        .eq('companies.deleted', False)\
        .execute()

    # Transform the response to include products and leads count in the desired format
    companies = []
    for profile in response.data:
        company = profile['companies']
        
        # Create base company data
        company_data = {
            'id': company['id'],
            'name': company['name'],
            'address': company['address'],
            'industry': company['industry'],
            'website': company['website'],
            'created_at': company['created_at'],
            'role': profile['role'],
            'user_id': profile['user_id']
        }
        
        # Add products and total leads only if show_stats is True
        if show_stats:
            # Add products if they exist
            if 'products' in company:
                products = []
                for product in company['products']:
                    # Skip deleted products
                    if product.get('deleted', False):
                        continue
                        
                    # Get campaign count for this product
                    campaigns_response = supabase.table('campaigns')\
                        .select('id', count='exact')\
                        .eq('product_id', product['id'])\
                        .execute()
                    
                    # Get campaign IDs in a separate query for calls count
                    campaign_ids_response = supabase.table('campaigns')\
                        .select('id')\
                        .eq('product_id', product['id'])\
                        .execute()
                    campaign_ids = [campaign['id'] for campaign in campaign_ids_response.data]

                    # Call the stored postgres function using Supabase RPC
                    response = supabase.rpc("count_unique_leads_by_campaign", {"campaign_ids": campaign_ids}).execute()

                    # Extract and print the result
                    if response.data:
                        unique_leads_contacted = response.data
                    else:
                        unique_leads_contacted = 0

                    # Initialize all statistics variables
                    total_calls = 0
                    total_positive_calls = 0
                    total_sent_emails = 0
                    total_opened_emails = 0
                    total_replied_emails = 0
                    total_meetings_booked_in_calls = 0
                    total_meetings_booked_in_emails = 0

                    if campaign_ids:  # Only query if there are campaigns
                        # Fetch all calls for this product
                        calls_response = supabase.table('calls')\
                            .select('id', count='exact')\
                            .in_('campaign_id', campaign_ids)\
                            .execute()
                        total_calls = calls_response.count

                        # Fetch all positive calls for this product
                        positive_calls_response = supabase.table('calls')\
                            .select('id', count='exact')\
                            .in_('campaign_id', campaign_ids)\
                            .eq('sentiment', 'positive')\
                            .execute()
                        total_positive_calls = positive_calls_response.count
                    
                        # Fetch all sent emails for this product
                        sent_emails_response = supabase.table('email_logs')\
                            .select('id', count='exact')\
                            .in_('campaign_id', campaign_ids)\
                            .execute()
                        total_sent_emails = sent_emails_response.count

                        # Fetch all opened emails for this product
                        opened_emails_response = supabase.table('email_logs')\
                            .select('id', count='exact')\
                            .in_('campaign_id', campaign_ids)\
                            .eq('has_opened', True)\
                            .execute()
                        total_opened_emails = opened_emails_response.count

                        # Fetch all replied emails for this product
                        replied_emails_response = supabase.table('email_logs')\
                            .select('id', count='exact')\
                            .in_('campaign_id', campaign_ids)\
                            .eq('has_replied', True)\
                            .execute()
                        total_replied_emails = replied_emails_response.count

                        # Fetch all meetings booked in calls for this product
                        meetings_booked_calls_response = supabase.table('calls')\
                            .select('id', count='exact')\
                            .in_('campaign_id', campaign_ids)\
                            .eq('has_meeting_booked', True)\
                            .execute()
                        total_meetings_booked_in_calls = meetings_booked_calls_response.count

                        # Fetch all meetings booked in emails for this product
                        meetings_booked_emails_response = supabase.table('email_logs')\
                            .select('id', count='exact')\
                            .in_('campaign_id', campaign_ids)\
                            .eq('has_meeting_booked', True)\
                            .execute()
                        total_meetings_booked_in_emails = meetings_booked_emails_response.count
                    
                    products.append({
                        'id': product['id'],
                        'name': product['product_name'],
                        'total_campaigns': campaigns_response.count,
                        'total_calls': total_calls,
                        'total_positive_calls': total_positive_calls,
                        'total_sent_emails': total_sent_emails,
                        'total_opened_emails': total_opened_emails,
                        'total_replied_emails': total_replied_emails,
                        'total_meetings_booked_in_calls': total_meetings_booked_in_calls,
                        'total_meetings_booked_in_emails': total_meetings_booked_in_emails,
                        'unique_leads_contacted': unique_leads_contacted
                    })
                company_data['products'] = products
            else:
                company_data['products'] = []
            
            # Get total leads count using a separate count query
            leads_count_response = supabase.table('leads')\
                .select('id', count='exact')\
                .eq('company_id', company['id'])\
                .execute()
            company_data['total_leads'] = leads_count_response.count

        companies.append(company_data)
    
    return companies

async def get_company_users(company_id: UUID) -> List[dict]:
    """
    Get all users associated with a company through user_company_profiles.
    
    Args:
        company_id: UUID of the company
        
    Returns:
        List of dicts containing user details (name, email, role, user_company_profile_id)
    """
    response = supabase.table('user_company_profiles')\
        .select(
            'id,role,users!inner(name,email)'  # Added id field from user_company_profiles
        )\
        .eq('company_id', str(company_id))\
        .execute()
    
    # Transform the response to match the expected format
    users = []
    for record in response.data:
        user = record['users']
        users.append({
            'name': user['name'],
            'email': user['email'],
            'role': record['role'],
            'user_company_profile_id': record['id']  # Added user_company_profile_id
        })
    
    return users 

async def delete_user_company_profile(profile_id: UUID) -> bool:
    """
    Delete a user-company profile by its ID
    
    Args:
        profile_id: UUID of the user-company profile to delete
        
    Returns:
        bool: True if profile was deleted successfully, False otherwise
    """
    try:
        response = supabase.table('user_company_profiles').delete().eq('id', str(profile_id)).execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error deleting user company profile {profile_id}: {str(e)}")
        return False 

async def get_user_company_profile_by_id(profile_id: UUID):
    """Get user-company profile by its ID"""
    response = supabase.table('user_company_profiles')\
        .select('*')\
        .eq('id', str(profile_id))\
        .execute()
    return response.data[0] if response.data else None 

async def get_user_company_roles(user_id: UUID) -> List[dict]:
    """
    Get all company roles for a user
    
    Args:
        user_id: UUID of the user
        
    Returns:
        List of dicts containing company_id and role
    """
    response = supabase.table('user_company_profiles')\
        .select('company_id,role')\
        .eq('user_id', str(user_id))\
        .execute()
    
    return [{"company_id": record["company_id"], "role": record["role"]} for record in response.data] 

async def update_email_log_has_opened(email_log_id: UUID) -> bool:
    """
    Update the has_opened status of an email log to True.
    
    Args:
        email_log_id: UUID of the email log to update
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        response = supabase.table('email_logs').update({
            'has_opened': True
        }).eq('id', str(email_log_id)).execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error updating email_log has_opened status for {email_log_id}: {str(e)}")
        return False 

async def get_incomplete_calls() -> List[Dict]:
    """
    Fetch calls that have bland_call_id but missing duration, sentiment, or summary
    """
    try:
        response = supabase.table('calls') \
            .select('id, bland_call_id') \
            .not_.is_('bland_call_id', 'null') \
            .is_('duration', 'null') \
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error fetching incomplete calls: {str(e)}")
        return []

async def update_email_log_has_booked(email_log_id: UUID) -> Dict:
    """
    Update the has_booked status for an email log
    
    Args:
        email_log_id: UUID of the email log record
        
    Returns:
        Dict containing the updated record
    """
    response = supabase.table('email_logs').update({
        'has_meeting_booked': True
    }).eq('id', str(email_log_id)).execute()
    
    return response.data[0] if response.data else None

async def update_call_log_has_booked(call_log_id: UUID) -> Dict:
    """
    Update the has_booked status for a call log
    
    Args:
        call_log_id: UUID of the call log record
        
    Returns:
        Dict containing the updated record
    """
    response = supabase.table('calls').update({
        'has_meeting_booked': True
    }).eq('id', str(call_log_id)).execute()
    
    return response.data[0] if response.data else None

async def get_campaign_from_email_log(email_log_id: UUID):
    """
    Get campaign details including template from an email log ID
    
    Args:
        email_log_id: UUID of the email log
        
    Returns:
        Campaign details including template if found, None otherwise
    """
    response = supabase.table('email_logs')\
        .select('campaign_id, campaigns(*)')\
        .eq('id', str(email_log_id))\
        .execute()
    
    if response.data and response.data[0].get('campaigns'):
        return response.data[0]['campaigns']
    return None

async def get_lead_by_email(email: str):
    """
    Get a lead by email address
    """
    response = supabase.table('leads').select('*').eq('email', email).execute()
    return response.data[0] if response.data else None

async def get_lead_by_phone(phone: str):
    """
    Get a lead by phone number, checking all phone number fields
    """
    fields = ['phone_number', 'mobile', 'direct_phone', 'office_phone']
    
    for field in fields:
        response = supabase.table('leads').select('*').eq(field, phone).execute()
        if response.data:
            return response.data[0]
    
    return None

async def get_lead_communication_history(lead_id: UUID):
    """
    Get complete communication history for a lead including emails and calls
    """
    # Get email logs with campaign info
    email_logs = supabase.table('email_logs').select(
        'id, campaign_id, sent_at, has_opened, has_replied, has_meeting_booked, ' +
        'campaigns!inner(name, products(product_name))'
    ).eq('lead_id', str(lead_id)).execute()

    # Get email details for each log
    email_history = []
    for log in email_logs.data:
        details = supabase.table('email_log_details').select(
            'message_id, email_subject, email_body, sender_type, sent_at, created_at, from_name, from_email, to_email'
        ).eq('email_logs_id', str(log['id'])).order('created_at', desc=False).execute()

        email_history.append({
            'id': log['id'],
            'campaign_id': log['campaign_id'],
            'campaign_name': log['campaigns']['name'],
            'product_name': log['campaigns']['products']['product_name'] if log['campaigns'].get('products') else None,
            'sent_at': log['sent_at'],
            'has_opened': log['has_opened'],
            'has_replied': log['has_replied'],
            'has_meeting_booked': log['has_meeting_booked'],
            'messages': details.data
        })

    # Get call logs with campaign info
    calls = supabase.table('calls').select(
        'id, campaign_id, duration, sentiment, summary, bland_call_id, has_meeting_booked, transcripts, created_at, ' +
        'campaigns!inner(name, products(product_name))'
    ).eq('lead_id', str(lead_id)).execute()

    call_history = []
    for call in calls.data:
        call_history.append({
            'id': call['id'],
            'campaign_id': call['campaign_id'],
            'campaign_name': call['campaigns']['name'],
            'product_name': call['campaigns']['products']['product_name'] if call['campaigns'].get('products') else None,
            'duration': call['duration'],
            'sentiment': call['sentiment'],
            'summary': call['summary'],
            'bland_call_id': call['bland_call_id'],
            'has_meeting_booked': call['has_meeting_booked'],
            'transcripts': call['transcripts'],
            'created_at': call['created_at']
        })

    return {
        'email_history': email_history,
        'call_history': call_history
    }