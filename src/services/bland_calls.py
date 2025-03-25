from uuid import UUID
from src.config import get_settings
from src.bland_client import BlandClient
import logging
from src.database import create_call, get_product_by_id, get_company_by_id, update_call_details, update_call_failure_reason, get_call_by_id
from typing import Optional

logger = logging.getLogger(__name__)

async def initiate_call(
    campaign: dict,
    lead: dict,
    call_script: str,
    campaign_run_id: Optional[UUID] = None,
    call_log_id: Optional[UUID] = None
):  
    # Initialize Bland client and start the call
    settings = get_settings()
    
    # Add debugging logs for Bland settings
    logger.info(f"Initializing Bland client with API key: {settings.bland_api_key[:5]}...")
    logger.info(f"Bland secret key exists: {bool(settings.bland_secret_key)}")
    if settings.bland_secret_key:
        logger.info(f"Bland secret key starts with: {settings.bland_secret_key[:5]}...")
    
    logger.info(f"Bland tool ID exists: {bool(settings.bland_tool_id)}")
    if settings.bland_tool_id:
        logger.info(f"Using Bland tool ID: {settings.bland_tool_id}")
    else:
        logger.error("Bland tool ID is missing in settings")
    
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
        
        # Log lead information
        logger.info(f"Initiating call for lead: {lead.get('first_name', '')} {lead.get('last_name', '')}")
        logger.info(f"Lead phone number: {lead.get('phone_number', 'Not provided')}")
        
        if not lead.get('phone_number'):
            raise Exception("Lead is missing a phone number")

        # Create call record in database with script
        if campaign_run_id is not None:
            try:
                # Check if a call record already exists for this lead, campaign, and campaign run
                try:
                    from src.database import supabase
                    existing_call = supabase.table('calls')\
                        .select('*')\
                        .eq('lead_id', str(lead['id']))\
                        .eq('campaign_id', str(campaign['id']))\
                        .eq('campaign_run_id', str(campaign_run_id))\
                        .execute()
                    
                    if existing_call.data and len(existing_call.data) > 0:
                        logger.info(f"Found existing call record with ID: {existing_call.data[0]['id']}")
                        call = existing_call.data[0]
                        # Skip the create_call function below since we already have a record
                        logger.info("Using existing call record instead of creating a new one")
                except Exception as lookup_error:
                    logger.warning(f"Error checking for existing call record: {str(lookup_error)}")
                    return
                
                # Only create a new call record if we didn't find an existing one
                if not (existing_call and existing_call.data and len(existing_call.data) > 0):
                    call = await create_call(
                        lead_id=lead['id'], 
                        product_id=campaign['product_id'], 
                        campaign_id=campaign['id'], 
                        script=call_script, 
                        campaign_run_id=campaign_run_id if campaign_run_id is not None else None
                    )
                    logger.info(f"Created call record with ID: {call['id']}")
            except Exception as db_error:
                logger.error(f"Error creating call record: {str(db_error)}")
                logger.exception("Database error traceback:")
                raise Exception(f"Failed to create call record: {str(db_error)}")
        else:
            if call_log_id is not None:
                call = await get_call_by_id(call_log_id)
                logger.info(f"Found call record with ID: {call['id']}")
            else:
                logger.error("No call log ID provided")
                raise Exception("No call log ID provided")

        # Prepare request data for the call
        request_data = {
            "company_uuid": str(campaign['company_id']),
            "email": lead['email'],
            "email_subject": f"'{product['product_name']}' Discovery Call – Exclusive Insights for You!",
            "call_log_id": str(call['id'])
        }
        
        # Add email if available
        if lead.get('email'):
            request_data["email"] = lead['email']
            request_data["email_subject"] = f"'{product['product_name']}' Discovery Call – Exclusive Insights for You!"

        # Log call details before making the API call
        logger.info(f"Making call to {lead['phone_number']} for company {company['name']}")
        logger.info(f"Call script length: {len(call_script)} characters")

        bland_response = await bland_client.start_call(
            phone_number=lead['phone_number'],
            script=call_script,
            request_data=request_data,
            company=company
        )
        
        logger.info(f"Bland Call ID: {bland_response.get('call_id', 'Not provided')}")

        # Update call record in database with bland_call_id
        if bland_response and bland_response.get('call_id'):
            try:
                db_update_result = await update_call_details(call['id'], bland_response['call_id'])
                if db_update_result:
                    logger.info(f"Updated call record with Bland call ID: {bland_response['call_id']}")
                else:
                    logger.warning(f"Failed to update call record in database, but call was initiated. Call ID: {call['id']}, Bland Call ID: {bland_response['call_id']}")
            except Exception as db_error:
                # If database update fails, log the error but consider the call to be successful
                logger.error(f"Error updating call record in database: {str(db_error)}")
                logger.exception("Database update exception traceback:")
                # The call was still successfully initiated, so we continue
        else:
            logger.warning(f"No call_id in Bland response: {bland_response}")
        
        # Return the call record regardless of database update status
        # The call was successfully initiated with Bland
        return call
        
    except Exception as e:
        logger.error(f"Failed to initiate call: {str(e)}")
        if 'call' in locals():  # Check if call was created before the error
            await update_call_failure_reason(call['id'], str(e))
        raise Exception(f"Failed to initiate call: {str(e)}")

async def initiate_test_call(
    campaign: dict,
    lead: dict,
    call_script: str,
    lead_contact: str
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

        # Prepare request data for the call
        request_data = {
            "company_uuid": str(campaign['company_id']),
            "email_subject": f"'{product['product_name']}' Discovery Call – Exclusive Insights for You!"
        }

        bland_response = await bland_client.start_call(
            phone_number=lead_contact,
            script=call_script,
            request_data=request_data,
            company=company
        )
        
        logger.info(f"Bland Call ID: {bland_response['call_id']}")
        
    except Exception as e:
        logger.error(f"Failed to initiate test call: {str(e)}")
        raise Exception(f"Failed to initiate test call: {str(e)}")