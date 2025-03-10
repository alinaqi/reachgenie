import asyncio
import imaplib
import email
from email.header import decode_header
import logging
from datetime import datetime, timezone, timedelta
import os
import json
from uuid import UUID

# Import OpenAI directly
from openai import AsyncOpenAI

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

def decode_header_value(header_value):
    if not header_value:
        return ""
    decoded = decode_header(header_value)
    return ''.join(
        str(part[0], part[1] or 'utf-8') if isinstance(part[0], bytes) else str(part[0])
        for part in decoded
    )

def parse_from_field(from_field: str) -> tuple:
    """Extract name and email from From field (e.g., "John Doe <john@example.com>")"""
    if '<' in from_field and '>' in from_field:
        name = from_field.split('<')[0].strip()
        email = from_field.split('<')[1].split('>')[0].strip()
    else:
        name = ''
        email = from_field.strip()
    return name, email

async def check_for_unsubscribe_emails():
    # Zenloop credentials - get directly from environment variables
    account_email = os.environ.get("ZENLOOP_EMAIL", "ali.shaheen@zenloop.com")
    account_password = os.environ.get("ZENLOOP_PASSWORD")
    account_type = "gmail"  # default to gmail
    
    if not account_password:
        logger.error("No password provided via environment variable ZENLOOP_PASSWORD")
        return
    
    # OpenAI API key
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("No OpenAI API key provided via environment variable OPENAI_API_KEY")
        return
    
    # Connect to IMAP server
    host = IMAP_SERVERS.get(account_type)
    if not host:
        logger.error(f"Unsupported email account type: {account_type}")
        return
    
    try:
        logger.info(f"Connecting to {host} with account {account_email}")
        imap = imaplib.IMAP4_SSL(host)
        
        # Login to the account
        imap.login(account_email, account_password)
        
        # Select the mailbox you want to use (e.g., INBOX)
        imap.select("INBOX", readonly=True)
        
        # Search for emails from the last 7 days
        last_processed_date = datetime.now(timezone.utc) - timedelta(days=7)
        last_processed_date_str = last_processed_date.strftime("%d-%b-%Y")
        logger.info(f"Searching for emails since {last_processed_date_str}")
        
        status, messages = imap.uid('search', None, f'SINCE "{last_processed_date_str}"')
        
        if status != 'OK':
            logger.error(f"No messages found since {last_processed_date_str}")
            return
        
        # Get message UIDs
        message_uids = messages[0].split()
        logger.info(f"Found {len(message_uids)} emails")
        
        # OpenAI client for unsubscribe detection
        client = AsyncOpenAI(api_key=openai_api_key)
        
        # Fetch and process up to 10 emails for testing
        processed_count = 0
        unsubscribe_count = 0
        
        for uid in message_uids[:10]:  # Process only the first 10 emails for testing
            uid_str = uid.decode('utf-8')
            logger.info(f"Processing email with UID {uid_str}")
            
            # Fetch the email
            status, data = imap.uid('fetch', uid, '(RFC822)')
            
            if status != 'OK':
                logger.error(f"Failed to fetch email with UID {uid_str}")
                continue
                
            raw_email = data[0][1]
            msg_obj = email.message_from_bytes(raw_email)
            
            # Get subject and from fields
            subject = decode_header_value(msg_obj.get('Subject', ''))
            from_field = decode_header_value(msg_obj.get('From', ''))
            
            logger.info(f"Subject: {subject}")
            logger.info(f"From: {from_field}")
            
            # Extract email body
            body = ""
            if msg_obj.is_multipart():
                for part in msg_obj.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain" or content_type == "text/html":
                        try:
                            body_part = part.get_payload(decode=True).decode('utf-8')
                            body += body_part
                        except:
                            # If decoding fails, try to get the raw payload
                            try:
                                body += str(part.get_payload())
                            except:
                                pass
            else:
                try:
                    body = msg_obj.get_payload(decode=True).decode('utf-8')
                except:
                    # If decoding fails, try to get the raw payload
                    try:
                        body += str(msg_obj.get_payload())
                    except:
                        pass
            
            # Check for unsubscribe request
            try:
                logger.info(f"Checking for unsubscribe request in email: {subject}")
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an assistant that analyzes email content to determine if the user is requesting to unsubscribe or opt-out from emails. Respond with 'yes' if the email contains an unsubscribe request, and 'no' if it doesn't."},
                        {"role": "user", "content": f"Subject: {subject}\n\nBody: {body[:1000]}\n\nDoes this email contain a request to unsubscribe, opt-out, stop receiving emails, or any similar request?"}
                    ],
                    temperature=0.1,
                    max_tokens=10
                )
                
                unsubscribe_check = response.choices[0].message.content.strip().lower()
                logger.info(f"Unsubscribe check result: {unsubscribe_check}")
                
                if unsubscribe_check == "yes":
                    from_name, from_email = parse_from_field(from_field)
                    logger.info(f"UNSUBSCRIBE REQUEST DETECTED from {from_email} ({from_name})")
                    logger.info(f"Subject: {subject}")
                    logger.info(f"Body snippet: {body[:200].replace(chr(10), ' ')}...")
                    unsubscribe_count += 1
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error checking for unsubscribe request: {str(e)}")
        
        logger.info(f"Processed {processed_count} emails")
        logger.info(f"Found {unsubscribe_count} unsubscribe requests")
            
        # Logout from IMAP
        imap.logout()
        
    except Exception as e:
        logger.error(f"Error processing emails: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_for_unsubscribe_emails()) 