import os
import json
from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Tuple
import uuid
import logging
import math
import csv
import io

# Set up logger
logger = logging.getLogger(__name__)

from supabase import create_client, Client
from src.config import get_settings
from fastapi import HTTPException
from src.utils.encryption import encrypt_password
import secrets
import json
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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

async def get_leads_by_company(company_id: UUID, page_number: int = 1, limit: int = 20, search_term: Optional[str] = None):
    # Build base query
    base_query = supabase.table('leads').select('*', count='exact').eq('company_id', str(company_id))
    
    # Add search filter if search_term is provided
    if search_term:
        pattern = f"%{search_term}%"
        base_query = base_query.or_(
            f"name.ilike.{pattern},"
            f"email.ilike.{pattern},"
            f"company.ilike.{pattern},"
            f"job_title.ilike.{pattern}"
        )
    
    # Get total count with search filter
    count_response = base_query.execute()
    total = count_response.count if count_response.count is not None else 0

    # Calculate offset from page_number
    offset = (page_number - 1) * limit

    # Get paginated data with the same filters
    response = base_query.range(offset, offset + limit - 1).execute()
    
    return {
        'items': response.data,
        'total': total,
        'page': page_number,
        'page_size': limit,
        'total_pages': (total + limit - 1) // limit if total > 0 else 1
    }

async def create_call(lead_id: UUID, product_id: UUID, campaign_id: UUID, script: Optional[str] = None, campaign_run_id: Optional[UUID] = None):
    """
    Create a call record in the database
    """
    try:
        # Prepare call data
        call_data = {
            'lead_id': str(lead_id),
            'product_id': str(product_id),
            'campaign_id': str(campaign_id),
            'script': script
        }
        
        # Only add campaign_run_id if it exists
        if campaign_run_id is not None:
            call_data['campaign_run_id'] = str(campaign_run_id)
        
        # Insert the record
        response = supabase.table('calls').insert(call_data).execute()
        return response.data[0]
    except Exception as e:
        logger.error(f"Error creating call: {str(e)}")
        raise

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
    """
    Update call record with Bland call ID
    
    Args:
        call_id: UUID of the call record
        bland_call_id: Bland AI call ID
    
    Returns:
        Updated call record or None if update fails
    """
    try:
        # Validate inputs
        if not call_id:
            logger.error("Cannot update call details: call_id is None or empty")
            return None
            
        if not bland_call_id or bland_call_id == "None":
            logger.error(f"Cannot update call details: bland_call_id is None or empty")
            return None
            
        logger.info(f"Updating call {call_id} with bland_call_id {bland_call_id}")
        
        call_data = {
            'bland_call_id': bland_call_id
        }
        
        # Log the request data
        logger.info(f"Supabase update request: table('calls').update({call_data}).eq('id', {str(call_id)})")
        
        response = supabase.table('calls').update(call_data).eq('id', str(call_id)).execute()
        
        if not response.data:
            logger.warning(f"No data returned from update operation for call_id {call_id}")
            return None
            
        logger.info(f"Successfully updated call_id {call_id} with bland_call_id {bland_call_id}")
        return response.data[0]
        
    except Exception as e:
        logger.error(f"Error updating call_id {call_id} with bland_call_id {bland_call_id}: {str(e)}")
        logger.exception("Full exception traceback:")
        return None

async def update_call_failure_reason(call_id: UUID, failure_reason: str):
    """
    Update the failure reason for a call
    
    Args:
        call_id: UUID of the call to update
        failure_reason: The reason why the call failed
        
    Returns:
        Updated call record or None if update fails
    """
    try:
        response = supabase.table('calls').update({
            'failure_reason': failure_reason
        }).eq('id', str(call_id)).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating call failure reason for call {call_id}: {str(e)}")
        return None

async def get_company_by_id(company_id: UUID):
    response = supabase.table('companies').select('*').eq('id', str(company_id)).execute()
    return response.data[0] if response.data else None

async def update_call_webhook_data(bland_call_id: str, duration: str, sentiment: str, summary: str, transcripts: list[dict], recording_url: Optional[str] = None, reminder_eligible: bool = False):
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
            'recording_url': recording_url,
            'is_reminder_eligible': reminder_eligible
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

async def get_calls_by_company_id(company_id: UUID, campaign_id: Optional[UUID] = None, campaign_run_id: Optional[UUID] = None, lead_id: Optional[UUID] = None):
    # Get calls with their related data using a join with campaigns
    query = supabase.table('calls').select(
        'id,lead_id,product_id,duration,sentiment,summary,bland_call_id,has_meeting_booked,transcripts,recording_url,failure_reason,created_at,campaign_id,leads(*),campaigns!inner(*)'
    ).eq('campaigns.company_id', str(company_id))
    
    # Add campaign filter if provided
    if campaign_id:
        query = query.eq('campaign_id', str(campaign_id))
    
    # Add campaign run filter if provided
    if campaign_run_id:
        query = query.eq('campaign_run_id', str(campaign_run_id))
    
    # Add lead filter if provided
    if lead_id:
        query = query.eq('lead_id', str(lead_id))
    
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

async def create_campaign(company_id: UUID, name: str, description: Optional[str], product_id: UUID, type: str = 'email', template: Optional[str] = None, number_of_reminders: Optional[int] = 0, days_between_reminders: Optional[int] = 0, phone_number_of_reminders: Optional[int] = 0, phone_days_between_reminders: Optional[int] = 0, auto_reply_enabled: Optional[bool] = False, trigger_call_on: Optional[str] = None):
    campaign_data = {
        'company_id': str(company_id),
        'name': name,
        'description': description,
        'product_id': str(product_id),
        'type': type,
        'template': template,
        'number_of_reminders': number_of_reminders,
        'days_between_reminders': days_between_reminders,
        'phone_number_of_reminders': phone_number_of_reminders,
        'phone_days_between_reminders': phone_days_between_reminders,
        'auto_reply_enabled': auto_reply_enabled,
        'trigger_call_on': trigger_call_on
    }
    response = supabase.table('campaigns').insert(campaign_data).execute()
    return response.data[0]

async def get_campaigns_by_company(company_id: UUID, campaign_types: Optional[List[str]] = None):
    """
    Get campaigns for a company, optionally filtered by multiple types
    
    Args:
        company_id: UUID of the company
        campaign_types: Optional list of types to filter (['email', 'call'], etc.)
        
    Returns:
        List of campaigns
    """
    query = supabase.table('campaigns').select('*').eq('company_id', str(company_id))
    
    if campaign_types:
        query = query.in_('type', campaign_types) 
    
    response = query.execute()
    return response.data

async def get_campaign_by_id(campaign_id: UUID):
    response = supabase.table('campaigns').select('*').eq('id', str(campaign_id)).execute()
    return response.data[0] if response.data else None

async def create_email_log(campaign_id: UUID, lead_id: UUID, sent_at: datetime, campaign_run_id: UUID):
    log_data = {
        'campaign_id': str(campaign_id),
        'lead_id': str(lead_id),
        'sent_at': sent_at.isoformat(),
        'campaign_run_id': str(campaign_run_id)
    }
    response = supabase.table('email_logs').insert(log_data).execute()
    return response.data[0]

