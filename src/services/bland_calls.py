from uuid import UUID
from src.config import get_settings
from src.bland_client import BlandClient
import logging
from src.database import create_call, get_product_by_id, get_company_by_id, update_call_details

logger = logging.getLogger(__name__)

async def initiate_call(
    campaign: dict,
    lead: dict,
    call_script: str
):  
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
        # Get product details for email subject
        product = await get_product_by_id(campaign['product_id'])
        if not product:
            raise Exception("Product not found")

        # Get company details
        company = await get_company_by_id(campaign['company_id'])
        if not company:
            raise Exception("Company not found")

        call = await create_call(lead['id'], campaign['product_id'], campaign['id'])

        # Prepare request data for the call
        request_data = {
            "company_uuid": str(campaign['company_id']),
            "email": lead['email'],
            "email_subject": f"'{product['product_name']}' Discovery Call – Exclusive Insights for You!",
            "call_log_id": str(call['id'])
        }

        bland_response = await bland_client.start_call(
            phone_number=lead['phone_number'],
            script=call_script,
            request_data=request_data,
            company=company
        )
        
        logger.info(f"Bland Call ID: {bland_response['call_id']}")

        # Update call record in database
        await update_call_details(call['id'], bland_response['call_id'])

        # Create call record in database
        #call = await create_call(lead['id'], campaign['product_id'], campaign['id'], bland_response['call_id'])
        
        return call
        
    except Exception as e:
        logger.error(f"Failed to initiate call: {str(e)}")
        raise Exception(f"Failed to initiate call: {str(e)}")