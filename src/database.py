from supabase import create_client, Client
from src.config import get_settings
from typing import Optional
from uuid import UUID

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

async def create_call(lead_id: UUID, product_id: UUID):
    call_data = {
        'lead_id': str(lead_id),
        'product_id': str(product_id)
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