async def get_leads_with_email(campaign_id: UUID, count: bool = False, page: int = 1, limit: int = 50):
    """
    Get leads with email addresses for a campaign with pagination support
    
    Args:
        campaign_id: UUID of the campaign
        count: If True, return only the count of leads
        page: Page number (1-indexed)
        limit: Number of leads per page
        
    Returns:
        If count=True: Total number of leads
        If count=False: Dict containing paginated leads data and metadata
    """
    # First get the campaign to get company_id
    campaign = await get_campaign_by_id(campaign_id)
    if not campaign:
        return 0 if count else {'items': [], 'total': 0, 'page': page, 'page_size': limit, 'total_pages': 0}
    
    def apply_filters(query):
        return query\
            .eq('company_id', campaign['company_id'])\
            .neq('email', None)\
            .neq('email', '')\
            .eq('do_not_contact', False)
    
    if count:
        # Get count using the filter chain
        response = apply_filters(
            supabase.from_('leads').select('*', count='exact')
        ).execute()
        return response.count
    else:
        # Calculate offset for pagination
        offset = (page - 1) * limit
        
        # Get total count for pagination metadata
        count_response = apply_filters(
            supabase.from_('leads').select('*', count='exact')
        ).execute()
        total = count_response.count if count_response.count is not None else 0
        
        # Get paginated data
        response = apply_filters(
            supabase.from_('leads').select('*')
        ).range(offset, offset + limit - 1).execute()
        
        return {
            'items': response.data,
            'total': total,
            'page': page,
            'page_size': limit,
            'total_pages': math.ceil(total / limit) if total > 0 else 1
        }

async def get_leads_with_phone(company_id: UUID, count: bool = False, page: int = 1, limit: int = 50):
    """
    Get leads with phone numbers for a company with pagination support
    
    Args:
        company_id: UUID of the company
        count: If True, return only the count of leads
        page: Page number (1-indexed)
        limit: Number of leads per page
        
    Returns:
        If count=True: Total number of leads
        If count=False: Dict containing paginated leads data and metadata
    """
    def apply_filters(query):
        return query\
            .eq('company_id', str(company_id))\
            .neq('phone_number', None)\
            .neq('phone_number', '')\
            .eq('do_not_contact', False)
    
    if count:
        # Get count using the filter chain
        response = apply_filters(
            supabase.from_('leads').select('*', count='exact')
        ).execute()
        return response.count
    else:
        # Calculate offset for pagination
        offset = (page - 1) * limit
        
        # Get total count for pagination metadata
        count_response = apply_filters(
            supabase.from_('leads').select('*', count='exact')
        ).execute()
        total = count_response.count if count_response.count is not None else 0
        
        # Get paginated data
        response = apply_filters(
            supabase.from_('leads').select('*')
        ).range(offset, offset + limit - 1).execute()
        
        return {
            'items': response.data,
            'total': total,
            'page': page,
            'page_size': limit,
            'total_pages': math.ceil(total / limit) if total > 0 else 1
        }

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

async def get_company_email_logs(company_id: UUID, campaign_id: Optional[UUID] = None, lead_id: Optional[UUID] = None, campaign_run_id: Optional[UUID] = None):
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
    
    if campaign_run_id:
        query = query.eq('campaign_run_id', str(campaign_run_id))
    
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

async def get_email_logs_reminder(campaign_id: UUID, days_between_reminders: int, reminder_type: Optional[str] = None):
    """
    Fetch all email logs that need to be processed for reminders.
    Joins with campaigns and companies to ensure we only get active records.
    Excludes deleted companies.
    Only fetches records where:
    - For first reminder (reminder_type is None):
      - No reminder has been sent yet (last_reminder_sent is NULL)
      - More than days_between_reminders days have passed since the initial email was sent
    - For subsequent reminders:
      - last_reminder_sent equals the specified reminder_type
      - More than days_between_reminders days have passed since the last reminder was sent
    
    Args:
        reminder_type: Optional type of reminder to filter by (e.g., 'r1' for first reminder)
    
    Returns:
        List of dictionaries containing email log data with campaign and company information
    """
    try:
        # Calculate the date threshold (days_between_reminders days ago from now)
        days_between_reminders_ago = (datetime.now(timezone.utc) - timedelta(days=days_between_reminders)).isoformat()
        
        # Build the base query
        query = supabase.table('email_logs')\
            .select(
                'id, sent_at, has_replied, last_reminder_sent, last_reminder_sent_at, lead_id, ' +
                'campaigns!inner(id, name, company_id, companies!inner(id, name, account_email, account_password, account_type)), ' +
                'leads!inner(email)'
            )\
            .eq('has_replied', False)\
            .eq('campaigns.id', str(campaign_id))\
            .eq('campaigns.companies.deleted', False)
            
        # Add reminder type filter
        if reminder_type is None:
            query = query\
                .is_('last_reminder_sent', 'null')\
                .lt('sent_at', days_between_reminders_ago)  # Only check sent_at for first reminder
        else:
            query = query\
                .eq('last_reminder_sent', reminder_type)\
                .lt('last_reminder_sent_at', days_between_reminders_ago)  # Check last reminder timing
            
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

async def create_campaign_run(campaign_id: UUID, status: str = "idle", leads_total: int = 0, leads_processed: int = 0):
    """
    Create a new campaign run record
    
    Args:
        campaign_id: UUID of the campaign
        status: Status of the run ('idle', 'running', 'completed')
        leads_total: Total number of leads available for this run
        leads_processed: Number of leads processed so far (defaults to 0)
        
    Returns:
        Dict containing the created campaign run record
    """
    try:
        campaign_run_data = {
            'campaign_id': str(campaign_id),
            'status': status,
            'leads_total': leads_total,
            'leads_processed': leads_processed,
            'run_at': datetime.now(timezone.utc).isoformat()
        }
        
        response = supabase.table('campaign_runs').insert(campaign_run_data).execute()
        
        if not response.data:
            logger.error(f"Failed to create campaign run for campaign {campaign_id}")
            return None
            
        return response.data[0]
    except Exception as e:
        logger.error(f"Error creating campaign run: {str(e)}")
        return None

async def update_campaign_run_status(campaign_run_id: UUID, status: str):
    """
    Update the status of a campaign run
    
    Args:
        campaign_run_id: UUID of the campaign run
        status: New status ('idle', 'running', 'completed')
        
    Returns:
        Dict containing the updated campaign run record or None if update failed
    """
    try:
        if status not in ['idle', 'running', 'completed']:
            logger.error(f"Invalid campaign run status: {status}")
            return None
            
        response = supabase.table('campaign_runs').update({
            'status': status
        }).eq('id', str(campaign_run_id)).execute()
        
        if not response.data:
            logger.error(f"Failed to update status for campaign run {campaign_run_id}")
            return None
            
        return response.data[0]
    except Exception as e:
        logger.error(f"Error updating campaign run status: {str(e)}")
        return None

async def update_campaign_run_progress(
    campaign_run_id: UUID, 
    leads_processed: int,
    leads_total: Optional[int] = None,
    increment: bool = False
):
    """
    Update the progress of a campaign run
    
    Args:
        campaign_run_id: UUID of the campaign run
        leads_processed: Number of leads processed so far
        leads_total: Optional total number of leads for the campaign run
        increment: If True, increment the leads_processed count instead of setting it
        
    Returns:
        Dict containing the updated campaign run record or None if update failed
    """
    try:
        # Prepare update data
        update_data = {}
        
        if increment:
            # Get current progress first
            current = supabase.table('campaign_runs').select('leads_processed').eq('id', str(campaign_run_id)).execute()
            if current.data and len(current.data) > 0:
                current_count = current.data[0].get('leads_processed', 0) or 0
                update_data['leads_processed'] = current_count + leads_processed
            else:
                # Fallback to setting value directly if we can't get current value
                update_data['leads_processed'] = leads_processed
        else:
            update_data['leads_processed'] = leads_processed
            
        # Set total leads if provided
        if leads_total is not None:
            update_data['leads_total'] = leads_total
            
        response = supabase.table('campaign_runs').update(update_data).eq('id', str(campaign_run_id)).execute()
        
        if not response.data:
            logger.error(f"Failed to update progress for campaign run {campaign_run_id}")
            return None
            
        # Check if leads_processed equals leads_total and update status if needed
        if not increment and leads_total is not None and leads_processed >= leads_total:
            # All leads have been processed, mark as completed
            await update_campaign_run_status(campaign_run_id, "completed")
        
        return response.data[0]
    except Exception as e:
        logger.error(f"Error updating campaign run progress: {str(e)}")
        return None

