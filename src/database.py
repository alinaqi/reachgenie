from supabase import create_client, Client
from src.config import get_settings
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime

settings = get_settings()
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)

async def get_user_by_email(email: str):
    response = supabase.table('users').select('*').eq('email', email).execute()
    return response.data[0] if response.data else None

async def create_user(email: str, password_hash: str):
    user_data = {'email': email, 'password_hash': password_hash}
    response = supabase.table('users').insert(user_data).execute()
    return response.data[0]

async def get_companies_by_user_id(user_id: UUID):
    response = supabase.table('companies').select('*').eq('user_id', str(user_id)).execute()
    return response.data

async def db_create_company(user_id: UUID, name: str, address: Optional[str], industry: Optional[str]):
    company_data = {
        'user_id': str(user_id),
        'name': name,
        'address': address,
        'industry': industry
    }
    response = supabase.table('companies').insert(company_data).execute()
    return response.data[0]

async def db_create_product(company_id: UUID, product_name: str, description: Optional[str]):
    product_data = {
        'company_id': str(company_id),
        'product_name': product_name,
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
    return response.data[0] if response.data else None

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

async def create_email_log(campaign_id: UUID, lead_id: UUID, sent_at: str):
    log_data = {
        'campaign_id': str(campaign_id),
        'lead_id': str(lead_id),
        'sent_at': sent_at
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

async def create_email_log_detail(email_logs_id: UUID, message_id: str, email_subject: str, email_body: str, sender_type: str):
    log_detail_data = {
        'email_logs_id': str(email_logs_id),
        'message_id': message_id,
        'email_subject': email_subject,
        'email_body': email_body,
        'sender_type': sender_type
    }
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