import json
from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Union
import logging
import math
import csv
import io
from math import ceil
from dateutil import parser
import os
from supabase import create_client, Client
from src.config import get_settings
from fastapi import HTTPException
from src.utils.encryption import encrypt_password
import secrets
import json
from email_validator import validate_email, EmailNotValidError
import asyncpg
from asyncpg.pool import Pool

# Set up logger
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

settings = get_settings()
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)

# PostgreSQL connection pool
pg_pool: Optional[Pool] = None

async def init_pg_pool(force_reinit: bool = False):
    global pg_pool
    # Force close the old pool if reinitializing
    if force_reinit and pg_pool is not None:
        try:
            await pg_pool.close()
            logger.info("Closed old PostgreSQL connection pool before reinitialization")
        except Exception as e:
            logger.warning(f"Error closing old pool during reinit: {e}")

        pg_pool = None
    
    if pg_pool is None:
        try:
            pg_pool = await asyncpg.create_pool(
                user=os.getenv('POSTGRES_USER'),
                password=os.getenv('POSTGRES_PASSWORD'),
                database=os.getenv('POSTGRES_DB'),
                host=os.getenv('POSTGRES_HOST'),
                port=int(os.getenv('POSTGRES_PORT', '5432')),
                min_size=1,
                max_size=10 # 10 connections
            )
            logger.info("PostgreSQL connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing PostgreSQL connection pool: {str(e)}")
            raise

async def get_pg_pool() -> Pool:
    if pg_pool is None:
        await init_pg_pool()
    else:
        logger.info("Using existing PostgreSQL connection pool")
    return pg_pool

# Constants
TRIAL_PLAN_LEAD_LIMIT = 500

async def get_user_by_email(email: str):
    response = supabase.table('users').select('*').eq('email', email).execute()
    return response.data[0] if response.data else None

async def check_user_lead_limit(company_id: UUID) -> tuple[bool, str]:
    """
    Check if a company's owner has reached their lead limit based on their plan type.
    For trial users, checks against TRIAL_PLAN_LEAD_LIMIT.
    For subscription users, checks against their lead_tier within billing period.
    
    Args:
        company_id: UUID of the company
        
    Returns:
        tuple[bool, str]: (can_add_lead, error_message)
    """
    try:
        # Get company details with owner's user info
        company_query = supabase.table('companies')\
            .select('*, users!companies_user_id_fkey(plan_type, subscription_id, subscription_status, lead_tier, billing_period_start, billing_period_end)')\
            .eq('id', str(company_id))\
            .single()
        company = company_query.execute()
        
        if not company.data:
            return (False, "Company not found")
            
        # Get user's info
        user = company.data['users']
        
        # Check if user has active subscription
        if user.get('subscription_id') and user.get('subscription_status') == 'active':
            # Get all companies owned by this user
            companies = supabase.table('companies')\
                .select('id')\
                .eq('user_id', company.data['user_id'])\
                .execute()
                
            company_ids = [c['id'] for c in companies.data]
            
            # Count leads created within billing period across all user's companies
            leads_count = supabase.table('leads')\
                .select('count', count='exact')\
                .in_('company_id', company_ids)\
                .gte('created_at', user['billing_period_start'])\
                .lte('created_at', user['billing_period_end'])\
                .execute()
                
            if leads_count.count >= user['lead_tier']:
                return (False, f"You have reached your monthly lead limit of {user['lead_tier']} leads")
                
            return (True, "")
            
        # If not subscription, check trial limit
        if user['plan_type'] == 'trial':
            # Get all companies owned by this user
            companies = supabase.table('companies')\
                .select('id')\
                .eq('user_id', company.data['user_id'])\
                .execute()
                
            company_ids = [c['id'] for c in companies.data]
            
            # Count all leads across user's companies
            leads_count = supabase.table('leads')\
                .select('count', count='exact')\
                .in_('company_id', company_ids)\
                .execute()
                
            if leads_count.count >= TRIAL_PLAN_LEAD_LIMIT:
                return (False, f"Trial plan limit of {TRIAL_PLAN_LEAD_LIMIT} leads reached")
                
            return (True, "")
            
        return (False, "No active subscription or trial found")
        
    except Exception as e:
        logger.error(f"Error checking user lead limit: {str(e)}")
        return (False, f"Error checking lead limit: {str(e)}")

async def create_user(email: str, password_hash: str):
    user_data = {
        'email': email, 
        'password_hash': password_hash,
        'plan_type': 'trial',  # Set default plan type
        'channels_active': {
            'email': True,
            'phone': True,
            'linkedin': False,
            'whatsapp': False
        }
    }
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
    try:
        response = supabase.table('products').select('*').eq('company_id', str(company_id)).eq('deleted', False).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error in get_products_by_company for company {company_id}: {str(e)}", exc_info=True)
        return []

async def create_lead(company_id: UUID, lead_data: dict, upload_task_id: Optional[UUID] = None):
    try:
        # First check trial user limit
        can_add_lead, error_message = await check_user_lead_limit(company_id)
        if not can_add_lead:
            raise Exception(error_message)

        matches = await find_existing_leads(email=lead_data['email'], phone=lead_data['phone_number'], company_id=company_id)
        if len(matches) == 0:
            # Insert new lead
            lead_data['company_id'] = str(company_id)
            if upload_task_id:
                lead_data['upload_task_id'] = str(upload_task_id)
            logger.info(f"\nAttempting to insert lead with data: {lead_data}")
            response = supabase.table('leads').insert(lead_data).execute()
            return response.data[0]
        elif len(matches) == 1:
            # Safe update
            lead_id = matches[0]['id']

            lead_data['company_id'] = str(company_id)
            if upload_task_id:
                lead_data['upload_task_id'] = str(upload_task_id)
            logger.info(f"\nAttempting to update lead with data: {lead_data}")
            response = supabase.table('leads').update(lead_data).eq('id', lead_id).execute()
            return response.data[0]
        else:
            # Two matches — possible conflict
            email_match = next((m for m in matches if m['email'] == lead_data['email']), None)
            phone_match = next((m for m in matches if m['phone_number'] == lead_data['phone_number']), None)

            if email_match and phone_match and email_match['id'] == phone_match['id']:
                # Same lead, safe update
                lead_id = email_match['id']
                lead_data['company_id'] = str(company_id)
                if upload_task_id:
                    lead_data['upload_task_id'] = str(upload_task_id)
                logger.info(f"\nAttempting to update lead with data, third case: {lead_data}")
                response = supabase.table('leads').update(lead_data).eq('id', lead_id).execute()
                return response.data[0]
            else:
                # Two different leads, raise an error for conflict
                raise Exception(f"Different leads found for the email and phone number")

    except Exception as e:
        logger.info(f"\nError in create_lead: {str(e)}")
        raise e

async def get_leads_by_company(company_id: UUID, page_number: int = 1, limit: int = 20, search_term: Optional[str] = None):
    # Build base query
    base_query = supabase.table('leads').select('*', count='exact')\
        .eq('company_id', str(company_id))\
        .is_('deleted_at', 'null')  # Exclude soft-deleted leads
    
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

async def create_call(lead_id: UUID, product_id: UUID, campaign_id: UUID, script: Optional[str] = None, campaign_run_id: Optional[UUID] = None, last_called_at: Optional[datetime] = None):
    """
    Create a call record in the database
    
    Args:
        lead_id: UUID of the lead to call
        product_id: UUID of the product associated with the call
        campaign_id: UUID of the campaign associated with the call
        script: Optional script to use for the call
        campaign_run_id: Optional UUID of the campaign run
        last_called_at: Optional timestamp of when the call was initiated
        
    Returns:
        The created call record
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
            
        # Add last_called_at if provided
        if last_called_at is not None:
            call_data['last_called_at'] = last_called_at.isoformat() if isinstance(last_called_at, datetime) else last_called_at
        
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
    Soft delete a lead by setting its deleted_at timestamp
    
    Args:
        lead_id: UUID of the lead to delete
        
    Returns:
        bool: True if lead was marked as deleted successfully, False otherwise
    """
    try:
        # Update the lead with current timestamp in deleted_at
        response = supabase.table('leads')\
            .update({"deleted_at": datetime.now(timezone.utc).isoformat()})\
            .eq('id', str(lead_id))\
            .execute()
            
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error soft deleting lead {lead_id}: {str(e)}")
        return False

async def get_product_by_id(product_id: UUID):
    response = supabase.table('products').select('*').eq('id', str(product_id)).eq('deleted', False).execute()
    if not response.data:
        return None
    return response.data[0]