async def get_campaign_runs(company_id: UUID, campaign_id: Optional[UUID] = None) -> List[Dict[str, Any]]:
    """
    Get campaign runs for a company, optionally filtered by campaign_id.
    
    Args:
        company_id: UUID of the company
        campaign_id: Optional UUID of the campaign to filter runs by
        
    Returns:
        List of campaign run records including campaign name
    """
    try:
        if campaign_id:
            # If campaign_id is provided, directly filter campaign_runs and join with campaigns for the name
            query = supabase.table('campaign_runs').select(
                '*,campaigns!inner(name,type)'
            ).eq('campaign_id', str(campaign_id))
        else:
            # If only company_id is provided, join with campaigns to get all runs for the company
            query = supabase.table('campaign_runs').select(
                '*,campaigns!inner(name,type,company_id)'
            ).eq('campaigns.company_id', str(company_id))
            
        # Execute query and sort by run_at in descending order
        response = query.order('run_at', desc=True).execute()
        logger.info(f"Campaign runs: {response.data}")
        return response.data if response.data else []
        
    except Exception as e:
        logger.error(f"Error fetching campaign runs: {str(e)}")
        return []

async def update_lead_enrichment(lead_id: UUID, enriched_data: dict) -> Dict:
    """
    Update the enriched data for a lead
    
    Args:
        lead_id: UUID of the lead to update
        enriched_data: Dictionary containing enriched data
        
    Returns:
        Updated lead record
        
    Raises:
        HTTPException: If lead not found or update fails
    """
    # Convert to JSON string if it's a dict
    enriched_data_str = json.dumps(enriched_data) if isinstance(enriched_data, dict) else enriched_data
    
    try:
        response = supabase.table("leads")\
            .update({"enriched_data": enriched_data_str})\
            .eq("id", str(lead_id))\
            .execute()
        
        if not response.data:
            logger.error(f"Failed to update lead {lead_id} enrichment")
            raise HTTPException(status_code=404, detail="Lead not found")
        
        return response.data[0]
    except Exception as e:
        logger.error(f"Error updating lead enrichment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Email Queue Database Functions

async def add_email_to_queue(
    company_id: UUID, 
    campaign_id: UUID, 
    campaign_run_id: UUID, 
    lead_id: UUID,
    subject: str,
    body: str,
    priority: int = 1, 
    scheduled_for: Optional[datetime] = None,
    email_log_id: Optional[UUID] = None
) -> dict:
    """
    Add an email to the processing queue
    
    Args:
        company_id: UUID of the company
        campaign_id: UUID of the campaign
        campaign_run_id: UUID of the campaign run
        lead_id: UUID of the lead
        subject: Subject of the email
        body: Body of the email
        priority: Priority of the email (higher number = higher priority)
        scheduled_for: When to process this email (defaults to now)
        
    Returns:
        The created queue item
    """
    if scheduled_for is None:
        scheduled_for = datetime.now(timezone.utc)
        
    queue_data = {
        'company_id': str(company_id),
        'campaign_id': str(campaign_id),
        'campaign_run_id': str(campaign_run_id),
        'lead_id': str(lead_id),
        'status': 'pending',
        'priority': priority,
        'scheduled_for': scheduled_for.isoformat(),
        'retry_count': 0,
        'max_retries': 3,
        'subject': subject,
        'email_body': body,
        'email_log_id': str(email_log_id) if email_log_id else None
    }
    
    try:
        response = supabase.table('email_queue').insert(queue_data).execute()
        return response.data[0]
    except Exception as e:
        logger.error(f"Error adding email to queue: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add email to queue: {str(e)}")


async def get_next_emails_to_process(company_id: UUID, limit: int) -> List[dict]:
    """
    Get the next batch of emails to process for a company based on throttle settings
    
    Args:
        company_id: UUID of the company
        limit: Maximum number of emails to retrieve
        
    Returns:
        List of email queue items to process
    """
    # Get the current time
    now = datetime.now(timezone.utc)
    
    try:
        # Get pending emails that are scheduled for now or earlier, ordered by priority and creation time
        response = supabase.table('email_queue')\
            .select('*')\
            .eq('company_id', str(company_id))\
            .eq('status', 'pending')\
            .lte('scheduled_for', now.isoformat())\
            .order('priority', desc=True)\
            .order('created_at')\
            .limit(limit)\
            .execute()
            
        return response.data
    except Exception as e:
        logger.error(f"Error getting next emails to process: {str(e)}")
        return []


async def update_queue_item_status(
    queue_id: UUID, 
    status: str, 
    processed_at: Optional[datetime] = None, 
    error_message: Optional[str] = None,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    retry_count: Optional[int] = None
) -> dict:
    """
    Update the status of a queue item
    
    Args:
        queue_id: UUID of the queue item
        status: New status (pending, processing, sent, failed)
        processed_at: When the item was processed
        error_message: Error message if any
        
    Returns:
        Updated queue item
    """
    update_data = {'status': status}
    
    if retry_count is not None:
        update_data['retry_count'] = retry_count
    
    if processed_at:
        update_data['processed_at'] = processed_at.isoformat()
        
    if error_message:
        update_data['error_message'] = error_message
    
    if subject:
        update_data['subject'] = subject
    
    if body:
        update_data['email_body'] = body
    
    try:    
        response = supabase.table('email_queue')\
            .update(update_data)\
            .eq('id', str(queue_id))\
            .execute()
            
        if not response.data:
            logger.error(f"Failed to update queue item {queue_id}")
            raise HTTPException(status_code=404, detail="Queue item not found")
            
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating queue item status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update queue item: {str(e)}")


async def get_email_throttle_settings(company_id: UUID) -> dict:
    """
    Get email throttle settings for a company
    
    Args:
        company_id: UUID of the company
        
    Returns:
        Throttle settings dict with fields:
        - max_emails_per_hour (default: 500)
        - max_emails_per_day (default: 500)
        - enabled (default: True)
    """
    try:
        response = supabase.table('email_throttle_settings')\
            .select('*')\
            .eq('company_id', str(company_id))\
            .execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            # Return default settings
            return {
                'max_emails_per_hour': 500,
                'max_emails_per_day': 500,
                'enabled': True
            }
    except Exception as e:
        logger.error(f"Error getting email throttle settings: {str(e)}")
        # Return default settings on error
        return {
            'max_emails_per_hour': 500,
            'max_emails_per_day': 500,
            'enabled': True
        }


async def update_email_throttle_settings(
    company_id: UUID, 
    max_emails_per_hour: int, 
    max_emails_per_day: int, 
    enabled: bool = True
) -> dict:
    """
    Update email throttle settings for a company
    
    Args:
        company_id: UUID of the company
        max_emails_per_hour: Maximum emails per hour
        max_emails_per_day: Maximum emails per day
        enabled: Whether throttling is enabled
        
    Returns:
        Updated throttle settings
    """
    now = datetime.now(timezone.utc)
    
    settings_data = {
        'company_id': str(company_id),
        'max_emails_per_hour': max_emails_per_hour,
        'max_emails_per_day': max_emails_per_day,
        'enabled': enabled,
        'updated_at': now.isoformat()
    }
    
    try:
        # Check if settings already exist
        existing = await get_email_throttle_settings(company_id)
        
        if existing and 'id' in existing:
            # Update existing settings
            response = supabase.table('email_throttle_settings')\
                .update(settings_data)\
                .eq('company_id', str(company_id))\
                .execute()
        else:
            # Create new settings
            settings_data['created_at'] = now.isoformat()
            response = supabase.table('email_throttle_settings')\
                .insert(settings_data)\
                .execute()
                
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update throttle settings")
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating email throttle settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update throttle settings: {str(e)}")


async def get_emails_sent_count(company_id: UUID, start_time: datetime) -> int:
    """
    Get the count of emails sent for a company since the start time
    
    Args:
        company_id: UUID of the company
        start_time: Datetime to count from
        
    Returns:
        Number of emails sent
    """
    try:
        response = supabase.table('email_queue')\
            .select('id', count='exact')\
            .eq('company_id', str(company_id))\
            .eq('status', 'sent')\
            .gte('processed_at', start_time.isoformat())\
            .execute()
            
        return response.count
    except Exception as e:
        logger.error(f"Error getting emails sent count: {str(e)}")
        return 0


async def get_pending_emails_count(campaign_run_id: UUID) -> int:
    """
    Get the count of pending emails for a campaign run
    
    Args:
        campaign_run_id: UUID of the campaign run
        
    Returns:
        Number of pending emails
    """
    try:
        response = supabase.table('email_queue')\
            .select('id', count='exact')\
            .eq('campaign_run_id', str(campaign_run_id))\
            .in_('status', ['pending', 'processing'])\
            .execute()
            
        return response.count
    except Exception as e:
        logger.error(f"Error getting pending emails count: {str(e)}")
        return 0


async def get_running_campaign_runs(company_id: UUID, campaign_type: List[str]) -> List[dict]:
    """
    Get all campaign runs with status 'running' for a company
    
    Args:
        company_id: UUID of the company
        campaign_type: List of campaign types (email, call, email_and_call)
    Returns:
        List of running campaign runs
    """
    try:
        # Join campaign_runs with campaigns to filter by company_id and campaign_type
        response = supabase.table('campaign_runs')\
            .select('*, campaigns!inner(company_id, type)')\
            .eq('campaigns.company_id', str(company_id))\
            .in_('campaigns.type', campaign_type)\
            .eq('status', 'running')\
            .execute()
            
        return response.data
    except Exception as e:
        logger.error(f"Error getting running campaign runs: {str(e)}")
        return []

# Do Not Email List Functions
async def add_to_do_not_email_list(email: str, reason: str, company_id: Optional[UUID] = None) -> Dict:
    """
    Add an email to the do_not_email list
    
    Args:
        email: The email address to add
        reason: Reason for adding to the list (e.g. 'hard_bounce', 'unsubscribe')
        company_id: Optional company ID if specific to a company
        
    Returns:
        Dict with success status
    """
    email = email.lower().strip()  # Normalize email
    
    try:
        # Check if already in the list
        check_response = supabase.table('do_not_email')\
            .select('*')\
            .eq('email', email)\
            .execute()
        
        # If already exists, return early
        if check_response.data and len(check_response.data) > 0:
            return {"success": True, "email": email, "already_exists": True}
        
        # Insert new record
        current_time = datetime.now(timezone.utc).isoformat()
        insert_data = {
            "email": email,
            "reason": reason if reason else "Imported from CSV",
            "company_id": str(company_id) if company_id else None,
            "created_at": current_time,
            "updated_at": current_time
        }
        
        response = supabase.table('do_not_email')\
            .insert(insert_data)\
            .execute()
            
        # Also update any leads with this email to mark do_not_contact as true
        await update_lead_do_not_contact_by_email(email, company_id)
        
        if response.data and len(response.data) > 0:
            logger.info(f"Added {email} to do_not_email list")
            return {"success": True, "email": email}
        else:
            logger.error(f"Failed to add {email} to do_not_email list")
            return {"success": False, "email": email, "error": "Failed to add to list"}
            
    except Exception as e:
        logger.error(f"Error adding email to do_not_email list: {str(e)}")
        return {"success": False, "email": email, "error": str(e)}

async def is_email_in_do_not_email_list(email: str, company_id: Optional[UUID] = None) -> bool:
    """
    Check if an email is in the do_not_email list
    
    Args:
        email: Email address to check
        company_id: Optional company ID to check company-specific exclusions
        
    Returns:
        Boolean indicating if email should not be contacted
    """
    email = email.lower().strip()  # Normalize email
    
    try:
        # First check global do_not_email entries (no company_id)
        global_response = supabase.table('do_not_email')\
            .select('id')\
            .is_('company_id', 'null')\
            .eq('email', email)\
            .limit(1)\
            .execute()
            
        if global_response.data and len(global_response.data) > 0:
            return True
            
        # If company_id provided, also check company-specific exclusions
        if company_id:
            company_response = supabase.table('do_not_email')\
                .select('id')\
                .eq('company_id', str(company_id))\
                .eq('email', email)\
                .limit(1)\
                .execute()
                
            if company_response.data and len(company_response.data) > 0:
                return True
                
        return False
    except Exception as e:
        logger.error(f"Error checking do_not_email list: {str(e)}")
        # If error occurs, assume safe approach and return True
        return True

async def get_do_not_email_list(company_id: Optional[UUID] = None, 
                               page_number: int = 1, 
                               limit: int = 50) -> Dict:
    """
    Get entries from the do_not_email list with pagination
    
    Args:
        company_id: Optional company ID to filter by
        page_number: Page number (1-indexed)
        limit: Number of results per page
        
    Returns:
        Dict with items and pagination info matching the leads endpoint format
    """
    try:
        # Calculate offset for pagination
        offset = (page_number - 1) * limit
        
        # Build base query for count
        count_query = supabase.table('do_not_email').select('id', count='exact')
        
        # Build base query for data
        data_query = supabase.table('do_not_email').select('*')
        
        # Add filters based on company_id
        if company_id is None:
            # Get global entries (no company_id)
            count_query = count_query.is_('company_id', 'null')
            data_query = data_query.is_('company_id', 'null')
        else:
            # Get only company-specific entries
            count_query = count_query.eq('company_id', str(company_id))
            data_query = data_query.eq('company_id', str(company_id))
        
        # Execute count query
        count_response = count_query.execute()
        total = count_response.count if count_response.count is not None else 0
        
        # Get paginated results with ordering
        response = data_query\
            .order('created_at', desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        return {
            'items': response.data,
            'total': total,
            'page': page_number,
            'page_size': limit,
            'total_pages': math.ceil(total / limit) if total > 0 else 1
        }
    except Exception as e:
        logger.error(f"Error getting do_not_email list: {str(e)}")
        return {
            'items': [],
            'total': 0,
            'page': page_number,
            'page_size': limit,
            'total_pages': 1
        }

async def remove_from_do_not_email_list(email: str, company_id: Optional[UUID] = None) -> Dict:
    """
    Remove an email from the do_not_email list
    
    Args:
        email: Email address to remove
        company_id: Optional company ID if removing from company-specific list
        
    Returns:
        Dict with success status
    """
    email = email.lower().strip()  # Normalize email
    
    try:
        # Build query to delete email from do_not_email list
        query = supabase.table('do_not_email').delete()
        
        # Add email filter
        query = query.eq('email', email)
        
        # Add company filter if provided
        if company_id:
            query = query.eq('company_id', str(company_id))
        else:
            query = query.is_('company_id', 'null')
        
        # Execute the delete query
        response = query.execute()
        
        if response.data:
            # Update lead's do_not_contact to False
            await update_lead_do_not_contact_by_email(email, company_id, False)
            return {"success": True, "email": email}
        else:
            return {"success": False, "error": "Email not found in the list"}
    except Exception as e:
        logger.error(f"Error removing email from do_not_email list: {str(e)}")
        return {"success": False, "error": str(e)}

async def update_last_processed_bounce_uid(company_id: UUID, uid: str) -> bool:
    """
    Update the last processed bounce UID for a company
    
    Args:
        company_id: UUID of the company
        uid: The UID of the last processed bounce email
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Use update method directly without awaiting it
        response = supabase.table('companies')\
            .update({"last_processed_bounce_uid": uid, "updated_at": datetime.now(timezone.utc)})\
            .eq('id', str(company_id))\
            .execute()
        
        if response.data and len(response.data) > 0:
            logger.info(f"Updated last_processed_bounce_uid to {uid} for company {company_id}")
            return True
        else:
            logger.error(f"Failed to update last_processed_bounce_uid for company {company_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating last_processed_bounce_uid: {str(e)}")
        return False

async def get_email_log_by_message_id(message_id: str) -> Optional[Dict]:
    """
    Get email log by message ID
    
    Args:
        message_id: The message ID to look up
        
    Returns:
        Email log record if found, None otherwise
    """
    try:
        # Query email_log_details where message_id is stored, then join with email_logs
        response = supabase.table('email_log_details')\
            .select('email_logs_id')\
            .eq('message_id', message_id)\
            .limit(1)\
            .execute()
        
        # If we found a matching message_id, get the associated email log
        if response.data and len(response.data) > 0:
            email_logs_id = response.data[0]['email_logs_id']
            
            # Now get the email log with this ID
            email_log_response = supabase.table('email_logs')\
                .select('*')\
                .eq('id', email_logs_id)\
                .limit(1)\
                .execute()
            
            if email_log_response.data and len(email_log_response.data) > 0:
                return email_log_response.data[0]
        
        return None
            
    except Exception as e:
        logger.error(f"Error getting email log by message ID: {str(e)}")
        return None

async def get_email_queue_items(status: Optional[str] = 'pending', limit: int = 100) -> List[dict]:
    """
    Get email queue items by status
    
    Args:
        status: Status of items to retrieve (pending, processing, sent, failed)
        limit: Maximum number of items to retrieve
        
    Returns:
        List of email queue items
    """
    try:
        response = supabase.table('email_queue')\
            .select('*')\
            .eq('status', status)\
            .order('priority', desc=True)\
            .order('created_at')\
            .limit(limit)\
            .execute()
            
        return response.data
    except Exception as e:
        logger.error(f"Error getting email queue items: {str(e)}")
        return []

async def update_lead_do_not_contact_by_email(email: str, company_id: Optional[UUID] = None, do_not_contact: bool = True) -> Dict:
    """
    Update a lead's do_not_contact status based on email address.
    
    Args:
        email: The email address of the lead to update
        company_id: Optional company ID to filter leads by company
        do_not_contact: Boolean to set the do_not_contact status
        
    Returns:
        Dict with success status and list of updated lead IDs
    """
    email = email.lower().strip()  # Normalize email
    
    try:
        # Build query to update leads with matching email
        query = supabase.table('leads').update({"do_not_contact": do_not_contact})
        
        # Add email filter
        query = query.eq('email', email)
        
        # Add company filter if provided
        if company_id:
            query = query.eq('company_id', str(company_id))
            
        # Execute the update without awaiting
        response = query.execute()
        
        updated_lead_ids = [lead['id'] for lead in response.data] if response.data else []
        logger.info(f"Updated do_not_contact to {do_not_contact} for leads with email {email}: {updated_lead_ids}")
        
        return {
            "success": True, 
            "updated_lead_ids": updated_lead_ids,
            "count": len(updated_lead_ids)
        }
    except Exception as e:
        logger.error(f"Error updating lead do_not_contact status for email {email}: {str(e)}")
        return {"success": False, "error": str(e), "count": 0}

# Partner Application Database Functions

async def create_partner_application(
    company_name: str,
    contact_name: str,
    contact_email: str,
    contact_phone: Optional[str],
    website: Optional[str],
    partnership_type: str,
    company_size: str,
    industry: str,
    current_solutions: Optional[str],
    target_market: Optional[str],
    motivation: str,
    additional_information: Optional[str]
) -> Dict:
    """
    Create a new partner application in the database
    
    Args:
        company_name: Name of the company
        contact_name: Name of the contact person
        contact_email: Email of the contact person
        contact_phone: Phone number of the contact person (optional)
        website: Company website (optional)
        partnership_type: Type of partnership (RESELLER, REFERRAL, TECHNOLOGY)
        company_size: Size of the company
        industry: Industry of the company
        current_solutions: Current solutions used (optional)
        target_market: Target market (optional)
        motivation: Motivation for partnership
        additional_information: Additional information (optional)
        
    Returns:
        Dict containing the created partner application record
    """
    application_data = {
        'company_name': company_name,
        'contact_name': contact_name,
        'contact_email': contact_email,
        'partnership_type': partnership_type,
        'company_size': company_size,
        'industry': industry,
        'motivation': motivation,
        'status': 'PENDING'  # Default status
    }
    
    # Add optional fields if provided
    if contact_phone:
        application_data['contact_phone'] = contact_phone
    if website:
        application_data['website'] = website
    if current_solutions:
        application_data['current_solutions'] = current_solutions
    if target_market:
        application_data['target_market'] = target_market
    if additional_information:
        application_data['additional_information'] = additional_information
    
    try:
        response = supabase.table('partner_applications').insert(application_data).execute()
        logger.info(f"Created partner application for {company_name}")
        return response.data[0]
    except Exception as e:
        logger.error(f"Error creating partner application: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create partner application: {str(e)}"
        )

async def get_partner_applications(
    status: Optional[str] = None,
    partnership_type: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> Dict:
    """
    Get a paginated list of partner applications with optional filtering
    
    Args:
        status: Filter by application status (optional)
        partnership_type: Filter by partnership type (optional)
        page: Page number for pagination (default: 1)
        limit: Number of items per page (default: 10)
        sort_by: Field to sort by (default: created_at)
        sort_order: Sort order (asc or desc) (default: desc)
        
    Returns:
        Dict containing the list of partner applications and pagination metadata
    """
    # Calculate offset for pagination
    offset = (page - 1) * limit
    
    # Start building the query
    query = supabase.table('partner_applications').select('*')
    
    # Apply filters if provided
    if status:
        query = query.eq('status', status)
    if partnership_type:
        query = query.eq('partnership_type', partnership_type)
    
    # Apply sorting
    sort_order_func = 'desc' if sort_order.lower() == 'desc' else 'asc'
    query = getattr(query.order(sort_by), sort_order_func)()
    
    # Get total count (without pagination) for calculating total pages
    count_query = supabase.table('partner_applications').select('id', count='exact')
    if status:
        count_query = count_query.eq('status', status)
    if partnership_type:
        count_query = count_query.eq('partnership_type', partnership_type)
    
    count_response = count_query.execute()
    total_count = count_response.count
    
    # Apply pagination to the main query
    query = query.range(offset, offset + limit - 1)
    
    # Execute the query
    response = query.execute()
    
    # Calculate total pages
    total_pages = math.ceil(total_count / limit)
    
    return {
        'items': response.data,
        'total': total_count,
        'page': page,
        'page_size': limit,
        'total_pages': total_pages
    }

async def get_partner_application_by_id(application_id: UUID) -> Optional[Dict]:
    """
    Get a partner application by ID, including its notes
    
    Args:
        application_id: UUID of the partner application
        
    Returns:
        Dict containing the partner application record with notes, or None if not found
    """
    try:
        # Get the partner application
        app_response = supabase.table('partner_applications').select('*').eq('id', str(application_id)).execute()
        
        if not app_response.data:
            return None
        
        application = app_response.data[0]
        
        # Get the notes for this application
        notes_response = supabase.table('partner_application_notes').select('*').eq('application_id', str(application_id)).order('created_at', desc=True).execute()
        
        application['notes'] = notes_response.data
        
        return application
    except Exception as e:
        logger.error(f"Error getting partner application {application_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get partner application: {str(e)}"
        )

async def update_partner_application_status(application_id: UUID, status: str) -> Optional[Dict]:
    """
    Update the status of a partner application
    
    Args:
        application_id: UUID of the partner application
        status: New status to set
        
    Returns:
        Dict containing the updated partner application record, or None if not found
    """
    try:
        # Check if application exists
        app_response = supabase.table('partner_applications').select('id').eq('id', str(application_id)).execute()
        
        if not app_response.data:
            return None
        
        # Update the application status
        update_data = {
            'status': status,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        response = supabase.table('partner_applications').update(update_data).eq('id', str(application_id)).execute()
        
        return response.data[0]
    except Exception as e:
        logger.error(f"Error updating partner application status {application_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update partner application status: {str(e)}"
        )

async def create_partner_application_note(application_id: UUID, author_name: str, note: str) -> Dict:
    """
    Add a note to a partner application
    
    Args:
        application_id: UUID of the partner application
        author_name: Name of the note author
        note: Content of the note
        
    Returns:
        Dict containing the created note record
    """
    try:
        # Check if application exists
        app_response = supabase.table('partner_applications').select('id').eq('id', str(application_id)).execute()
        
        if not app_response.data:
            raise HTTPException(
                status_code=404,
                detail=f"Partner application with ID {application_id} not found"
            )
        
        # Create the note
        note_data = {
            'application_id': str(application_id),
            'author_name': author_name,
            'note': note
        }
        
        response = supabase.table('partner_application_notes').insert(note_data).execute()
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating partner application note: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create partner application note: {str(e)}"
        )

async def get_partner_application_statistics() -> Dict:
    """
    Get statistics about partner applications
    
    Returns:
        Dict containing statistics about applications (counts by status, type, etc.)
    """
    try:
        # Get total count
        total_response = supabase.table('partner_applications').select('id', count='exact').execute()
        total_count = total_response.count
        
        # Get counts by status
        status_counts = {}
        for status in ['PENDING', 'REVIEWING', 'APPROVED', 'REJECTED']:
            status_response = supabase.table('partner_applications').select('id', count='exact').eq('status', status).execute()
            status_counts[status] = status_response.count
        
        # Get counts by partnership type
        type_counts = {}
        for p_type in ['RESELLER', 'REFERRAL', 'TECHNOLOGY']:
            type_response = supabase.table('partner_applications').select('id', count='exact').eq('partnership_type', p_type).execute()
            type_counts[p_type] = type_response.count
        
        # Get recent applications count (last 30 days)
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        recent_response = supabase.table('partner_applications').select('id', count='exact').gte('created_at', thirty_days_ago).execute()
        recent_count = recent_response.count
        
        return {
            'total_applications': total_count,
            'by_status': status_counts,
            'by_type': type_counts,
            'recent_applications': recent_count
        }
    except Exception as e:
        logger.error(f"Error getting partner application statistics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get partner application statistics: {str(e)}"
        )

async def get_leads_by_campaign(campaign_id: UUID) -> List[Dict]:
    """
    Get all leads associated with a campaign's company
    
    Args:
        campaign_id: UUID of the campaign
        
    Returns:
        List of lead records
    """
    try:
        # First get the campaign to get company_id
        campaign = await get_campaign_by_id(campaign_id)
        
        if not campaign:
            logger.warning(f"Campaign with ID {campaign_id} not found")
            return []
            
        # Get company_id from campaign
        company_id = campaign.get('company_id')
        if not company_id:
            logger.warning(f"Campaign {campaign_id} has no company_id")
            return []
            
        # Get all leads for this company
        leads_response = await get_leads_by_company(UUID(company_id), page_number=1, limit=1000)
        
        if not leads_response or 'data' not in leads_response:
            return []
            
        return leads_response.get('data', [])
        
    except Exception as e:
        logger.error(f"Error fetching leads for campaign {campaign_id}: {str(e)}")
        return []

async def get_lead_details(lead_id: UUID) -> Optional[Dict]:
    """
    Get detailed information about a lead, including any enrichment data
    
    Args:
        lead_id: UUID of the lead
        
    Returns:
        Dict containing lead details or None if not found
    """
    try:
        # First get basic lead information
        lead = await get_lead_by_id(lead_id)
        
        if not lead:
            logger.warning(f"Lead with ID {lead_id} not found")
            return None
            
        # Get communication history to get a more complete picture
        communication_history = await get_lead_communication_history(lead_id)
        
        # Return combined information
        return {
            **lead,
            "communication_history": communication_history.get("history", []) if communication_history else []
        }
        
    except Exception as e:
        logger.error(f"Error getting lead details for {lead_id}: {str(e)}")
        return None

async def process_do_not_email_csv_upload(
    company_id: UUID,
    file_url: str,
    user_id: UUID,
    task_id: UUID
):
    """
    Process a CSV file containing email addresses to add to the do_not_email list
    
    Args:
        company_id: UUID of the company
        file_url: URL of the uploaded file in storage
        user_id: UUID of the user who initiated the upload
        task_id: UUID of the upload task
    """
    try:
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
            storage = supabase.storage.from_("do-not-email-uploads")
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
        
        email_count = 0
        skipped_count = 0
        unmapped_headers = set()
        
        # Get CSV headers
        headers = csv_data.fieldnames
        if not headers:
            await update_task_status(task_id, "failed", "CSV file has no headers")
            return
            
        # Process each row
        for row in csv_data:
            try:
                email = row.get('email', '').strip()
                reason = row.get('reason', 'Imported from CSV').strip()
                
                if not email:
                    logger.info(f"Skipping row - no email address provided: {row}")
                    skipped_count += 1
                    continue
                
                # Add to do_not_email list
                result = await add_to_do_not_email_list(
                    email=email,
                    reason=reason,
                    company_id=company_id
                )
                
                if result["success"]:
                    email_count += 1
                    # Update any leads with this email to mark do_not_contact as true
                    await update_lead_do_not_contact_by_email(email, company_id)
                else:
                    logger.error(f"Failed to add {email} to do_not_email list: {result.get('error')}")
                    skipped_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing row: {str(e)}")
                logger.error(f"Row data that failed: {row}")
                skipped_count += 1
                continue
        
        # Update task status with results
        await update_task_status(
            task_id,
            "completed",
            json.dumps({
                "emails_saved": email_count,
                "emails_skipped": skipped_count,
                "unmapped_headers": list(unmapped_headers)
            })
        )
        
    except Exception as e:
        logger.error(f"Error processing do-not-email CSV upload: {str(e)}")
        await update_task_status(task_id, "failed", str(e))

async def get_email_queues_by_campaign_run(campaign_run_id: UUID, page_number: int = 1, limit: int = 20):
    """
    Get paginated email queues for a specific campaign run
    
    Args:
        campaign_run_id: UUID of the campaign run
        page_number: Page number to fetch (default: 1)
        limit: Number of items per page (default: 20)
        
    Returns:
        Dictionary containing paginated email queues and metadata
    """
    # Modify the base query to select fields from email_queue and join with leads
    base_query = supabase.table('email_queue')\
        .select('*, leads!inner(name, email)')\
        .eq('campaign_run_id', str(campaign_run_id))

    # Get total count
    total_count_query = supabase.table('email_queue')\
        .select('id', count='exact')\
        .eq('campaign_run_id', str(campaign_run_id))
    count_response = total_count_query.execute()
    total = count_response.count if count_response.count is not None else 0

    # Calculate offset from page_number
    offset = (page_number - 1) * limit

    # Get paginated data
    response = base_query.range(offset, offset + limit - 1).order('created_at', desc=True).execute()

    # Map leads fields to lead_name and lead_email
    items = [
        {**item, 'lead_name': item['leads']['name'], 'lead_email': item['leads']['email']} for item in response.data
    ]

    return {
        'items': items,
        'total': total,
        'page': page_number,
        'page_size': limit,
        'total_pages': (total + limit - 1) // limit if total > 0 else 1
    }

async def get_campaign_run(campaign_run_id: UUID) -> Optional[Dict]:
    """
    Get a campaign run by its ID
    
    Args:
        campaign_run_id: UUID of the campaign run
        
    Returns:
        Campaign run record or None if not found
    """
    try:
        response = supabase.table('campaign_runs').select('*').eq('id', str(campaign_run_id)).execute()
        
        if not response.data:
            return None
            
        return response.data[0]
        
    except Exception as e:
        logger.error(f"Error fetching campaign run {campaign_run_id}: {str(e)}")
        return None

async def get_campaigns(campaign_types: Optional[List[str]] = None):
    """
    Get all campaigns, optionally filtered by multiple types
    
    Args:
        campaign_types: Optional list of types to filter (['email', 'call'], etc.)
        
    Returns:
        List of campaigns
    """
    query = supabase.table('campaigns').select('*')
    
    if campaign_types:
        query = query.in_('type', campaign_types)    
    
    response = query.execute()
    return response.data

async def get_call_logs_reminder(campaign_id: UUID, days_between_reminders: int, reminder_type: Optional[str] = None):
    """
    Fetch all call logs that need to be processed for reminders.
    Joins with campaigns and companies to ensure we only get active records.
    Excludes deleted companies.
    Only fetches records where:
    - For first reminder (reminder_type is None):
      - No reminder has been sent yet (last_reminder_sent is NULL)
      - More than days_between_reminders days have passed since the initial call was sent
    - For subsequent reminders:
      - last_reminder_sent equals the specified reminder_type
      - More than days_between_reminders days have passed since the last reminder was sent
    
    Args:
        reminder_type: Optional type of reminder to filter by (e.g., 'r1' for first reminder)
    
    Returns:
        List of dictionaries containing call log data with campaign and company information
    """
    try:
        # Calculate the date threshold (days_between_reminders days ago from now)
        days_between_reminders_ago = (datetime.now(timezone.utc) - timedelta(days=days_between_reminders)).isoformat()
        
        # Build the base query
        query = supabase.table('calls')\
            .select(
                'id, created_at, is_reminder_eligible, last_reminder_sent, last_reminder_sent_at, lead_id, ' +
                'campaigns!inner(id, name, company_id, companies!inner(id, name)), ' +
                'leads!inner(phone_number,enriched_data)'
            )\
            .eq('is_reminder_eligible', True)\
            .eq('campaigns.id', str(campaign_id))\
            .eq('campaigns.companies.deleted', False)
            
        # Add reminder type filter
        if reminder_type is None:
            query = query\
                .is_('last_reminder_sent', 'null')\
                .lt('created_at', days_between_reminders_ago)  # Only check created_at for first reminder
        else:
            query = query\
                .eq('last_reminder_sent', reminder_type)\
                .lt('last_reminder_sent_at', days_between_reminders_ago)  # Check last reminder timing
            
        # Execute query with ordering
        response = query.order('created_at', desc=False).execute()
        
        # Flatten the nested structure to match the expected format
        flattened_data = []
        for record in response.data:
            campaign = record['campaigns']
            company = campaign['companies']
            lead = record['leads']
            
            flattened_record = {
                'call_log_id': record['id'],
                'created_at': record['created_at'],
                'sentiment': record['sentiment'],
                'last_reminder_sent': record['last_reminder_sent'],
                'last_reminder_sent_at': record['last_reminder_sent_at'],
                'lead_id': record['lead_id'],
                'lead_phone_number': lead['phone_number'],
                'lead_enriched_data': lead['enriched_data'],
                'campaign_id': campaign['id'],
                'campaign_name': campaign['name'],
                'company_id': company['id'],
                'company_name': company['name']
            }
            flattened_data.append(flattened_record)
            
        return flattened_data
    except Exception as e:
        logger.error(f"Error fetching call logs for reminder: {str(e)}")
        return []
    
async def get_call_by_id(call_id: UUID):
    response = supabase.table('calls').select('*').eq('id', str(call_id)).execute()
    return response.data[0] if response.data else None

async def update_call_reminder_sent_status(call_log_id: UUID, reminder_type: str, last_reminder_sent_at: datetime) -> bool:
    """
    Update the last_reminder_sent field and timestamp for a call log
    
    Args:
        call_log_id: UUID of the call log to update
        reminder_type: Type of reminder sent (e.g., 'r1' for first reminder)
        last_reminder_sent_at: Timestamp when the reminder was sent
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        response = supabase.table('calls')\
            .update({
                'last_reminder_sent': reminder_type,
                'last_reminder_sent_at': last_reminder_sent_at.isoformat()
            })\
            .eq('id', str(call_log_id))\
            .execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error updating reminder status for log {call_log_id}: {str(e)}")
        return False
    
async def add_call_to_queue(
    company_id: UUID, 
    campaign_id: UUID, 
    campaign_run_id: UUID, 
    lead_id: UUID,
    call_script: str,
    priority: int = 1, 
    scheduled_for: Optional[datetime] = None
) -> dict:
    """
    Add a call to the processing queue
    
    Args:
        company_id: UUID of the company
        campaign_id: UUID of the campaign
        campaign_run_id: UUID of the campaign run
        lead_id: UUID of the lead
        call_script: Script of the call
        priority: Priority of the call (higher number = higher priority)
        scheduled_for: When to process this call (defaults to now)
        
    Returns:
        The created queue item
    """
    if scheduled_for is None:
        scheduled_for = datetime.now(timezone.utc)
        
    queue_data = {
        'company_id': str(company_id),
        'campaign_id': str(campaign_id),
        'campaign_run_id': str(campaign_run_id),
        'lead_id': str(lead_id),
        'status': 'pending',
        'priority': priority,
        'scheduled_for': scheduled_for.isoformat(),
        'retry_count': 0,
        'max_retries': 3,
        'call_script': call_script
    }
    
    try:
        response = supabase.table('call_queue').insert(queue_data).execute()
        return response.data[0]
    except Exception as e:
        logger.error(f"Error adding call to queue: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add call to queue: {str(e)}")

async def update_call_queue_item_status(
    queue_id: UUID, 
    status: str, 
    processed_at: Optional[datetime] = None, 
    error_message: Optional[str] = None,
    call_script: Optional[str] = None,
    retry_count: Optional[int] = None
) -> dict:
    """
    Update the status of a call queue item
    
    Args:
        queue_id: UUID of the call queue item
        status: New status (pending, processing, sent, failed)
        processed_at: When the item was processed
        error_message: Error message if any
        call_script: Script of the call
    Returns:
        Updated call queue item
    """
    update_data = {'status': status}
    
    if retry_count is not None:
        update_data['retry_count'] = retry_count
    
    if processed_at:
        update_data['processed_at'] = processed_at.isoformat()
        
    if error_message:
        update_data['error_message'] = error_message
    
    if call_script:
        update_data['call_script'] = call_script

    try:    
        response = supabase.table('call_queue')\
            .update(update_data)\
            .eq('id', str(queue_id))\
            .execute()
            
        if not response.data:
            logger.error(f"Failed to update queue item {queue_id}")
            raise HTTPException(status_code=404, detail="Queue item not found")
            
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating call queue item status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update call queue item: {str(e)}")
    
async def get_calls_initiated_count(start_time: datetime) -> int:
    """
    Get the count of calls initiated since the start time
    
    Args:
        start_time: Datetime to count from
        
    Returns:
        Number of calls initiated
    """
    try:
        response = supabase.table('call_queue')\
            .select('id', count='exact')\
            .eq('status', 'sent')\
            .gte('processed_at', start_time.isoformat())\
            .execute()
            
        return response.count
    except Exception as e:
        logger.error(f"Error getting calls initiated count: {str(e)}")
        return 0

async def get_next_calls_to_process(company_id: UUID, limit: int) -> List[dict]:
    """
    Get the next batch of calls to process for a company
    
    Args:
        company_id: UUID of the company
        limit: Maximum number of calls to retrieve
        
    Returns:
        List of call queue items to process
    """
    # Get the current time
    now = datetime.now(timezone.utc)
    
    try:
        # Get pending calls that are scheduled for now or earlier, ordered by priority and creation time
        response = supabase.table('call_queue')\
            .select('*')\
            .eq('company_id', str(company_id))\
            .eq('status', 'pending')\
            .lte('scheduled_for', now.isoformat())\
            .order('priority', desc=True)\
            .order('created_at')\
            .limit(limit)\
            .execute()
            
        return response.data
    except Exception as e:
        logger.error(f"Error getting next calls to process: {str(e)}")
        return []

async def get_pending_calls_count(campaign_run_id: UUID) -> int:
    """
    Get the count of pending calls for a campaign run
    
    Args:
        campaign_run_id: UUID of the campaign run
        
    Returns:
        Number of pending calls
    """
    try:
        response = supabase.table('call_queue')\
            .select('id', count='exact')\
            .eq('campaign_run_id', str(campaign_run_id))\
            .in_('status', ['pending', 'processing'])\
            .execute()
            
        return response.count
    except Exception as e:
        logger.error(f"Error getting pending calls count: {str(e)}")
        return 0

async def get_call_queues_by_campaign_run(campaign_run_id: UUID, page_number: int = 1, limit: int = 20):
    """
    Get paginated call queues for a specific campaign run
    
    Args:
        campaign_run_id: UUID of the campaign run
        page_number: Page number to fetch (default: 1)
        limit: Number of items per page (default: 20)
        
    Returns:
        Dictionary containing paginated call queues and metadata
    """
    # Modify the base query to select fields from call_queue and join with leads
    base_query = supabase.table('call_queue')\
        .select('*, leads!inner(name, phone_number)')\
        .eq('campaign_run_id', str(campaign_run_id))

    # Get total count
    total_count_query = supabase.table('call_queue')\
        .select('id', count='exact')\
        .eq('campaign_run_id', str(campaign_run_id))
    count_response = total_count_query.execute()
    total = count_response.count if count_response.count is not None else 0

    # Calculate offset from page_number
    offset = (page_number - 1) * limit

    # Get paginated data
    response = base_query.range(offset, offset + limit - 1).order('created_at', desc=True).execute()

    # Map leads fields to lead_name and lead_phone
    items = [
        {**item, 'lead_name': item['leads']['name'], 'lead_phone': item['leads']['phone_number']} for item in response.data
    ]

    return {
        'items': items,
        'total': total,
        'page': page_number,
        'page_size': limit,
        'total_pages': (total + limit - 1) // limit if total > 0 else 1
    }

async def get_email_log_by_id(email_log_id: UUID):
    response = supabase.table('email_logs').select('*').eq('id', str(email_log_id)).execute()
    return response.data[0] if response.data else None

async def check_existing_call_queue_record(
    company_id: UUID,
    campaign_id: UUID,
    campaign_run_id: UUID,
    lead_id: UUID
) -> bool:
    """
    Check if a record with the given parameters already exists in the call_queue table
    
    Args:
        company_id: UUID of the company
        campaign_id: UUID of the campaign
        campaign_run_id: UUID of the campaign run
        lead_id: UUID of the lead
        
    Returns:
        bool: True if record exists, False otherwise
    """
    try:
        response = supabase.table('call_queue')\
            .select('id', count='exact')\
            .eq('company_id', str(company_id))\
            .eq('campaign_id', str(campaign_id))\
            .eq('campaign_run_id', str(campaign_run_id))\
            .eq('lead_id', str(lead_id))\
            .execute()
            
        return response.count > 0
    except Exception as e:
        logger.error(f"Error checking existing call queue record: {str(e)}")
        return False

async def update_call_reminder_eligibility(
    campaign_id: UUID,
    campaign_run_id: UUID,
    lead_id: UUID,
    is_reminder_eligible: bool = False
) -> bool:
    """
    Update the is_reminder_eligible column for a specific call record
    
    Args:
        campaign_id: UUID of the campaign
        campaign_run_id: UUID of the campaign run
        lead_id: UUID of the lead
        is_reminder_eligible: Boolean value to set (default: False)
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        response = supabase.table('calls')\
            .update({'is_reminder_eligible': is_reminder_eligible})\
            .eq('campaign_id', str(campaign_id))\
            .eq('campaign_run_id', str(campaign_run_id))\
            .eq('lead_id', str(lead_id))\
            .execute()
            
        return len(response.data) > 0
    except Exception as e:
        logger.error(f"Error updating call reminder eligibility: {str(e)}")
        return False

async def update_email_reminder_eligibility(
    campaign_id: UUID,
    campaign_run_id: UUID,
    lead_id: UUID,
    has_replied: bool = False
) -> bool:
    """
    Update the has_replied column for a specific email record
    
    Args:
        campaign_id: UUID of the campaign
        campaign_run_id: UUID of the campaign run
        lead_id: UUID of the lead
        has_replied: Boolean value to set (default: False)
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        response = supabase.table('email_logs')\
            .update({'has_replied': has_replied})\
            .eq('campaign_id', str(campaign_id))\
            .eq('campaign_run_id', str(campaign_run_id))\
            .eq('lead_id', str(lead_id))\
            .execute()
            
        return len(response.data) > 0
    except Exception as e:
        logger.error(f"Error updating email reminder eligibility: {str(e)}")
        return False

async def get_call_log_by_bland_id(bland_id: str):
    response = supabase.table('calls').select('*').eq('bland_call_id', bland_id).execute()
    return response.data[0] if response.data else None