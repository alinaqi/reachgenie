from datetime import datetime, timedelta
from uuid import UUID
import pycronofy
import logging
from typing import Dict
from fastapi import HTTPException
from src.database import get_company_by_id, update_company_cronofy_tokens
from src.config import get_settings
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def book_appointment(company_id: UUID, email: str, start_time: datetime, email_subject: str = "Sales Discussion") -> Dict[str, str]:
    """
    Create a calendar event using Cronofy
    
    Args:
        company_id: UUID of the company
        email: Lead's email address
        start_time: datetime for when the meeting should start
        email_subject: Subject line to use for the event summary
        
    Returns:
        Dict containing the event details
    """
    settings = get_settings()
    
    # Clean up the subject line by removing 'Re:' prefix
    cleaned_subject = email_subject.strip()
    if cleaned_subject.lower().startswith('re:'):
        cleaned_subject = cleaned_subject[3:].strip()
    
    logger.info(f"Company ID: {company_id}")
    logger.info(f"Attendee/Lead Email: {email}")
    logger.info(f"Meeting start time: {start_time}")
    logger.info(f"Event summary: {cleaned_subject}")

    # Get company to get Cronofy credentials
    company = await get_company_by_id(company_id)
    if not company or not company.get('cronofy_access_token'):
        raise HTTPException(status_code=400, detail="No Cronofy connection found")
    
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