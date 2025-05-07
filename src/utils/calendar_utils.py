from datetime import datetime, timedelta
from uuid import UUID
import pycronofy
import logging
from typing import Dict
from fastapi import HTTPException
from src.database import get_company_by_id, update_company_cronofy_tokens, update_email_log_has_booked, update_call_log_has_booked, get_user_by_id, create_booked_meeting
from src.config import get_settings
from src.services.stripe_service import stripe_service
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def book_appointment(company_id: UUID, log_id: UUID, email: str, start_time: datetime, email_subject: str = "Sales Discussion", campaign_type: str = "email") -> Dict[str, str]:
    """
    Create a calendar event using Cronofy
    
    Args:
        company_id: UUID of the company
        log_id: UUID of the email_log or call_log
        email: Lead's email address
        start_time: datetime for when the meeting should start
        email_subject: Subject line to use for the event summary
        campaign_type: Type of campaign ('email' or 'call')
        
    Returns:
        Dict containing the event details
    """
    settings = get_settings()
    
    # Clean up the subject line by removing 'Re:' prefix
    cleaned_subject = email_subject.strip()
    if cleaned_subject.lower().startswith('re:'):
        cleaned_subject = cleaned_subject[3:].strip()
    
    logger.info(f"Company ID: {company_id}")
    logger.info(f"Log ID: {log_id}")
    logger.info(f"Attendee/Lead Email: {email}")
    logger.info(f"Meeting start time: {start_time}")
    logger.info(f"Event summary: {cleaned_subject}")

    # Get company to get Cronofy credentials
    company = await get_company_by_id(company_id)
    if not company or not company.get('cronofy_access_token'):
        raise HTTPException(status_code=400, detail="No Cronofy connection found")
    
    # Get company owner's user details for Stripe customer ID
    user = await get_user_by_id(UUID(company['user_id']))
    if not user:
        raise HTTPException(status_code=400, detail="Company owner not found")
    
    # Initialize Cronofy client
    cronofy = pycronofy.Client(
        client_id=settings.cronofy_client_id,
        client_secret=settings.cronofy_client_secret,
        access_token=company['cronofy_access_token'],
        refresh_token=company['cronofy_refresh_token']
    )
    
    end_time = start_time + timedelta(minutes=30)
    
    # Format times in ISO 8601 format with Z suffix for UTC
    start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    event = {
        'event_id': str(uuid.uuid4()),
        'summary': cleaned_subject,
        'start': start_time_str,
        'end': end_time_str,
        'attendees': {
            'invite': [{'email': email}]
        }
    }
    
    try:
        cronofy.upsert_event(
            calendar_id=company['cronofy_default_calendar_id'],
            event=event
        )
        
        if campaign_type == "email":
            # Update the email log to indicate that the meeting has been booked
            await update_email_log_has_booked(log_id)
        elif campaign_type == "call":
            # Update the call log to indicate that the meeting has been booked
            await update_call_log_has_booked(log_id)

        # Report meeting to Stripe if user has a customer ID
        reported_to_stripe = False
        if user.get('stripe_customer_id'):
            try:
                await stripe_service.report_meeting_booked(user['stripe_customer_id'])
                reported_to_stripe = True
            except Exception as stripe_error:
                logger.error(f"Failed to report meeting to Stripe: {str(stripe_error)}")
                # Don't fail the booking if Stripe reporting fails

        # Create record in booked_meetings table
        await create_booked_meeting(
            user_id=UUID(company['user_id']),
            company_id=company_id,
            item_id=log_id,
            type=campaign_type,
            reported_to_stripe=reported_to_stripe
        )

        return {
            "message": f"Meeting scheduled for {start_time.strftime('%Y-%m-%d %H:%M')} UTC"
        }
    except pycronofy.exceptions.PyCronofyRequestError as e:
        if getattr(e.response, 'status_code', None) == 401:
            try:
                # Refresh the token
                logger.info("Refreshing Cronofy token")
                auth = cronofy.refresh_authorization()
                
                # Update company with new tokens
                await update_company_cronofy_tokens(
                    company_id=company_id,
                    access_token=auth['access_token'],
                    refresh_token=auth['refresh_token']
                )
                
                # Retry the event creation with new token
                cronofy = pycronofy.Client(
                    client_id=settings.cronofy_client_id,
                    client_secret=settings.cronofy_client_secret,
                    access_token=auth['access_token']
                )
                
                cronofy.upsert_event(
                    calendar_id=company['cronofy_default_calendar_id'],
                    event=event
                )
                
                if campaign_type == "email":
                    # Update the email log to indicate that the meeting has been booked
                    await update_email_log_has_booked(log_id)
                elif campaign_type == "call":
                    # Update the call log to indicate that the meeting has been booked
                    await update_call_log_has_booked(log_id)

                # Report meeting to Stripe if user has a customer ID
                reported_to_stripe = False
                if user.get('stripe_customer_id'):
                    try:
                        await stripe_service.report_meeting_booked(user['stripe_customer_id'])
                        reported_to_stripe = True
                    except Exception as stripe_error:
                        logger.error(f"Failed to report meeting to Stripe: {str(stripe_error)}")
                        # Don't fail the booking if Stripe reporting fails

                # Create record in booked_meetings table
                await create_booked_meeting(
                    user_id=UUID(company['user_id']),
                    company_id=company_id,
                    item_id=log_id,
                    type=campaign_type,
                    reported_to_stripe=reported_to_stripe
                )

                return {
                    "message": f"Meeting scheduled for {start_time.strftime('%Y-%m-%d %H:%M')} UTC"
                }
            except Exception as refresh_error:
                logger.error(f"Error refreshing token: {str(refresh_error)}")
                raise HTTPException(status_code=500, detail="Failed to refresh calendar authorization")
        else:
            logger.error(f"Error creating Cronofy event: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to schedule meeting")
    except Exception as e:
        logger.error(f"Error creating Cronofy event: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to schedule meeting") 