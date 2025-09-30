#!/usr/bin/env python3
import asyncio
import logging
from uuid import UUID
import sys
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timezone, timedelta
from src.scripts.process_bounces import extract_bounced_email, determine_bounce_type
from src.database import add_to_do_not_email_list

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# IMAP server configurations
IMAP_SERVERS = {
    'gmail': 'imap.gmail.com',
    'outlook': 'outlook.office365.com',
    'yahoo': 'imap.mail.yahoo.com'
}

# Function to decode email headers
def decode_header_value(header_value):
    if not header_value:
        return ""
    decoded = decode_header(header_value)
    return ''.join(
        str(part[0], part[1] or 'utf-8') if isinstance(part[0], bytes) else str(part[0])
        for part in decoded
    )

async def test_bounce_processing():
    """
    Test bounce processing with a specific email account
    """
    try:
        # Hardcoded test credentials - plain passwords
        company_id = 'company_id'
        email_address = 'email'
        raw_password = 'passowrd'
        email_provider = 'gmail'
        
        logger.info(f"Testing bounce processing for email: {email_address}")
        
        # First, test adding a simulated hard bounce to the do_not_email list
        test_email = "test.hard.bounce@example.com"
        logger.info(f"Simulating a hard bounce for testing: {test_email}")
        
        try:
            result = await add_to_do_not_email_list(
                email=test_email,
                reason="Hard bounce (simulated for testing)",
                company_id=UUID(company_id)
            )
            
            if result["success"]:
                logger.info(f"Successfully added {test_email} to do_not_email list")
            else:
                logger.error(f"Failed to add {test_email} to do_not_email list: {result.get('error')}")
        except Exception as e:
            logger.error(f"Error adding to do_not_email list: {str(e)}")
        
        # Connect directly to IMAP
        host = IMAP_SERVERS.get(email_provider)
        if not host:
            logger.error(f"Unsupported email account type: {email_provider}")
            return
            
        imap = imaplib.IMAP4_SSL(host)
        
        # Login to the account
        try:
            imap.login(email_address, raw_password)
            logger.info(f"Successfully logged into IMAP server: {host}")
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return
            
        # Select the inbox - we'll search for bounce messages here
        imap.select("INBOX", readonly=True)
        
        # Search for typical bounce subject patterns from the last week
        last_week = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%d-%b-%Y")
        search_criteria = f'(OR OR OR OR (SUBJECT "delivery failed") (SUBJECT "undeliverable") (SUBJECT "returned mail") (SUBJECT "delivery status") (SUBJECT "failure notice") SINCE "{last_week}")'
        
        logger.info(f"Searching for bounce messages since {last_week}")
        status, messages = imap.search(None, search_criteria)
        
        if status != "OK":
            logger.error("Failed to search for bounce messages")
            imap.logout()
            return
            
        # Get the list of message IDs
        email_ids = messages[0].split()
        
        if not email_ids:
            logger.info("No bounce notifications found in the inbox.")
            imap.logout()
            return
            
        total_emails = len(email_ids)
        logger.info(f"Found {total_emails} potential bounce notifications")
        
        # Process only up to 10 emails for the test
        max_emails = min(10, total_emails)
        email_ids_to_process = email_ids[:max_emails]
        processed_bounces = []
        
        for email_id in email_ids_to_process:
            # Fetch the email
            res, msg = imap.fetch(email_id, "(RFC822)")
            
            if res != "OK":
                logger.error(f"Failed to fetch email with ID {email_id.decode('utf-8')}")
                continue
                
            # Process the email
            for response_part in msg:
                if isinstance(response_part, tuple):
                    # Parse the raw email content
                    msg_obj = email.message_from_bytes(response_part[1])
                    
                    # Process bounce notification
                    subject = decode_header_value(msg_obj.get("Subject", ""))
                    logger.info(f"Processing potential bounce: {subject}")
                    
                    # Determine if this is actually a bounce message
                    is_bounce = any(phrase in subject.lower() for phrase in [
                        "delivery", "undeliverable", "failed", "failure", "returned", "bounce", 
                        "not delivered", "delivery status", "mail delivery", "rejected"
                    ])
                    
                    if not is_bounce:
                        logger.info(f"Skipping non-bounce message: {subject}")
                        continue
                        
                    # Try to extract the bounced email address
                    bounced_email = extract_bounced_email(msg_obj)
                    
                    if not bounced_email:
                        logger.warning(f"Could not extract bounced email from message: {subject}")
                        continue
                        
                    # Determine bounce type
                    bounce_type = determine_bounce_type(msg_obj)
                    
                    logger.info(f"Found bounce: {bounced_email} (Type: {bounce_type})")
                    
                    # Add to do_not_email list if it's a hard bounce
                    if bounce_type == "hard_bounce":
                        try:
                            result = await add_to_do_not_email_list(
                                email=bounced_email,
                                reason=f"Hard bounce: {subject}",
                                company_id=UUID(company_id)
                            )
                            
                            if result["success"]:
                                logger.info(f"Added {bounced_email} to do_not_email list (hard bounce)")
                            else:
                                logger.error(f"Failed to add {bounced_email} to do_not_email list: {result.get('error')}")
                                
                        except Exception as e:
                            logger.error(f"Error processing bounce for {bounced_email}: {str(e)}")
                    else:
                        logger.info(f"Detected soft bounce for {bounced_email}, not adding to do_not_email list")
                        
                    # Record that we processed this bounce
                    processed_bounces.append({
                        "email": bounced_email,
                        "bounce_type": bounce_type,
                        "subject": subject
                    })
                    
        # Logout from IMAP
        imap.logout()
        
        if processed_bounces:
            logger.info(f"Processed {len(processed_bounces)} bounce messages:")
            for i, bounce in enumerate(processed_bounces):
                logger.info(f"Bounce #{i+1}:")
                logger.info(f"  Email: {bounce.get('email')}")
                logger.info(f"  Type: {bounce.get('bounce_type')}")
                logger.info(f"  Subject: {bounce.get('subject')}")
                logger.info("---")
        else:
            logger.info("No valid bounce messages were processed.")
            
        logger.info("Test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in test bounce processing: {str(e)}")
        # Print full traceback for debugging
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bounce_processing()) 