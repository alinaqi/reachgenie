#!/usr/bin/env python3
"""
Email Bounce Processor

This script processes both hard and soft bounce notifications from company email accounts.
It performs the following actions:
1. Connects to each company's email account via IMAP
2. Searches for bounce notification emails
3. Extracts the bounced email address
4. Determines if it's a hard or soft bounce
5. Adds the bounced email to the "do not email" list
6. Removes the processed bounce emails from the inbox
7. Updates the last processed UID to avoid reprocessing the same emails

The script is designed to be run as a scheduled job (e.g., via cron).
"""
import imaplib
import email
from email.header import decode_header
import logging
import asyncio
from typing import List, Dict
from datetime import datetime, timezone, timedelta
from uuid import UUID

from src.database import (
    get_companies_with_email_credentials,
    add_to_do_not_email_list,
    update_last_processed_bounce_uid,
    get_email_log_by_message_id,
    get_lead_by_email,
    update_lead_do_not_contact_by_email
)
from src.utils.encryption import decrypt_password

# IMAP server configurations
IMAP_SERVERS = {
    'gmail': 'imap.gmail.com',
    'outlook': 'outlook.office365.com',
    'yahoo': 'imap.mail.yahoo.com'
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Function to decode email headers
def decode_header_value(header_value):
    if not header_value:
        return ""
    decoded = decode_header(header_value)
    return ''.join(
        str(part[0], part[1] or 'utf-8') if isinstance(part[0], bytes) else str(part[0])
        for part in decoded
    )

# Extract bounced email address from bounce message
def extract_bounced_email(msg_obj):
    """Extract the email address that bounced from various bounce formats"""
    bounced_email = None
    
    # DSN (Delivery Status Notification) format
    if msg_obj.is_multipart():
        for part in msg_obj.walk():
            content_type = part.get_content_type()
            if content_type == 'message/delivery-status':
                delivery_status = part.get_payload()
                if isinstance(delivery_status, list):
                    for status_part in delivery_status:
                        if isinstance(status_part, email.message.Message):
                            # Look for Final-Recipient header
                            final_recipient = status_part.get('Final-Recipient')
                            if final_recipient:
                                # Format is typically: "rfc822; user@example.com"
                                if ';' in final_recipient:
                                    bounced_email = final_recipient.split(';')[1].strip()
                                else:
                                    bounced_email = final_recipient.strip()
    
    # If not found in DSN format, try other common formats
    if not bounced_email:
        # Check common headers where the original recipient might be mentioned
        for header in ['X-Failed-Recipients', 'X-Original-To', 'Return-Path']:
            value = msg_obj.get(header)
            if value:
                # Extract email from potential angle brackets
                if '<' in value and '>' in value:
                    bounced_email = value.split('<')[1].split('>')[0].strip()
                else:
                    bounced_email = value.strip()
                break
    
    # Last resort: parse the body for common bounce patterns
    if not bounced_email:
        if msg_obj.is_multipart():
            for part in msg_obj.walk():
                content_type = part.get_content_type()
                if content_type in ['text/plain', 'text/html']:
                    try:
                        body = part.get_payload(decode=True).decode(errors='ignore')
                        # Common patterns in bounce messages
                        patterns = [
                            r'(?:failed recipient|failed delivery|undeliverable to): ([\w._%+-]+@[\w.-]+\.\w+)',
                            r'(?:recipient address rejected): ([\w._%+-]+@[\w.-]+\.\w+)',
                            r'(?:No such user|User unknown): ([\w._%+-]+@[\w.-]+\.\w+)',
                            r'The following recipient.+?: ([\w._%+-]+@[\w.-]+\.\w+)'
                        ]
                        
                        import re
                        for pattern in patterns:
                            match = re.search(pattern, body, re.IGNORECASE)
                            if match:
                                bounced_email = match.group(1)
                                break
                        
                        if bounced_email:
                            break
                    except Exception as e:
                        logger.error(f"Error parsing email body: {str(e)}")
        else:
            try:
                body = msg_obj.get_payload(decode=True).decode(errors='ignore')
                # Apply same patterns as above
                patterns = [
                    r'(?:failed recipient|failed delivery|undeliverable to): ([\w._%+-]+@[\w.-]+\.\w+)',
                    r'(?:recipient address rejected): ([\w._%+-]+@[\w.-]+\.\w+)',
                    r'(?:No such user|User unknown): ([\w._%+-]+@[\w.-]+\.\w+)',
                    r'The following recipient.+?: ([\w._%+-]+@[\w.-]+\.\w+)'
                ]
                
                import re
                for pattern in patterns:
                    match = re.search(pattern, body, re.IGNORECASE)
                    if match:
                        bounced_email = match.group(1)
                        break
            except Exception as e:
                logger.error(f"Error parsing email body: {str(e)}")
    
    return bounced_email.lower() if bounced_email else None

# Determine bounce type from bounce message
def determine_bounce_type(msg_obj):
    """Determine the type of bounce based on the message content"""
    bounce_type = "hard_bounce"  # Default to hard bounce
    
    # Check for common soft bounce indicators in headers
    if msg_obj.is_multipart():
        for part in msg_obj.walk():
            content_type = part.get_content_type()
            if content_type == 'message/delivery-status':
                delivery_status = part.get_payload()
                if isinstance(delivery_status, list):
                    for status_part in delivery_status:
                        if isinstance(status_part, email.message.Message):
                            # Check status code
                            status = status_part.get('Status')
                            if status:
                                # 4.X.X status codes are typically temporary failures (soft bounces)
                                if status.startswith('4'):
                                    bounce_type = "soft_bounce"
                                # 5.X.X status codes are typically permanent failures (hard bounces)
                                elif status.startswith('5'):
                                    bounce_type = "hard_bounce"
    
    # Check subject and body for common soft bounce indicators
    subject = decode_header_value(msg_obj.get("Subject", ""))
    soft_bounce_keywords = [
        "mailbox full", "quota exceeded", "over quota", "storage limit", "retry",
        "temporary", "temporarily", "delayed", "deferred", "try again", "try later",
        "timeout", "congestion", "busy", "unavailable", "overload", "load",
        "greylist", "greylisted", "throttle", "throttled", "rate limit", "too many"
    ]
    
    # Check subject for soft bounce indicators
    if any(keyword in subject.lower() for keyword in soft_bounce_keywords):
        bounce_type = "soft_bounce"
    
    # If still marked as hard bounce, check body for soft bounce indicators
    if bounce_type == "hard_bounce":
        if msg_obj.is_multipart():
            for part in msg_obj.walk():
                content_type = part.get_content_type()
                if content_type in ['text/plain', 'text/html']:
                    try:
                        body = part.get_payload(decode=True).decode(errors='ignore')
                        if any(keyword in body.lower() for keyword in soft_bounce_keywords):
                            bounce_type = "soft_bounce"
                            break
                    except Exception:
                        pass
        else:
            try:
                body = msg_obj.get_payload(decode=True).decode(errors='ignore')
                if any(keyword in body.lower() for keyword in soft_bounce_keywords):
                    bounce_type = "soft_bounce"
            except Exception:
                pass
    
    return bounce_type

# Function to fetch bounce notifications from IMAP Server
async def fetch_bounces(company: Dict):
    """
    Process bounce notifications for a single company
    
    Args:
        company: Company data dictionary
    """
    max_emails = 100  # Number of emails to fetch per run
    company_id = UUID(company['id'])

    try:
        # Decrypt email password
        try:
            decrypted_password = decrypt_password(company['account_password'])
        except Exception as e:
            logger.error(f"Failed to decrypt password for company '{company['name']}' ({company_id}): {str(e)}")
            return
        
        # Get IMAP host from mapping
        host = IMAP_SERVERS.get(company['account_type'])
        if not host:
            logger.error(f"Unsupported email account type: {company['account_type']}")
            return

        imap = imaplib.IMAP4_SSL(host)

        # Login to the account
        imap.login(company['account_email'], decrypted_password)

        # Select the inbox - changed from readonly=True to readonly=False to allow deletion
        imap.select("INBOX", readonly=False)

        # Get last processed UID for bounces
        last_processed_uid = company.get('last_processed_bounce_uid')
        if not last_processed_uid:
            # If no last_processed_uid, fetch all emails from two days ago
            last_processed_date = datetime.now(timezone.utc) - timedelta(days=2)
            logger.info(f"No last_processed_bounce_uid found for company '{company['name']}' ({company_id}). Fetching all emails from two days ago.")
            
            last_processed_date_str = last_processed_date.strftime("%d-%b-%Y")
            logger.info(f"Processing bounce notifications since {last_processed_date_str} for company '{company['name']}' ({company_id})")
            
            # Search for typical bounce subject patterns
            search_criteria = f'(OR OR OR OR (SUBJECT "delivery failed") (SUBJECT "undeliverable") (SUBJECT "returned mail") (SUBJECT "delivery status") (SUBJECT "failure notice") SINCE "{last_processed_date_str}")'
            status, messages = imap.search(None, search_criteria)
        else:
            x = int(last_processed_uid) + 1
            logger.info(f"Processing bounce notifications from UID {x} for company '{company['name']}' ({company_id})")
            
            # Search for typical bounce subject patterns with UIDs greater than last processed
            search_criteria = f'(OR OR OR OR (SUBJECT "delivery failed") (SUBJECT "undeliverable") (SUBJECT "returned mail") (SUBJECT "delivery status") (SUBJECT "failure notice") UID {x}:*)'
            status, messages = imap.search(None, search_criteria)

        if status != "OK":
            raise Exception("Failed to search for bounce messages")

        # Get the list of message IDs
        email_ids = messages[0].split()
        
        if not email_ids:
            logger.info(f"No bounce notifications found for company '{company['name']}'")
            imap.logout()
            return []

        total_emails = len(email_ids)
        logger.info(f"Found {total_emails} potential bounce notifications for company '{company['name']}', processing up to {max_emails} in this run")

        # Process only up to max_emails
        email_ids_to_process = email_ids[:max_emails]
        processed_bounces = []

        for email_id in email_ids_to_process:
            # Fetch the email
            res, msg = imap.fetch(email_id, "(RFC822 UID)")
            
            if res != "OK":
                logger.error(f"Failed to fetch email with ID {email_id.decode('utf-8')}")
                continue

            # Extract UID for tracking
            uid = None
            for response_part in msg:
                if isinstance(response_part, tuple):
                    # Find the UID in the response
                    uid_data = imap.fetch(email_id, "(UID)")
                    if uid_data[0] == "OK":
                        uid_string = uid_data[1][0].decode('utf-8')
                        # Extract UID using regex to handle different IMAP server formats
                        import re
                        uid_match = re.search(r'UID (\d+)', uid_string)
                        if uid_match:
                            uid = uid_match.group(1)
                    
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
                    
                    # Extract In-Reply-To or References header to find our original message ID
                    in_reply_to = msg_obj.get("In-Reply-To")
                    references = msg_obj.get("References")
                    original_message_id = None
                    
                    if in_reply_to:
                        original_message_id = in_reply_to.strip()
                    elif references:
                        # References may contain multiple message IDs, try to find ours
                        ref_ids = references.strip().split()
                        if ref_ids:
                            original_message_id = ref_ids[-1]  # Usually the last one
                    
                    # Try to find the email log associated with this message ID
                    email_log = None
                    if original_message_id:
                        try:
                            email_log = await get_email_log_by_message_id(original_message_id)
                        except Exception as e:
                            logger.error(f"Error retrieving email log: {str(e)}")
                    
                    # Skip if we can't verify this was an email sent from our system
                    if not email_log:
                        logger.info(f"Bounce email doesn't match any message ID in our system, checking if we can find the recipient in our database")
                        # Additional check - if the bounced email exists in our leads database, process it anyway
                        lead = await get_lead_by_email(bounced_email)
                        if not lead:
                            logger.info(f"Skipping bounce for {bounced_email} - not in our system")
                            continue
                        logger.info(f"Processing bounce for {bounced_email} - email address exists in our leads database")
                    
                    # Add to do_not_email list for both hard and soft bounces
                    try:
                        bounce_reason = f"{bounce_type.replace('_', ' ').title()}: {subject}"
                        result = await add_to_do_not_email_list(
                            email=bounced_email,
                            reason=bounce_reason,
                            company_id=company_id
                        )
                        
                        if result["success"]:
                            logger.info(f"Added {bounced_email} to do_not_email list ({bounce_type})")
                            
                            # Check if the email belongs to a lead in our database
                            lead = await get_lead_by_email(bounced_email)
                            if lead:
                                # Mark the lead as do_not_contact
                                lead_update_result = await update_lead_do_not_contact_by_email(
                                    email=bounced_email,
                                    company_id=company_id
                                )
                                
                                if lead_update_result["success"]:
                                    logger.info(f"Marked lead with email {bounced_email} as do_not_contact")
                                else:
                                    logger.error(f"Failed to mark lead with email {bounced_email} as do_not_contact: {lead_update_result.get('error')}")
                            else:
                                logger.info(f"No lead found with email {bounced_email} in our database")
                        else:
                            logger.error(f"Failed to add {bounced_email} to do_not_email list: {result.get('error')}")
                            
                    except Exception as e:
                        logger.error(f"Error processing bounce for {bounced_email}: {str(e)}")
                    
                    # Record that we processed this bounce
                    processed_bounces.append({
                        "email": bounced_email,
                        "bounce_type": bounce_type,
                        "subject": subject,
                        "email_log_id": email_log["id"] if email_log else None,
                        "processed_at": datetime.now(timezone.utc),
                        "uid": uid
                    })
                    
                    # Mark the email for deletion by adding the \Deleted flag
                    imap.store(email_id, '+FLAGS', '\\Deleted')
                    logger.info(f"Marked bounce email for {bounced_email} for deletion")

        # Permanently remove emails marked for deletion
        imap.expunge()
        logger.info(f"Deleted processed bounce emails from inbox for company '{company['name']}'")
        
        # Logout from IMAP
        imap.logout()
        
        # Update the last processed UID
        if email_ids_to_process:
            max_uid = max(int(email['uid']) for email in email_ids_to_process)
            if max_uid > 0:
                logger.info(f"Updating last_processed_bounce_uid for company '{company['name']}' ({company_id}) to {max_uid}")
                await update_last_processed_bounce_uid(company_id, str(max_uid))

        return processed_bounces

    except Exception as e:
        logger.error(f"Error processing bounces for company '{company['name']}': {str(e)}")
        return []

async def main():
    """Main function to process bounce notifications for all companies"""
    try:
        last_id = None
        while True:
            # Get paginated companies with email credentials
            companies = await get_companies_with_email_credentials(last_id=last_id)
            if not companies:
                logger.info("No more companies to process")
                break
                
            logger.info(f"Found {len(companies)} companies with email credentials")
            
            # Process bounces for each company in this page
            for company in companies:
                try:
                    await fetch_bounces(company)
                except Exception as e:
                    logger.error(f"Error processing bounces for company '{company['name']}' {company['id']}: {str(e)}")
                    continue
                
                # Add small delay between companies to avoid rate limits
                await asyncio.sleep(1)
            
            # Update last_id for next page
            last_id = UUID(companies[-1]['id'])
            
    except Exception as e:
        logger.error(f"Error in main bounce processing: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 