async def update_call_details(call_id: UUID, bland_call_id: str, last_called_at: Optional[datetime] = None):
    """
    Update call record with Bland call ID and optionally the last called timestamp
    
    Args:
        call_id: UUID of the call record
        bland_call_id: Bland AI call ID
        last_called_at: Optional timestamp of when the call was last initiated
    
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
        
        # Add last_called_at if provided
        if last_called_at is not None:
            call_data['last_called_at'] = last_called_at.isoformat() if isinstance(last_called_at, datetime) else last_called_at
            logger.info(f"Including last_called_at: {call_data['last_called_at']}")
        
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

async def update_call_webhook_data(bland_call_id: str, duration: str, sentiment: str, summary: str, transcripts: list[dict], recording_url: Optional[str] = None, reminder_eligible: bool = False, error_message: Optional[str] = None):
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
    if duration is not None:
        duration = int(float(duration))
    try:
        call_data = {
            'duration': duration,
            'sentiment': sentiment,
            'summary': summary,
            'transcripts': transcripts,
            'recording_url': recording_url,
            'is_reminder_eligible': reminder_eligible,
            'failure_reason': error_message
        }
        response = supabase.table('calls').update(call_data).eq('bland_call_id', bland_call_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating call webhook data for bland_call_id {bland_call_id}: {str(e)}")
        return None

async def get_calls_by_companies(company_ids: List[str]):
    # Get all leads for the companies (excluding soft-deleted)
    leads_response = supabase.table('leads')\
        .select('id')\
        .in_('company_id', company_ids)\
        .is_('deleted_at', None)\
        .execute()
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

async def get_calls_by_company_id(
    company_id: UUID,
    campaign_id: Optional[UUID] = None,
    campaign_run_id: Optional[UUID] = None,
    lead_id: Optional[UUID] = None,
    sentiment: Optional[str] = None,
    has_meeting_booked: Optional[bool] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page_number: int = 1,
    limit: int = 20
):
    """
    Get paginated calls for a company, optionally filtered by campaign ID, campaign run ID, lead ID, sentiment, meeting booked status, or date range
    
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
        
    Returns:
        Dictionary containing paginated calls and metadata
    """
    # Get calls with their related data using a join with campaigns
    base_query = supabase.table('calls').select(
        'id,lead_id,product_id,duration,sentiment,summary,bland_call_id,has_meeting_booked,transcripts,recording_url,last_called_at,failure_reason,created_at,campaign_id,leads(*),campaigns!inner(*)'
    ).eq('campaigns.company_id', str(company_id))
    
    # Add campaign filter if provided
    if campaign_id:
        base_query = base_query.eq('campaign_id', str(campaign_id))
    
    # Add campaign run filter if provided
    if campaign_run_id:
        base_query = base_query.eq('campaign_run_id', str(campaign_run_id))
    
    # Add lead filter if provided
    if lead_id:
        base_query = base_query.eq('lead_id', str(lead_id))
        
    # Add sentiment filter if provided
    if sentiment:
        base_query = base_query.eq('sentiment', sentiment)
        
    # Add meeting booked filter if provided
    if has_meeting_booked is not None:
        base_query = base_query.eq('has_meeting_booked', has_meeting_booked)
        
    # Add date range filters if provided
    if from_date:
        base_query = base_query.gte('created_at', from_date.isoformat())
    if to_date:
        base_query = base_query.lte('created_at', to_date.isoformat())

    # Get total count with the same filters
    total_count_query = supabase.table('calls').select(
        'id,leads(*),campaigns!inner(*)', count='exact'
    ).eq('campaigns.company_id', str(company_id))
    
    if campaign_id:
        total_count_query = total_count_query.eq('campaign_id', str(campaign_id))
    if campaign_run_id:
        total_count_query = total_count_query.eq('campaign_run_id', str(campaign_run_id))
    if lead_id:
        total_count_query = total_count_query.eq('lead_id', str(lead_id))
    if sentiment:
        total_count_query = total_count_query.eq('sentiment', sentiment)
    if has_meeting_booked is not None:
        total_count_query = total_count_query.eq('has_meeting_booked', has_meeting_booked)
    if from_date:
        total_count_query = total_count_query.gte('created_at', from_date.isoformat())
    if to_date:
        total_count_query = total_count_query.lte('created_at', to_date.isoformat())
        
    count_response = total_count_query.execute()
    total = count_response.count if count_response.count is not None else 0

    # Calculate offset from page_number
    offset = (page_number - 1) * limit

    # Get paginated data
    response = base_query.range(offset, offset + limit - 1).order('created_at', desc=True).execute()
    
    # Add lead_name, lead_phone_number and campaign_name to each call record
    calls = []
    for call in response.data:
        call['lead_name'] = call['leads']['name'] if call.get('leads') else None
        call['lead_phone_number'] = call['leads']['phone_number'] if call.get('leads') else None
        call['campaign_name'] = call['campaigns']['name'] if call.get('campaigns') else None
        calls.append(call)
    
    return {
        'items': calls,
        'total': total,
        'page': page_number,
        'page_size': limit,
        'total_pages': (total + limit - 1) // limit if total > 0 else 1
    }

async def create_campaign(company_id: UUID, name: str, description: Optional[str], product_id: UUID, type: str = 'email', template: Optional[str] = None, number_of_reminders: Optional[int] = 0, days_between_reminders: Optional[int] = 0, phone_number_of_reminders: Optional[int] = 0, phone_days_between_reminders: Optional[int] = 0, auto_reply_enabled: Optional[bool] = False, trigger_call_on: Optional[str] = None, scheduled_at: Optional[datetime] = None):
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
        'trigger_call_on': trigger_call_on,
        'scheduled_at': scheduled_at.isoformat() if scheduled_at else None
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

async def get_leads_with_email(
    campaign_id: UUID, 
    count: bool = False, 
    last_id: Optional[UUID] = None,
    limit: int = 50
):
    """
    Get leads with email addresses for a campaign with keyset pagination support.
    Only returns leads that don't have any record in the email_queue table for this campaign.
    Uses native PostgreSQL query for better performance.
    
    Args:
        campaign_id: UUID of the campaign
        count: If True, return only the count of matching leads
        last_id: UUID of the last lead from previous page (for pagination)
        limit: Number of leads to return per page
        
    Returns:
        If count=True: Total number of leads
        If count=False: Dict with leads data and pagination info
    """
    try:
        # First get the campaign to get company_id
        campaign = await get_campaign_by_id(campaign_id)
        if not campaign:
            return 0 if count else {'items': [], 'has_more': False}

        pool = await get_pg_pool()

        # Count query
        count_sql = """
            SELECT COUNT(*) 
            FROM leads l
            WHERE l.company_id = $1
            AND l.email IS NOT NULL
            AND l.email != ''
            AND l.do_not_contact = false
            AND l.deleted_at IS NULL
            AND NOT EXISTS (
                SELECT 1 
                FROM email_queue eq
                WHERE eq.lead_id::uuid = l.id
                AND eq.campaign_id = $2
            )
        """

        # Full query with keyset pagination
        leads_sql = """
            SELECT l.*
            FROM leads l
            WHERE l.company_id = $1
            AND l.email IS NOT NULL
            AND l.email != ''
            AND l.do_not_contact = false
            AND l.deleted_at IS NULL
            AND NOT EXISTS (
                SELECT 1 
                FROM email_queue eq
                WHERE eq.lead_id::uuid = l.id
                AND eq.campaign_id = $2
            )
        """
        
        # Add keyset pagination condition if last_id is provided
        params = [str(campaign['company_id']), str(campaign_id)]
        if last_id is not None:
            leads_sql += " AND l.id > $3"
            params.append(str(last_id))
            
        # Add ordering and limit
        leads_sql += """
            ORDER BY l.id ASC
            LIMIT $%d
        """ % (len(params) + 1)
        params.append(limit + 1)  # Fetch one extra to determine if there are more results
        
        async with pool.acquire() as conn:
            if count:
                total_count = await conn.fetchval(count_sql, str(campaign['company_id']), str(campaign_id))
                return total_count
            
            # Get paginated results
            leads = await conn.fetch(leads_sql, *params)
            
            # Convert to list of dicts
            leads_data = [dict(lead) for lead in leads]
            
            # Determine if there are more results
            has_more = len(leads_data) > limit
            if has_more:
                leads_data = leads_data[:limit]  # Remove the extra item we fetched
            
            return {
                'items': leads_data,
                'has_more': has_more
            }
            
    except Exception as e:
        logger.error(f"Error getting leads with email for campaign {campaign_id}: {str(e)}")
        raise

async def get_leads_with_phone(campaign_id: UUID, count: bool = False, last_id: Optional[UUID] = None, limit: int = 50):
    """
    Get leads with phone numbers for a campaign with keyset pagination support.
    Only returns leads that don't have any record in the call_queue table for this campaign.
    Uses native PostgreSQL query for better performance.
    
    Args:
        campaign_id: UUID of the campaign
        count: If True, return only the count of matching leads
        last_id: UUID of the last lead from previous page (for pagination)
        limit: Number of leads to return per page
        
    Returns:
        If count=True: Total number of leads
        If count=False: Dict with leads data and pagination info
    """
    try:
        # First get the campaign to get company_id
        campaign = await get_campaign_by_id(campaign_id)
        if not campaign:
            return 0 if count else {'items': [], 'has_more': False}

        pool = await get_pg_pool()
        
        # Count query
        count_sql = """
            SELECT COUNT(*) 
            FROM leads l
            WHERE l.company_id = $1
            AND l.phone_number IS NOT NULL
            AND l.phone_number != ''
            AND l.do_not_contact = false
            AND l.deleted_at IS NULL
            AND NOT EXISTS (
                SELECT 1 
                FROM call_queue cq
                WHERE cq.lead_id::uuid = l.id
                AND cq.campaign_id = $2
            )
        """

        # Full query with keyset pagination
        leads_sql = """
            SELECT l.*
            FROM leads l
            WHERE l.company_id = $1
            AND l.phone_number IS NOT NULL
            AND l.phone_number != ''
            AND l.do_not_contact = false
            AND l.deleted_at IS NULL
            AND NOT EXISTS (
                SELECT 1 
                FROM call_queue cq
                WHERE cq.lead_id::uuid = l.id
                AND cq.campaign_id = $2
            )
        """
        
        # Add keyset pagination condition if last_id is provided
        params = [str(campaign['company_id']), str(campaign_id)]
        if last_id is not None:
            leads_sql += " AND l.id > $3"
            params.append(str(last_id))
            
        # Add ordering and limit
        leads_sql += """
            ORDER BY l.id ASC
            LIMIT $%d
        """ % (len(params) + 1)
        params.append(limit + 1)  # Fetch one extra to determine if there are more results
        
        async with pool.acquire() as conn:
            if count:
                total_count = await conn.fetchval(count_sql, str(campaign['company_id']), str(campaign_id))
                return total_count
            
            # Get paginated results
            leads = await conn.fetch(leads_sql, *params)
            
            # Convert to list of dicts
            leads_data = [dict(lead) for lead in leads]
            
            # Determine if there are more results
            has_more = len(leads_data) > limit
            if has_more:
                leads_data = leads_data[:limit]  # Remove the extra item we fetched
            
            return {
                'items': leads_data,
                'has_more': has_more
            }
            
    except Exception as e:
        logger.error(f"Error getting leads with phone for campaign {campaign_id}: {str(e)}")
        raise

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
async def create_upload_task(task_id: UUID, company_id: UUID, user_id: UUID, file_url: str, file_name: str, type: str = 'leads'):
    """Create a new upload task record
    
    Args:
        task_id: UUID of the task
        company_id: UUID of the company
        user_id: UUID of the user
        file_url: Storage URL where the file is stored
        file_name: Original name of the uploaded file
        type: Type of upload task ('leads' or 'do_not_email')
    """
    data = {
        'id': str(task_id),
        'company_id': str(company_id),
        'user_id': str(user_id),
        'file_url': file_url,
        'file_name': file_name,
        'type': type,
        'status': 'pending',
        'created_at': datetime.now().isoformat()
    }
    response = supabase.table('upload_tasks').insert(data).execute()
    return response.data[0] if response.data else None

async def update_task_status(task_id: UUID, status: str = None, result: str = None, celery_task_id: str = None):
    """Update task status, result and celery_task_id"""
    data = {
        'updated_at': datetime.now().isoformat()
    }
    if status is not None:
        data['status'] = status
    if result is not None:
        data['result'] = result
    if celery_task_id is not None:
        data['celery_task_id'] = celery_task_id

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

async def get_companies_with_email_credentials(last_id: Optional[UUID] = None, limit: int = 10):
    """Get all companies that have email credentials configured and are not deleted
    
    Args:
        last_id: Optional UUID of the last company ID from previous page for keyset pagination
        limit: Number of companies to return per page (default: 10)
        
    Returns:
        List of companies with email credentials
    """
    query = supabase.table('companies')\
        .select('*')\
        .not_.is_('account_email', 'null')\
        .not_.is_('account_password', 'null')\
        .eq('deleted', False)\
        .order('id')\
        .limit(limit)
    
    if last_id:
        query = query.gt('id', str(last_id))
    
    response = query.execute()
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

async def get_company_email_logs(company_id: UUID, campaign_id: Optional[UUID] = None, lead_id: Optional[UUID] = None, campaign_run_id: Optional[UUID] = None, status: Optional[str] = None, page_number: int = 1, limit: int = 20):
    """
    Get email logs for a company, optionally filtered by campaign_id, lead_id, campaign_run_id, and status
    
    Args:
        company_id: UUID of the company
        campaign_id: Optional UUID of the campaign to filter by
        lead_id: Optional UUID of the lead to filter by
        campaign_run_id: Optional UUID of the campaign run to filter by
        status: Optional status to filter by ('opened', 'replied', or 'meeting_booked')
        page_number: Page number to fetch (default: 1)
        limit: Number of items per page (default: 20)
        
    Returns:
        Dictionary containing paginated email logs and metadata
    """
    # Build base query
    base_query = supabase.table('email_logs')\
        .select(
            'id, campaign_id, lead_id, sent_at, has_opened, has_replied, has_meeting_booked, ' +
            'campaigns!inner(name, company_id), ' +  # Using inner join to ensure campaign exists
            'leads(name, email)'
        )\
        .eq('campaigns.company_id', str(company_id))  # Filter by company_id in the join
    
    # Add filters if provided
    if campaign_id:
        base_query = base_query.eq('campaign_id', str(campaign_id))
    
    if lead_id:
        base_query = base_query.eq('lead_id', str(lead_id))
    
    if campaign_run_id:
        base_query = base_query.eq('campaign_run_id', str(campaign_run_id))
        
    # Add status filter if provided
    if status:
        if status == 'opened':
            base_query = base_query.eq('has_opened', True)
        elif status == 'replied':
            base_query = base_query.eq('has_replied', True)
        elif status == 'meeting_booked':
            base_query = base_query.eq('has_meeting_booked', True)
    
    # Calculate offset for pagination
    offset = (page_number - 1) * limit
    
    # Execute paginated query
    response = base_query.order('sent_at', desc=True)\
        .range(offset, offset + limit - 1)\
        .execute()
    
    # Get total count
    total_count_query = supabase.table('email_logs')\
        .select('id,campaigns!inner(name, company_id)', count='exact')\
        .eq('campaigns.company_id', str(company_id))
    
    # Add the same filters to the count query
    if campaign_id:
        total_count_query = total_count_query.eq('campaign_id', str(campaign_id))
    
    if lead_id:
        total_count_query = total_count_query.eq('lead_id', str(lead_id))
        
    if campaign_run_id:
        total_count_query = total_count_query.eq('campaign_run_id', str(campaign_run_id))
        
    # Add status filter to count query if provided
    if status:
        if status == 'opened':
            total_count_query = total_count_query.eq('has_opened', True)
        elif status == 'replied':
            total_count_query = total_count_query.eq('has_replied', True)
        elif status == 'meeting_booked':
            total_count_query = total_count_query.eq('has_meeting_booked', True)
    
    count_response = total_count_query.execute()
    total = count_response.count if count_response.count is not None else 0
    
    
    
    
    return {
        'items': response.data,
        'total': total,
        'page': page_number,
        'page_size': limit,
        'total_pages': (total + limit - 1) // limit if total > 0 else 1
    }

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

async def get_email_logs_reminder(
    campaign_id: UUID, 
    days_between_reminders: int, 
    reminder_type: Optional[str] = None,
    last_id: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Fetch email logs that need to be processed for reminders using keyset pagination.
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
        campaign_id: UUID of the campaign
        days_between_reminders: Number of days to wait between reminders
        reminder_type: Optional type of reminder to filter by (e.g., 'r1' for first reminder)
        last_id: Optional ID of the last record from previous page
        limit: Number of items per page (default: 20)
    
    Returns:
        Dictionary containing:
        - items: List of email logs for the current page
        - has_more: Boolean indicating if there are more records
        - last_id: ID of the last record (for next page)
    """
    try:
        # Calculate the date threshold (days_between_reminders days ago from now)
        days_between_reminders_ago = (datetime.now(timezone.utc) - timedelta(days=days_between_reminders)).isoformat()
        
        # Build the base query
        query = supabase.table('email_logs')\
            .select(
                'id, sent_at, has_replied, has_opened, last_reminder_sent, last_reminder_sent_at, lead_id, ' +
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
            
        # Add keyset pagination condition if last_id is provided
        if last_id:
            query = query.gt('id', last_id)
            
        # Add ordering and limit
        response = query.order('id', desc=False).limit(limit + 1).execute()
        
        # Get one extra record to determine if there are more pages
        has_more = len(response.data) > limit
        records = response.data[:limit]  # Remove the extra record from the results
        
        # Flatten the nested structure to match the expected format
        flattened_data = []
        for record in records:
            campaign = record['campaigns']
            company = campaign['companies']
            lead = record['leads']
            
            flattened_record = {
                'email_log_id': record['id'],
                'sent_at': record['sent_at'],
                'has_replied': record['has_replied'],
                'has_opened': record['has_opened'],
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
            
        # Get the last record's id if there are records
        last_record_id = records[-1]['id'] if records else None
            
        return {
            'items': flattened_data,
            'has_more': has_more,
            'last_id': last_record_id
        }
    except Exception as e:
        logger.error(f"Error fetching email logs for reminder: {str(e)}")
        return {
            'items': [],
            'has_more': False,
            'last_id': None
        }

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
        'verified': False,
        'plan_type': 'trial',  # Set default plan type
        'channels_active': {
            'email': True,
            'phone': True,
            'linkedin': False,
            'whatsapp': False
        }
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

async def get_companies_by_user_id(user_id: Union[UUID, str], show_stats: bool = False):
    """
    Get all companies that a user has access to through user_company_profiles,
    including their products (with campaign counts and total calls) and total leads count if show_stats is True
    
    Args:
        user_id: UUID or str of the user
        show_stats: bool, if True includes products (with campaign and call counts) and total leads count in the response
        
    Returns:
        List of companies the user has access to, optionally including array of products (with campaign and call counts) and total leads
    """
    try:
        # Convert to string if UUID object is passed
        user_id_str = str(user_id)
        logger.info(f"Getting companies for user {user_id_str}")
        
        # First, let's check if user has any profiles
        check_response = supabase.table('user_company_profiles')\
            .select('*')\
            .eq('user_id', user_id_str)\
            .execute()
        
        logger.info(f"Found {len(check_response.data)} user_company_profiles for user {user_id_str}")
        
        # Build the select statement based on show_stats
        select_fields = 'role, user_id, companies!inner(id, name, address, industry, website, deleted, created_at'
        if show_stats:
            select_fields += ', products(id, product_name, deleted)'  # Include deleted column for filtering
        select_fields += ')'

        response = supabase.table('user_company_profiles')\
            .select(select_fields)\
            .eq('user_id', user_id_str)\
            .execute()
        
        logger.info(f"Query returned {len(response.data)} companies (including deleted) for user {user_id_str}")

        # Filter out deleted companies
        non_deleted_profiles = []
        for profile in response.data:
            if profile.get('companies') and not profile['companies'].get('deleted', False):
                non_deleted_profiles.append(profile)
            else:
                logger.debug(f"Skipping deleted company for user {user_id_str}")
        
        logger.info(f"After filtering deleted companies: {len(non_deleted_profiles)} companies for user {user_id_str}")

        # If no data, try alternative approach by fetching company roles first
        if not non_deleted_profiles:
            logger.info(f"Trying alternative approach: fetching company roles first for user {user_id_str}")
            company_roles = await get_user_company_roles(user_id)
            logger.info(f"Found {len(company_roles)} company roles for user {user_id_str}")
            
            # Fetch companies individually
            companies = []
            for role in company_roles:
                try:
                    company = await get_company_by_id(UUID(role['company_id']))
                    if company and not company.get('deleted', False):
                        company_data = {
                            'id': company['id'],
                            'name': company['name'],
                            'address': company.get('address'),
                            'industry': company.get('industry'),
                            'website': company.get('website'),
                            'created_at': company.get('created_at'),
                            'role': role['role'],
                            'user_id': user_id_str
                        }
                        
                        # Add products and stats if requested
                        if show_stats:
                            # Get products
                            products_data = await get_products_by_company(UUID(company['id']))
                            products = []
                            for product in products_data:
                                if not product.get('deleted', False):
                                    # Get campaign count for this product
                                    campaigns_response = supabase.table('campaigns')\
                                        .select('id', count='exact')\
                                        .eq('product_id', product['id'])\
                                        .execute()
                                    
                                    products.append({
                                        'id': product['id'],
                                        'name': product['product_name'],
                                        'total_campaigns': campaigns_response.count
                                    })
                            company_data['products'] = products
                            
                            # Get total leads count
                            leads_count_response = supabase.table('leads')\
                                .select('id', count='exact')\
                                .eq('company_id', company['id'])\
                                .execute()
                            company_data['total_leads'] = leads_count_response.count
                        
                        companies.append(company_data)
                except Exception as e:
                    logger.error(f"Error fetching company {role['company_id']}: {str(e)}")
                    continue
            
            logger.info(f"Alternative approach found {len(companies)} companies for user {user_id_str}")
            return companies

        # Transform the response to include products and leads count in the desired format
        companies = []
        for profile in non_deleted_profiles:
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
                        if campaign_ids:  # Only call RPC if there are campaign IDs
                            try:
                                response = supabase.rpc("count_unique_leads_by_campaign", {"campaign_ids": campaign_ids}).execute()
                                # Extract and print the result
                                if response.data is not None:
                                    unique_leads_contacted = response.data
                                else:
                                    unique_leads_contacted = 0
                            except Exception as rpc_error:
                                logger.warning(f"Error calling count_unique_leads_by_campaign RPC: {str(rpc_error)}")
                                unique_leads_contacted = 0
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
    
    except Exception as e:
        logger.error(f"Error in get_companies_by_user_id for user {user_id}: {str(e)}", exc_info=True)
        return []  # Always return a list, even on error

async def get_company_users(company_id: UUID) -> List[dict]:
    """
    Get all users associated with a company through user_company_profiles.
    
    Args:
        company_id: UUID of the company
        
    Returns:
        List of dicts containing user details (name, email, role, user_company_profile_id)
    """
    company = await get_company_by_id(company_id)

    response = supabase.table('user_company_profiles')\
        .select(
            'id,role,user_id,users!inner(name,email)'  # Added id field from user_company_profiles
        )\
        .eq('company_id', str(company_id))\
        .execute()
    
    # Transform the response to match the expected format
    users = []
    for record in response.data:
        user = record['users']

        is_owner = False
        if company['user_id'] == record['user_id']:
            is_owner = True

        users.append({
            'name': user['name'],
            'email': user['email'],
            'role': record['role'],
            'user_company_profile_id': record['id'],  # Added user_company_profile_id
            'is_owner': is_owner
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
    response = supabase.table('leads')\
        .select('*')\
        .eq('email', email)\
        .is_('deleted_at', None)\
        .execute()
    return response.data[0] if response.data else None

async def get_lead_by_phone(phone: str):
    """
    Get a lead by phone number, checking all phone number fields
    """
    fields = ['phone_number', 'mobile', 'direct_phone', 'office_phone']
    
    for field in fields:
        response = supabase.table('leads')\
            .select('*')\
            .eq(field, phone)\
            .is_('deleted_at', None)\
            .execute()
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

async def create_campaign_run(campaign_id: UUID, status: str = "idle", leads_total: int = 0):
    """
    Create a new campaign run record
    
    Args:
        campaign_id: UUID of the campaign
        status: Status of the run ('idle', 'running', 'completed')
        leads_total: Total number of leads available for this run
        
    Returns:
        Dict containing the created campaign run record
    """
    try:
        campaign_run_data = {
            'campaign_id': str(campaign_id),
            'status': status,
            'leads_total': leads_total,
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

async def update_campaign_run_status(campaign_run_id: UUID, status: str, failure_reason: Optional[str] = None):
    """
    Update the status of a campaign run
    
    Args:
        campaign_run_id: UUID of the campaign run
        status: New status ('idle', 'failed', 'running', 'completed')
        failure_reason: Optional reason for failure when status is 'failed'
        
    Returns:
        Dict containing the updated campaign run record or None if update failed
    """
    try:
        if status not in ['idle', 'failed', 'running', 'completed']:
            logger.error(f"Invalid campaign run status: {status}")
            return None
            
        update_data = {'status': status}
        if failure_reason is not None:
            update_data['failure_reason'] = failure_reason
            
        response = supabase.table('campaign_runs').update(update_data).eq('id', str(campaign_run_id)).execute()
        
        if not response.data:
            logger.error(f"Failed to update status for campaign run {campaign_run_id}")
            return None
        
        if status == 'completed':
            await create_or_update_campaign_schedule(campaign_run_id)

        return response.data[0]
    except Exception as e:
        logger.error(f"Error updating campaign run status: {str(e)}")
        return None

async def update_campaign_run_progress(
    campaign_run_id: UUID, 
    leads_total: Optional[int] = None
):
    """
    Update the progress of a campaign run
    
    Args:
        campaign_run_id: UUID of the campaign run
        leads_total: Optional total number of leads for the campaign run
        
    Returns:
        Dict containing the updated campaign run record or None if update failed
    """
    try:
        # Prepare update data
        update_data = {}
            
        # Set total leads if provided
        if leads_total is not None:
            update_data['leads_total'] = leads_total
            
        response = supabase.table('campaign_runs').update(update_data).eq('id', str(campaign_run_id)).execute()
        
        if not response.data:
            logger.error(f"Failed to update progress for campaign run {campaign_run_id}")
            return None
        
        return response.data[0]
    except Exception as e:
        logger.error(f"Error updating campaign run progress: {str(e)}")
        return None

async def get_campaign_runs(company_id: UUID, campaign_id: Optional[UUID] = None, page_number: int = 1, limit: int = 20) -> Dict[str, Any]:
    """
    Get paginated campaign runs for a company, optionally filtered by campaign_id.
    
    Args:
        company_id: UUID of the company
        campaign_id: Optional UUID of the campaign to filter runs by
        page_number: Page number to fetch (default: 1)
        limit: Number of items per page (default: 20)
        
    Returns:
        Dictionary containing paginated campaign runs and metadata
    """
    try:
        if campaign_id:
            # If campaign_id is provided, directly filter campaign_runs and join with campaigns for the name
            base_query = supabase.table('campaign_runs').select(
                '*,campaigns!inner(name,type)'
            ).eq('campaign_id', str(campaign_id))
            
            # Get total count
            total_count_query = supabase.table('campaign_runs').select(
                'id', count='exact'
            ).eq('campaign_id', str(campaign_id))
        else:
            # If only company_id is provided, join with campaigns to get all runs for the company
            base_query = supabase.table('campaign_runs').select(
                '*,campaigns!inner(name,type,company_id)'
            ).eq('campaigns.company_id', str(company_id))
            
            # Get total count
            total_count_query = supabase.table('campaign_runs').select(
                'id,campaigns!inner(name,type,company_id)', count='exact'
            ).eq('campaigns.company_id', str(company_id))
            
        # Get total count
        count_response = total_count_query.execute()
        total = count_response.count if count_response.count is not None else 0
        
        # Calculate offset from page_number
        offset = (page_number - 1) * limit
            
        # Execute query and sort by run_at in descending order
        response = base_query.order('run_at', desc=True).range(offset, offset + limit - 1).execute()
        
        # Get leads_processed count for each campaign run
        campaign_runs_with_counts = []
        for run in response.data if response.data else []:
            campaign_type = run['campaigns']['type']
            
            # Determine which queue table to use based on campaign type
            queue_table = None
            if campaign_type == 'call':
                queue_table = 'call_queue'
            elif campaign_type in ['email', 'email_and_call']:
                queue_table = 'email_queue'
                
            if queue_table:
                # Get count of processed leads from appropriate queue
                processed_count_query = supabase.table(queue_table).select(
                    'id', count='exact'
                ).eq('campaign_run_id', str(run['id'])).in_('status', ['failed', 'sent', 'skipped'])
                
                processed_count_response = processed_count_query.execute()
                leads_processed = processed_count_response.count if processed_count_response.count is not None else 0
                
                # Get count of failed items
                failed_count_query = supabase.table(queue_table).select(
                    'id', count='exact'
                ).eq('campaign_run_id', str(run['id'])).eq('status', 'failed')
                
                failed_count_response = failed_count_query.execute()
                failed_count = failed_count_response.count if failed_count_response.count is not None else 0
                
                # Add leads_processed and has_failed_items to the run data
                run['leads_processed'] = leads_processed
                run['has_failed_items'] = failed_count > 0
            else:
                # Handle unknown campaign types
                run['leads_processed'] = 0
                run['has_failed_items'] = False
                
            campaign_runs_with_counts.append(run)
        
        return {
            'items': campaign_runs_with_counts,
            'total': total,
            'page': page_number,
            'page_size': limit,
            'total_pages': (total + limit - 1) // limit if total > 0 else 1
        }
        
    except Exception as e:
        logger.error(f"Error fetching campaign runs: {str(e)}")
        return {
            'items': [],
            'total': 0,
            'page': page_number,
            'page_size': limit,
            'total_pages': 0
        }

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
    email_log_id: Optional[UUID] = None,
    message_id: Optional[str] = None,
    reference_ids: Optional[str] = None
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
        'email_log_id': str(email_log_id) if email_log_id else None,
        'message_id': message_id,
        'reference_ids': reference_ids
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
                'max_emails_per_hour': 300,
                'max_emails_per_day': 300,
                'enabled': True
            }
    except Exception as e:
        logger.error(f"Error getting email throttle settings: {str(e)}")
        # Return default settings on error
        return {
            'max_emails_per_hour': 300,
            'max_emails_per_day': 300,
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
            .is_('email_log_id', 'null')\
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
            .update({"last_processed_bounce_uid": uid})\
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
                    await create_skipped_row_record(
                        upload_task_id=task_id,
                        category="missing_email",
                        row_data=row
                    )
                    skipped_count += 1
                    continue

                # Validate email format
                try:
                    # Validate and normalize the email
                    email_info = validate_email(email, check_deliverability=False)
                    email = email_info.normalized
                except EmailNotValidError as e:
                    logger.info(f"Skipping record - invalid email format: {email}")
                    logger.info(f"Email validation error: {str(e)}")
                    await create_skipped_row_record(
                        upload_task_id=task_id,
                        category="invalid_email",
                        row_data=row
                    )
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
                    await create_skipped_row_record(
                        upload_task_id=task_id,
                        category="do_not_email_creation_error",
                        row_data=row
                    )
                    skipped_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing row: {str(e)}")
                logger.error(f"Row data that failed: {row}")
                await create_skipped_row_record(
                    upload_task_id=task_id,
                    category="processing_error",
                    row_data=row
                )
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

async def get_email_queues_by_campaign_run(campaign_run_id: UUID, page_number: int = 1, limit: int = 20, status: Optional[str] = None):
    """
    Get paginated email queues for a specific campaign run
    
    Args:
        campaign_run_id: UUID of the campaign run
        page_number: Page number to fetch (default: 1)
        limit: Number of items per page (default: 20)
        status: Filter by email status (optional)
        
    Returns:
        Dictionary containing paginated email queues and metadata
    """
    # Modify the base query to select fields from email_queue and join with leads
    base_query = supabase.table('email_queue')\
        .select('*, leads!inner(name, email)')\
        .eq('campaign_run_id', str(campaign_run_id))

    # Add status filter if provided
    if status:
        base_query = base_query.eq('status', status)

    # Get total count with the same filters
    total_count_query = supabase.table('email_queue')\
        .select('id', count='exact')\
        .eq('campaign_run_id', str(campaign_run_id))
        
    # Add status filter to count query if provided
    if status:
        total_count_query = total_count_query.eq('status', status)
        
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

async def get_active_campaign_runs_count(campaign_id: UUID) -> int:
    """
    Get count of campaign runs with status 'running' or 'idle' for a specific campaign
    
    Args:
        campaign_id: UUID of the campaign
    Returns:
        Count of active campaign runs
    """
    try:
        response = supabase.table('campaign_runs')\
            .select('id', count='exact')\
            .eq('campaign_id', str(campaign_id))\
            .in_('status', ['running', 'idle'])\
            .execute()
            
        return response.count or 0
    except Exception as e:
        logger.error(f"Error getting active campaign runs count: {str(e)}")
        return 0

async def get_campaigns(
    campaign_types: Optional[List[str]] = None, 
    page_number: int = 1, 
    limit: int = 20,
    reminder_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get paginated campaigns, optionally filtered by multiple types and reminder type
    
    Args:
        campaign_types: Optional list of types to filter (['email', 'call'], etc.)
        page_number: Page number to fetch (default: 1)
        limit: Number of items per page (default: 20)
        reminder_type: Type of reminder to filter ('email' or 'phone')
        
    Returns:
        Dictionary containing:
        - items: List of campaigns for the current page
        - total: Total number of campaigns
        - page: Current page number
        - page_size: Number of items per page
        - total_pages: Total number of pages
    """
    try:
        # Build base query for counting total records
        count_query = supabase.table('campaigns').select('id', count='exact')
        
        # Add reminder type filter if provided
        if reminder_type == 'email':
            count_query = count_query.gt('number_of_reminders', 0)
        elif reminder_type == 'phone':
            count_query = count_query.gt('phone_number_of_reminders', 0)
        
        # Add type filter to count query if provided
        if campaign_types:
            count_query = count_query.in_('type', campaign_types)
            
        # Get total count
        count_response = count_query.execute()
        total = count_response.count if count_response.count is not None else 0
        
        # Calculate offset from page_number
        offset = (page_number - 1) * limit
        
        # Build query for fetching paginated data
        query = supabase.table('campaigns').select('*')
        
        # Add reminder type filter if provided
        if reminder_type == 'email':
            query = query.gt('number_of_reminders', 0)
        elif reminder_type == 'phone':
            query = query.gt('phone_number_of_reminders', 0)
        
        # Add type filter if provided
        if campaign_types:
            query = query.in_('type', campaign_types)
            
        # Add pagination
        response = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        return {
            'items': response.data,
            'total': total,
            'page': page_number,
            'page_size': limit,
            'total_pages': (total + limit - 1) // limit if total > 0 else 1
        }
    except Exception as e:
        logger.error(f"Error fetching campaigns: {str(e)}")
        return {
            'items': [],
            'total': 0,
            'page': page_number,
            'page_size': limit,
            'total_pages': 0
        }

async def get_call_logs_reminder(
    campaign_id: UUID, 
    days_between_reminders: int, 
    reminder_type: Optional[str] = None,
    last_id: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Fetch call logs that need to be processed for reminders using keyset pagination.
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
        campaign_id: UUID of the campaign
        days_between_reminders: Number of days to wait between reminders
        reminder_type: Optional type of reminder to filter by (e.g., 'r1' for first reminder)
        last_id: Optional ID of the last record from previous page
        limit: Number of items per page (default: 20)
    
    Returns:
        Dictionary containing:
        - items: List of call logs for the current page
        - has_more: Boolean indicating if there are more records
        - last_id: ID of the last record (for next page)
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
            
        # Add keyset pagination condition if last_id is provided
        if last_id:
            query = query.gt('id', last_id)
            
        # Add ordering and limit
        response = query.order('id', desc=False).limit(limit + 1).execute()
        
        # Get one extra record to determine if there are more pages
        has_more = len(response.data) > limit
        records = response.data[:limit]  # Remove the extra record from the results
        
        # Flatten the nested structure to match the expected format
        flattened_data = []
        for record in records:
            campaign = record['campaigns']
            company = campaign['companies']
            lead = record['leads']
            
            flattened_record = {
                'call_log_id': record['id'],
                'created_at': record['created_at'],
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
            
        # Get the last record's id if there are records
        last_record_id = records[-1]['id'] if records else None
            
        return {
            'items': flattened_data,
            'has_more': has_more,
            'last_id': last_record_id
        }
    except Exception as e:
        logger.error(f"Error fetching call logs for reminder: {str(e)}")
        return {
            'items': [],
            'has_more': False,
            'last_id': None
        }

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
    call_log_id: Optional[UUID] = None
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
        work_time_start: Start time of the work day
        work_time_end: End time of the work day
        
    Returns:
        The created queue item
    """
    from src.utils.llm import fetch_timezone,convert_to_utc

    if call_log_id is None:
        # First check if a record already exists
        existing_record = await check_existing_call_queue_record(
            company_id=company_id,
            campaign_id=campaign_id,
            campaign_run_id=campaign_run_id,
            lead_id=lead_id
        )
        
        if existing_record:
            logger.info(f"Call queue record already exists for lead {lead_id} in campaign {campaign_id}")
            return None

    lead = await get_lead_by_id(lead_id)
    work_time_start = None
    work_time_end = None

    try:
        timezone = await fetch_timezone(lead['phone_number'])
        if timezone:
            start_time = convert_to_utc(timezone, '09:00')
            end_time = convert_to_utc(timezone, '17:00')
            # Convert time objects to string format HH:MM:SS
            work_time_start = start_time.strftime('%H:%M:%S') if start_time else None
            work_time_end = end_time.strftime('%H:%M:%S') if end_time else None
    except Exception as e:
        logger.error(f"Error fetching timezone for lead {lead_id}: {str(e)}")
        # Continue with None values for work times

    queue_data = {
        'company_id': str(company_id),
        'campaign_id': str(campaign_id),
        'campaign_run_id': str(campaign_run_id),
        'lead_id': str(lead_id),
        'status': 'pending',
        'priority': priority,
        'retry_count': 0,
        'max_retries': 3,
        'call_script': call_script,
        'call_log_id': str(call_log_id) if call_log_id else None,
        'work_time_start': work_time_start,
        'work_time_end': work_time_end
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
    Get the next batch of calls to process for a company using a database function
    
    Args:
        company_id: UUID of the company
        limit: Maximum number of calls to retrieve
        
    Returns:
        List of call queue items to process
    """
    try:
        response = supabase.rpc(
            'get_next_calls_to_process',
            {
                'p_company_id': str(company_id),
                'p_limit': limit
            }
        ).execute()
            
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
            .is_('call_log_id', 'null')\
            .execute()
            
        return response.count
    except Exception as e:
        logger.error(f"Error getting pending calls count: {str(e)}")
        return 0

async def get_call_queues_by_campaign_run(campaign_run_id: UUID, page_number: int = 1, limit: int = 20, status: Optional[str] = None):
    """
    Get paginated call queues for a specific campaign run
    
    Args:
        campaign_run_id: UUID of the campaign run
        page_number: Page number to fetch (default: 1)
        limit: Number of items per page (default: 20)
        status: Filter by status (sent, failed, or None for all)
        
    Returns:
        Dictionary containing paginated call queues and metadata
    """
    # Modify the base query to select fields from call_queue and join with leads
    base_query = supabase.table('call_queue')\
        .select('*, leads!inner(name, phone_number)')\
        .eq('campaign_run_id', str(campaign_run_id))

    # Add status filter if provided
    if status:
        base_query = base_query.eq('status', status)

    # Get total count with the same filters
    total_count_query = supabase.table('call_queue')\
        .select('id', count='exact')\
        .eq('campaign_run_id', str(campaign_run_id))
    
    # Add status filter to count query if provided
    if status:
        total_count_query = total_count_query.eq('status', status)

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

async def get_call_by_bland_id(bland_call_id: str) -> Optional[dict]:
    """Get a call record by its Bland call ID."""
    response = supabase.table('calls').select('*').eq('bland_call_id', bland_call_id).execute()
    return response.data[0] if response.data else None

async def check_call_queue_exists(company_id: UUID, campaign_id: UUID, campaign_run_id: UUID, lead_id: UUID) -> Optional[dict]:
    """Check if a record exists in call_queue table with the given parameters."""
    response = supabase.table('call_queue').select('*').eq('company_id', str(company_id)).eq('campaign_id', str(campaign_id)).eq('campaign_run_id', str(campaign_run_id)).eq('lead_id', str(lead_id)).execute()
    return response.data[0] if response.data else None

async def get_processed_leads_count(campaign_run_id: UUID, campaign_type: str = 'email') -> int:
    """
    Get the count of processed leads (failed or sent) for a campaign run based on campaign type
    
    Args:
        campaign_run_id: UUID of the campaign run
        campaign_type: Type of campaign ('email' or 'call')
        
    Returns:
        int: Count of processed leads
        
    Raises:
        ValueError: If campaign_type is not 'email' or 'call'
    """
    try:
        # Determine which queue table to use based on campaign type
        if campaign_type == 'call':
            queue_table = 'call_queue'
        elif campaign_type == 'email':
            queue_table = 'email_queue'
        else:
            raise ValueError(f"Invalid campaign type: {campaign_type}. Must be 'email' or 'call'")
        
        # Get count from the appropriate queue
        response = supabase.from_(queue_table)\
            .select('*', count='exact')\
            .eq('campaign_run_id', str(campaign_run_id))\
            .in_('status', ['failed', 'sent', 'skipped'])\
            .execute()
            
        return response.count if response.count is not None else 0
        
    except Exception as e:
        logger.error(f"Error getting processed leads count: {str(e)}")
        return 0

async def check_existing_email_log_record(
    campaign_id: UUID,
    lead_id: UUID,
    campaign_run_id: UUID
) -> bool:
    """
    Check if an email log record exists for the given campaign, lead, and campaign run.
    
    Args:
        campaign_id: UUID of the campaign
        lead_id: UUID of the lead
        campaign_run_id: UUID of the campaign run
        
    Returns:
        bool: True if a record exists, False otherwise
    """
    try:
        response = supabase.table('email_logs')\
            .select('id')\
            .eq('campaign_id', str(campaign_id))\
            .eq('lead_id', str(lead_id))\
            .eq('campaign_run_id', str(campaign_run_id))\
            .execute()
            
        return len(response.data) > 0
    except Exception as e:
        logger.error(f"Error checking existing email log record: {str(e)}")
        return False

async def get_call_queue_item(queue_id: UUID) -> Optional[dict]:
    """
    Get a call queue item by its ID
    
    Args:
        queue_id: UUID of the call queue item
        
    Returns:
        Call queue item if found, None otherwise
    """
    try:
        response = supabase.table('call_queue')\
            .select('*')\
            .eq('id', str(queue_id))\
            .execute()
            
        if not response.data:
            return None
            
        return response.data[0]
    except Exception as e:
        logger.error(f"Error getting call queue item: {str(e)}")
        return None

async def update_company_custom_calendar(company_id: UUID, custom_calendar_link: str):
    """
    Update custom calendar link for a company
    
    Args:
        company_id: UUID of the company
        custom_calendar_link: New calendar link to set
        
    Returns:
        Updated company data or None if update failed
    """
    try:
        response = supabase.table('companies')\
            .update({'custom_calendar_link': custom_calendar_link})\
            .eq('id', str(company_id))\
            .execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating company custom calendar link: {str(e)}")
        return None

async def create_or_update_campaign_schedule(campaign_run_id: UUID) -> List[dict]:
    """
    Create or update campaign message schedule entries based on existing records.
    
    Args:
        campaign_run_id: UUID of the campaign run
        
    Returns:
        List of created schedule entries
    """
    try:
        current_date = datetime.now(timezone.utc).date()
        current_date_str = datetime.combine(current_date, datetime.min.time()).isoformat()
        
        # Check if record exists for current date
        existing_record = supabase.table('campaign_message_schedule')\
            .select('id')\
            .eq('campaign_run_id', str(campaign_run_id))\
            .eq('scheduled_for', current_date_str)\
            .execute()
            
        created_records = []
        
        if not existing_record.data:
            # No record exists for current date, create two records
            # First record: current date
            first_record = supabase.table('campaign_message_schedule')\
                .insert({
                    'campaign_run_id': str(campaign_run_id),
                    'status': 'pending',
                    'scheduled_for': current_date_str,
                    'data_fetch_date': (datetime.combine(current_date - timedelta(days=1), datetime.min.time())).isoformat()
                })\
                .execute()
            created_records.extend(first_record.data)
            
            # Second record: next day
            second_record = supabase.table('campaign_message_schedule')\
                .insert({
                    'campaign_run_id': str(campaign_run_id),
                    'status': 'pending',
                    'scheduled_for': (datetime.combine(current_date + timedelta(days=1), datetime.min.time())).isoformat(),
                    'data_fetch_date': current_date_str
                })\
                .execute()
            created_records.extend(second_record.data)
        else:
            # Record exists for current date, only create one record for next day
            next_record = supabase.table('campaign_message_schedule')\
                .insert({
                    'campaign_run_id': str(campaign_run_id),
                    'status': 'pending',
                    'scheduled_for': (datetime.combine(current_date + timedelta(days=1), datetime.min.time())).isoformat(),
                    'data_fetch_date': current_date_str
                })\
                .execute()
            created_records.extend(next_record.data)
            
        return created_records
    except Exception as e:
        logger.error(f"Error creating/updating campaign schedule for run {campaign_run_id}: {str(e)}")
        raise

async def get_email_sent_count(campaign_run_id: UUID, date: Union[str, datetime], has_opened: Optional[bool] = None, has_replied: Optional[bool] = None, has_meeting_booked: Optional[bool] = None) -> int:
    """
    Get count of email sent for a specific date and campaign run ID.
    
    Args:
        campaign_run_id: UUID of the campaign run
        date: The date to count emails for (can be string in ISO format or datetime object)
        has_opened: Optional filter for opened emails (True/False)
        has_replied: Optional filter for replied emails (True/False)
        has_meeting_booked: Optional filter for emails that resulted in meetings (True/False)
        
    Returns:
        Number of email sent for the specified date and campaign run
    """
    try:
        # Convert string date to datetime if needed
        if isinstance(date, str):
            try:
                # Try parsing ISO format
                parsed_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                date = parsed_date.date()
            except ValueError as e:
                logger.error(f"Invalid date format. Expected ISO format, got: {date}")
                return 0
        elif isinstance(date, datetime):
            date = date.date()
            
        # Convert date to start and end of day in ISO format
        start_of_day = datetime.combine(date, datetime.min.time()).isoformat()
        end_of_day = datetime.combine(date, datetime.max.time()).isoformat()
        
        logger.info(f"Counting emails for date range: {start_of_day} to {end_of_day}")
        
        # Build base query
        query = supabase.table('email_logs')\
            .select('id', count='exact')\
            .eq('campaign_run_id', str(campaign_run_id))\
            .gte('created_at', start_of_day)\
            .lte('created_at', end_of_day)
            
        # Add has_opened filter only if explicitly set
        if has_opened is not None:
            query = query.eq('has_opened', has_opened)
        
        # Add has_replied filter only if explicitly set
        if has_replied is not None:
            query = query.eq('has_replied', has_replied)

        # Add has_meeting_booked filter only if explicitly set
        if has_meeting_booked is not None:
            query = query.eq('has_meeting_booked', has_meeting_booked)

        response = query.execute()
        return response.count if response.count is not None else 0
    except Exception as e:
        logger.error(f"Error getting email sent count: {str(e)}")
        return 0

async def get_call_sent_count(campaign_run_id: UUID, date: Union[str, datetime], has_meeting_booked: Optional[bool] = None) -> int:
    """
    Get count of successful calls (where failure_reason is null) for a specific date and campaign run ID.
    
    Args:
        campaign_run_id: UUID of the campaign run
        date: The date to count calls for (can be string in ISO format or datetime object)
        has_meeting_booked: Optional filter for meeting booked calls (True/False)
        
    Returns:
        Number of successful calls sent for the specified date and campaign run
    """
    try:
        # Convert string date to datetime if needed
        if isinstance(date, str):
            try:
                # Try parsing ISO format
                parsed_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                date = parsed_date.date()
            except ValueError as e:
                logger.error(f"Invalid date format. Expected ISO format, got: {date}")
                return 0
        elif isinstance(date, datetime):
            date = date.date()
            
        # Convert date to start and end of day in ISO format
        start_of_day = datetime.combine(date, datetime.min.time()).isoformat()
        end_of_day = datetime.combine(date, datetime.max.time()).isoformat()
        
        logger.info(f"Counting calls for date range: {start_of_day} to {end_of_day}")
        
        # Build base query
        query = supabase.table('calls')\
            .select('id', count='exact')\
            .eq('campaign_run_id', str(campaign_run_id))\
            .gte('created_at', start_of_day)\
            .lte('created_at', end_of_day)\
            .is_('failure_reason', 'null')  # Only count successful calls

        # Add has_meeting_booked filter only if explicitly set
        if has_meeting_booked is not None:
            query = query.eq('has_meeting_booked', has_meeting_booked)

        response = query.execute()
        return response.count if response.count is not None else 0
    except Exception as e:
        logger.error(f"Error getting call sent count: {str(e)}")
        return 0

async def get_lead_details_for_email_interactions(
    campaign_run_id: UUID,
    date: Union[str, datetime],
    limit: int = 3
) -> List[dict]:
    """
    Get lead details for emails that were either opened or replied to on a specific date.
    
    Args:
        campaign_run_id: UUID of the campaign run
        date: The date to check for interactions (can be string 'YYYY-MM-DD' or ISO format, or datetime object)
        limit: Maximum number of records to return (default: 3)
        
    Returns:
        List of lead details including name, company, and job title
    """
    try:
        # Convert string date to datetime if needed
        if isinstance(date, str):
            try:
                # Try parsing ISO format first
                parsed_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                date = parsed_date.date()
            except ValueError:
                try:
                    # Try YYYY-MM-DD format as fallback
                    date = datetime.strptime(date, '%Y-%m-%d').date()
                except ValueError as e:
                    logger.error(f"Invalid date format. Expected 'YYYY-MM-DD' or ISO format, got: {date}")
                    return []
        elif isinstance(date, datetime):
            date = date.date()
            
        # Convert date to start and end of day in ISO format
        start_of_day = datetime.combine(date, datetime.min.time()).isoformat()
        end_of_day = datetime.combine(date, datetime.max.time()).isoformat()
        
        logger.info(f"Fetching lead details for date range: {start_of_day} to {end_of_day}")
        
        response = supabase.table('email_logs')\
            .select(
                'leads(name, company, job_title)'
            )\
            .eq('campaign_run_id', str(campaign_run_id))\
            .gte('created_at', start_of_day)\
            .lte('created_at', end_of_day)\
            .or_('has_replied.eq.true,has_opened.eq.true')\
            .limit(limit)\
            .execute()
            
        # Extract and flatten lead details from the response
        leads = []
        for item in response.data:
            if item.get('leads'):
                leads.append({
                    'name': item['leads']['name'],
                    'company': item['leads']['company'],
                    'job_title': item['leads']['job_title']
                })
                
        return leads
    except Exception as e:
        logger.error(f"Error getting lead details for email interactions: {str(e)}")
        return []

async def update_campaign_schedule_status(schedule_id: UUID, status: str = "sent") -> bool:
    """
    Update the status of a campaign message schedule record.
    
    Args:
        schedule_id: UUID of the schedule record
        status: New status to set (default: "sent")
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        response = supabase.table('campaign_message_schedule')\
            .update({
                'status': status
            })\
            .eq('id', str(schedule_id))\
            .execute()
            
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error updating campaign schedule status: {str(e)}")
        return False

async def get_pending_scheduled_campaigns(last_id: Optional[UUID] = None, limit: int = 50) -> List[Dict]:
    """
    Get campaigns that are scheduled to run and haven't been auto-triggered yet.
    Uses keyset pagination for efficient querying of large datasets.
    
    Args:
        last_id: UUID of the last campaign from previous page (for pagination)
        limit: Maximum number of records to return
        
    Returns:
        List of campaign dictionaries with id, name, scheduled_at, and company info
    """
    try:
        # Get current timestamp in UTC
        current_time = datetime.now(timezone.utc)
        
        # Build base query
        query = supabase.from_('campaigns')\
            .select('id, name, type, scheduled_at, company_id, companies!inner(id, name, deleted)')\
            .eq('auto_run_triggered', False)\
            .eq('companies.deleted', False)\
            .lte('scheduled_at', current_time.isoformat())\
            .order('id')\
            .limit(limit)
            
        # Add keyset pagination condition if last_id is provided
        if last_id:
            query = query.gt('id', str(last_id))
            
        response = query.execute()
        return response.data
            
    except Exception as e:
        logger.error(f"Error fetching pending scheduled campaigns: {str(e)}")
        return []
    
async def mark_campaign_as_triggered(campaign_id: UUID) -> bool:
    """
    Mark a campaign as auto-triggered.
    
    Args:
        campaign_id: UUID of the campaign to mark as triggered
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        response = supabase.table('campaigns').update({
            'auto_run_triggered': True
        }).eq('id', str(campaign_id)).execute()
        
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error marking campaign {campaign_id} as triggered: {str(e)}")
        return False

async def get_campaign_lead_count(campaign: dict) -> int:
    """
    Get the total number of leads for a campaign based on its type.
    
    Args:
        campaign: Campaign dictionary containing type and id
        
    Returns:
        int: Total number of leads
    """
    try:
        if campaign['type'] in ['email', 'email_and_call']:
            return await get_leads_with_email(campaign['id'], count=True)
        elif campaign['type'] == 'call':
            return await get_leads_with_phone(campaign['id'], count=True)
        return 0
    except Exception as e:
        logger.error(f"Error getting lead count for campaign {campaign['id']}: {str(e)}")
        return 0

async def check_account_email_exists_in_other_companies(company_id: UUID, account_email: str, user_id: UUID) -> bool:
    """
    Check if the given account_email exists in other non-deleted companies for the user
    
    Args:
        company_id: UUID of the current company to exclude from check
        account_email: Email address to check
        user_id: UUID of the current user
        
    Returns:
        bool: True if email exists in other companies, False otherwise
    """
    try:
        # Get all companies for the user where the account_email exists
        response = supabase.table('companies')\
            .select('id')\
            .neq('id', str(company_id))\
            .eq('account_email', account_email)\
            .eq('deleted', False)\
            .execute()

        if not response.data:
            return False

        # Check if any of these companies belong to the user
        user_companies = await get_companies_by_user_id(user_id)
        user_company_ids = {str(company['id']) for company in user_companies}
        
        # Check if any of the found companies belong to the user
        for company in response.data:
            if str(company['id']) in user_company_ids:
                return True
                
        return False
        
    except Exception as e:
        logger.error(f"Error checking account email existence: {str(e)}")
        return False

async def check_user_access_status(user_id: UUID) -> tuple[bool, str]:
    """
    Check if a user has either an active subscription or a valid trial.
    
    Args:
        user_id (UUID): The ID of the user to check
        
    Returns:
        tuple[bool, str]: A tuple containing (has_access, message)
                         has_access: True if user has either active subscription or valid trial
                         message: Empty string if access granted, otherwise contains reason for no access
    """
    try:
        # Get user info with all required fields
        user_query = supabase.table('users')\
            .select('subscription_id, subscription_status, plan_type, created_at')\
            .eq('id', str(user_id))\
            .single()
        user = user_query.execute()
        
        if not user.data:
            return (False, "User not found")
            
        # First check for active subscription
        if user.data.get('subscription_id') and user.data.get('subscription_status') == 'active':
            return (True, "")  # Active subscription exists
            
        # If no active subscription, check trial status
        if user.data['plan_type'] != 'trial':
            return (False, "No active subscription or trial found")
            
        # Check if trial has expired (7 days from creation)
        created_at = parser.parse(user.data['created_at'])
        trial_expiry = created_at + timedelta(days=7)
        
        if datetime.now(timezone.utc) > trial_expiry:
            return (False, "Your trial plan has expired. Please upgrade to a paid plan to continue using the platform.")
            
        return (True, "")  # Trial is still valid
        
    except Exception as e:
        logger.error(f"Error checking user access status: {str(e)}")
        return (False, f"Error checking user access status: {str(e)}")

async def check_user_campaign_access(user_id: UUID, campaign_type: str) -> tuple[bool, str]:
    """
    Check if a user has access to create a campaign of the specified type based on their subscription and active channels.
    
    Args:
        user_id (UUID): The ID of the user to check
        campaign_type (str): The type of campaign being created ('email', 'call', or 'email_and_call')
        
    Returns:
        tuple[bool, str]: A tuple containing (has_access, error_message)
                         has_access: True if user can create the campaign type
                         error_message: Empty string if access granted, otherwise contains reason for denial
    """
    try:
        # Get user details with subscription and channels
        user_query = supabase.table('users')\
            .select('subscription_id, subscription_status, channels_active')\
            .eq('id', str(user_id))\
            .single()
        user = user_query.execute()
        
        if not user.data:
            return (False, "User not found")
            
        # Check if user has an active subscription
        if user.data.get('subscription_id'):
            if user.data.get('subscription_status') != 'active':
                return (False, "Your subscription is not active. Please upgrade your plan.")
                
            # Get active channels
            channels = user.data.get('channels_active', {})
            
            # Validate campaign type based on purchased channels
            if campaign_type == 'email' and not channels.get('email'):
                return (False, "Email channel is not active in your subscription. Please upgrade your plan to include email campaigns.")
            elif campaign_type == 'call' and not channels.get('phone'):
                return (False, "Phone channel is not active in your subscription. Please upgrade your plan to include call campaigns.")
            elif campaign_type == 'email_and_call' and (not channels.get('email') or not channels.get('phone')):
                return (False, "Both email and phone channels are required for this campaign type. Please upgrade your plan to include both channels.")
                
        # If no subscription or all checks pass, allow access
        return (True, "")
        
    except Exception as e:
        logger.error(f"Error checking user campaign access: {str(e)}")
        return (False, f"Error checking campaign access: {str(e)}")

async def create_booked_meeting(
    user_id: UUID,
    company_id: UUID,
    item_id: UUID,
    type: str,
    reported_to_stripe: bool = False
) -> Dict:
    """
    Create a record in the booked_meetings table to track a booked meeting.
    
    Args:
        user_id: UUID of the user who owns the company
        company_id: UUID of the company
        item_id: UUID of either email_logs.id or calls.id
        type: Type of meeting booking ('email' or 'call')
        reported_to_stripe: Whether the meeting has been reported to Stripe
        
    Returns:
        Dict containing the created booked meeting record
    """
    try:
        response = supabase.table('booked_meetings').insert({
            'user_id': str(user_id),
            'company_id': str(company_id),
            'item_id': str(item_id),
            'type': type,
            'reported_to_stripe': reported_to_stripe
        }).execute()
        
        if not response.data:
            raise Exception("Failed to create booked meeting record")
            
        return response.data[0]
        
    except Exception as e:
        logger.error(f"Error creating booked meeting record: {str(e)}")
        raise

async def get_booked_meetings_count(user_id: str, start_date: datetime, end_date: datetime) -> int:
    """
    Get the count of booked meetings for a user within a specific date range.
    
    Args:
        user_id: The ID of the user
        start_date: Start date of the billing period
        end_date: End date of the billing period
        
    Returns:
        int: Count of booked meetings
    """
    try:
        response = supabase.table('booked_meetings').select('id', count='exact').eq('user_id', user_id).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).execute()
        return response.count if response.count is not None else 0
    except Exception as e:
        logger.error(f"Error getting booked meetings count: {str(e)}")
        return 0

async def update_user_subscription_cancellation(user_id: UUID, canceled_at: datetime) -> Optional[dict]:
    """
    Update user record when subscription is canceled
    
    Args:
        user_id: UUID of the user
        canceled_at: Timestamp when the subscription was canceled
        
    Returns:
        Updated user record if successful, None otherwise
    """
    try:
        response = supabase.table('users').update({
            "subscription_status": "canceled",
            "subscription_canceled_at": canceled_at.isoformat()
        }).eq('id', str(user_id)).execute()
        
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating user subscription cancellation: {str(e)}")
        return None

async def update_user_subscription_details(subscription_id: str, plan_type: str, lead_tier: int, channels_active: Dict) -> Dict:
    """
    Update user's subscription details in the database
    
    Args:
        subscription_id: Stripe subscription ID
        plan_type: New plan type (fixed or performance)
        lead_tier: New lead tier
        channels_active: Dict of active channels
        
    Returns:
        Updated user record
    """
    try:
        # Get user by subscription ID
        response = supabase.table("users").select("id").eq("subscription_id", subscription_id).execute()
        if not response.data:
            raise Exception(f"No user found with subscription ID: {subscription_id}")
        
        user_id = response.data[0]["id"]
        
        # Update user's subscription details
        update_data = {
            "plan_type": plan_type,
            "lead_tier": lead_tier,
            "channels_active": channels_active
        }
        
        response = supabase.table("users").update(update_data).eq("id", user_id).execute()
        return response.data[0] if response.data else None
        
    except Exception as e:
        logger.error(f"Error updating user subscription details: {str(e)}")
        raise

async def has_pending_upload_tasks(company_id: UUID) -> bool:
    """
    Check if a company has any pending or processing upload tasks using count query.
    
    Args:
        company_id: UUID of the company to check
        
    Returns:
        bool: True if there are pending/processing tasks, False otherwise
    """
    try:
        response = supabase.table('upload_tasks')\
            .select('count', count='exact')\
            .eq('company_id', str(company_id))\
            .in_('status', ['pending', 'processing'])\
            .execute()
            
        count = response.count if hasattr(response, 'count') else 0
        return count > 0
    except Exception as e:
        logger.error(f"Error checking pending upload tasks: {str(e)}")
        return False

async def find_existing_leads(email: str, phone: Optional[str], company_id: UUID) -> List[Dict]:
    """
    Find existing leads in a company that match either the email or phone number.
    
    Args:
        email: Email address to search for
        phone: Phone number to search for
        company_id: UUID of the company to search in
        
    Returns:
        List[Dict]: List of matching leads, if any
    """
    try:
        # Build query to find leads with matching email or phone
        query = supabase.table('leads')\
            .select('id, email, phone_number, name')\
            .eq('company_id', str(company_id))\
            .is_('deleted_at', None)
        
        # If phone is provided, check for email OR phone match
        if phone:
            response = query.or_(f'email.eq.{email},phone_number.eq.{phone}').execute()
        else:
            # If phone is not provided, only check for email match
            response = query.eq('email', email).execute()
            
        return response.data if response.data else []
        
    except Exception as e:
        logger.error(f"Error finding existing leads: {str(e)}")
        return []

async def create_skipped_row_record(
    upload_task_id: UUID,
    category: str,
    row_data: dict
):
    """
    Create a record in the skipped_rows table for a row that was skipped during upload.
    
    Args:
        upload_task_id (UUID): ID of the upload task
        category (str): Category/reason for skipping the row
        row_data (dict): Original row data that was skipped
        
    Returns:
        dict: Created skipped row record
    """
    try:
        result = supabase.table('skipped_rows').insert({
            'upload_task_id': str(upload_task_id),
            'category': category,
            'row_data': json.dumps(row_data)  # Convert dict to JSON string
        }).execute()

        if len(result.data) > 0:
            return result.data[0]
        else:
            return None
    except Exception as e:
        logger.error(f"Error creating skipped row record: {str(e)}")
        return None
async def get_upload_tasks_by_company(
    company_id: UUID,
    page_number: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Get paginated upload tasks for a specific company.
    
    Args:
        company_id (UUID): Company ID to filter tasks
        page_number (int): Page number for pagination (default: 1)
        limit (int): Number of items per page (default: 20)
        
    Returns:
        Dict containing:
            - data: List of upload tasks
            - total: Total number of tasks
            - page: Current page number
            - total_pages: Total number of pages
    """
    try:
        # Build base query
        base_query = supabase.table('upload_tasks').select('*', count='exact')\
            .eq('company_id', str(company_id))
        
        # Get total count
        count_response = base_query.execute()
        total = count_response.count if count_response.count is not None else 0
        
        # Calculate offset and total pages
        offset = (page_number - 1) * limit
        total_pages = ceil(total / limit) if total > 0 else 0
        
        # Get paginated results
        response = base_query.range(offset, offset + limit - 1)\
            .order('created_at', desc=True)\
            .execute()

        return {
            "items": response.data,
            "total": total,
            "page": page_number,
            "page_size": limit,
            "total_pages": total_pages
        }
    except Exception as e:
        logger.error(f"Error in get_upload_tasks_by_company: {str(e)}")
        raise e

async def get_skipped_rows_by_task(
    upload_task_id: UUID,
    page_number: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Get paginated skipped rows for a specific upload task.
    
    Args:
        upload_task_id (UUID): Upload task ID to filter skipped rows
        page_number (int): Page number for pagination (default: 1)
        limit (int): Number of items per page (default: 20)
        
    Returns:
        Dict containing:
            - items: List of skipped rows
            - total: Total number of skipped rows
            - page: Current page number
            - page_size: Number of items per page
            - total_pages: Total number of pages
    """
    try:
        # Build base query
        base_query = supabase.table('skipped_rows').select('*', count='exact')\
            .eq('upload_task_id', str(upload_task_id))
        
        # Get total count
        count_response = base_query.execute()
        total = count_response.count if count_response.count is not None else 0
        
        # Calculate offset and total pages
        offset = (page_number - 1) * limit
        total_pages = ceil(total / limit) if total > 0 else 0
        
        # Get paginated results
        response = base_query.range(offset, offset + limit - 1)\
            .order('created_at', desc=True)\
            .execute()

        return {
            "items": response.data,
            "total": total,
            "page": page_number,
            "page_size": limit,
            "total_pages": total_pages
        }
    except Exception as e:
        logger.error(f"Error in get_skipped_rows_by_task: {str(e)}")
        raise e

async def get_upload_task_file_url(upload_task_id: UUID) -> Optional[str]:
    """
    Get the file_url for a specific upload task.
    
    Args:
        upload_task_id (UUID): Upload task ID
        
    Returns:
        Optional[str]: The file URL if found, None otherwise
    """
    try:
        response = supabase.table('upload_tasks')\
            .select('file_url')\
            .eq('id', str(upload_task_id))\
            .single()\
            .execute()
        
        return response.data.get('file_url') if response.data else None
    except Exception as e:
        logger.error(f"Error in get_upload_task_file_url: {str(e)}")
        raise e

async def get_upload_task_company_id(upload_task_id: UUID) -> Optional[UUID]:
    """
    Get the company_id for a specific upload task.
    
    Args:
        upload_task_id (UUID): Upload task ID
        
    Returns:
        Optional[UUID]: The company ID if found, None otherwise
    """
    try:
        response = supabase.table('upload_tasks')\
            .select('company_id')\
            .eq('id', str(upload_task_id))\
            .single()\
            .execute()
        
        if response.data and 'company_id' in response.data:
            return UUID(response.data['company_id'])
        return None
    except Exception as e:
        logger.error(f"Error in get_upload_task_company_id: {str(e)}")
        raise e

async def update_campaign_run_celery_task_id(campaign_run_id: UUID, celery_task_id: str) -> Optional[Dict]:
    """
    Update the celery_task_id of a campaign run
    
    Args:
        campaign_run_id: UUID of the campaign run
        celery_task_id: Celery task ID to set
        
    Returns:
        Dict containing the updated campaign run record or None if update failed
    """
    try:
        response = supabase.table('campaign_runs').update({
            'celery_task_id': celery_task_id
        }).eq('id', str(campaign_run_id)).execute()
        
        if not response.data:
            logger.error(f"Failed to update celery_task_id for campaign run {campaign_run_id}")
            return None
            
        return response.data[0]
    except Exception as e:
        logger.error(f"Error updating campaign run celery_task_id: {str(e)}")
        return None

async def delete_skipped_rows_by_task(upload_task_id: UUID) -> bool:
    """
    Delete all skipped rows for a specific upload task.
    
    Args:
        upload_task_id (UUID): ID of the upload task
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        response = supabase.table('skipped_rows')\
            .delete()\
            .eq('upload_task_id', str(upload_task_id))\
            .execute()
            
        return True
    except Exception as e:
        logger.error(f"Error deleting skipped rows for task {upload_task_id}: {str(e)}")
        return False

async def update_company_details(company_id: UUID, update_data: dict) -> Optional[dict]:
    """
    Update company details
    
    Args:
        company_id: UUID of the company
        update_data: Dictionary containing fields to update
        
    Returns:
        Updated company record or None if update failed
    """
    try:
        response = supabase.table('companies')\
            .update(update_data)\
            .eq('id', str(company_id))\
            .execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error updating company details: {str(e)}")
        return None