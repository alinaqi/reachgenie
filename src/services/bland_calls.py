from uuid import UUID
from src.config import get_settings
from src.bland_client import BlandClient
import logging
from src.database import create_call

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
        bland_response = await bland_client.start_call(
            phone_number=lead['phone_number'],
            script=call_script
        )
        
        logger.info(f"Bland Call ID: {bland_response['call_id']}")

        # Create call record in database
        call = await create_call(lead['id'], campaign['product_id'], campaign['id'], bland_response['call_id'])
        
        return call
        
    except Exception as e:
        raise Exception("Failed to initiate call")