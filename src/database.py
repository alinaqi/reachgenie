from supabase import create_client, Client
from src.config import get_settings
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from src.utils.encryption import encrypt_password
import logging
import secrets
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
    """
    Get all non-deleted companies for a user
    
    Args:
        user_id: UUID of the user
        
    Returns:
        List of companies where deleted = FALSE
    """
    response = supabase.table('companies').select('*').eq('user_id', str(user_id)).eq('deleted', False).execute()
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

async def create_call(lead_id: UUID, product_id: UUID, campaign_id: UUID, bland_call_id: str):
    call_data = {
        'lead_id': str(lead_id),
        'product_id': str(product_id),
        'campaign_id': str(campaign_id),
        'bland_call_id': bland_call_id
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

async def get_calls_by_company_id(company_id: UUID, campaign_id: Optional[UUID] = None):
    # Get calls with their related data using a join with campaigns
    query = supabase.table('calls').select(
        'id,lead_id,product_id,duration,sentiment,summary,bland_call_id,created_at,campaign_id,leads(*),campaigns!inner(*)'
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

async def create_campaign(company_id: UUID, name: str, description: Optional[str], product_id: UUID, type: str = 'email'):
    campaign_data = {
        'company_id': str(company_id),
        'name': name,
        'description': description,
        'product_id': str(product_id),
        'type': type
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

async def get_company_email_logs(company_id: UUID, campaign_id: Optional[UUID] = None):
    """
    Get email logs for a company, optionally filtered by campaign_id
    
    Args:
        company_id: UUID of the company
        campaign_id: Optional UUID of the campaign to filter by
        
    Returns:
        List of email logs with campaign and lead information
    """
    query = supabase.table('email_logs')\
        .select(
            'id, campaign_id, lead_id, sent_at, ' +
            'campaigns!inner(name, company_id), ' +  # Using inner join to ensure campaign exists
            'leads(name, email)'
        )\
        .eq('campaigns.company_id', str(company_id))  # Filter by company_id in the join
    
    if campaign_id:
        query = query.eq('campaign_id', str(campaign_id))
    
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
        response = supabase.table('companies').update({
            'voice_agent_settings': settings
        }).eq('id', str(company_id)).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating voice agent settings: {str(e)}")
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
    Update the has_replied field to True for an email log
    
    Args:
        email_log_id: UUID of the email log to update
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        response = supabase.table('email_logs')\
            .update({'has_replied': True})\
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