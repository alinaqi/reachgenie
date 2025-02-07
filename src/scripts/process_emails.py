import imaplib
import email
from email.header import decode_header
import logging
import asyncio
from typing import List, Dict
from datetime import datetime, timezone
from uuid import UUID
from src.utils.smtp_client import SMTPClient

from src.database import (
    get_companies_with_email_credentials,
    update_last_processed_email_date,
    create_email_log_detail,
    update_email_log_has_replied
)
from src.utils.encryption import decrypt_password
from src.utils.llm import generate_ai_reply

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
    decoded = decode_header(header_value)
    return ''.join(
        str(part[0], part[1] or 'utf-8') if isinstance(part[0], bytes) else str(part[0])
        for part in decoded
    )

def parse_from_field(from_field: str) -> tuple[str, str]:
    """Extract name and email from From field (e.g., "John Doe <john@example.com>")"""
    if '<' in from_field and '>' in from_field:
        name = from_field.split('<')[0].strip()
        email = from_field.split('<')[1].split('>')[0].strip()
    else:
        name = ''
        email = from_field.strip()
    return name, email

# Function to fetch the oldest N emails from IMAP Server
async def fetch_emails(company: Dict):
    """
    Process emails for a single company
    
    Args:
        company: Company data dictionary
    """
    max_emails = 100 # Number of emails to fetch per run
    company_id = UUID(company['id'])

    try:
        # Get the last processed email date
        last_processed_date = company.get('last_email_processed_at')
        if not last_processed_date:
            logger.error(f"No last processed email date found for company '{company['name']}' ({company_id}). Please set an initial processing date.")
            return
        
        # Convert ISO format string to datetime object
        last_processed_date = datetime.fromisoformat(last_processed_date.replace('Z', '+00:00'))
        last_processed_date_str = last_processed_date.strftime("%d-%b-%Y")
        logger.info(f"Processing unseen emails since {last_processed_date_str} for company '{company['name']}' ({company_id})")

        # Decrypt email password
        try:
            decrypted_password = decrypt_password(company['account_password'])
        except Exception as e:
            logger.error(f"Failed to decrypt password for company {company_id}: {str(e)}")
            return
        #print(decrypted_password)
        
        # Get IMAP host from mapping
        host = IMAP_SERVERS.get(company['account_type'])
        if not host:
            logger.error(f"Unsupported email account type: {company['account_type']}")
            return

        imap = imaplib.IMAP4_SSL(host)

        # Login to the account
        imap.login(company['account_email'], decrypted_password)

        # Select the mailbox you want to use (e.g., INBOX)
        imap.select("INBOX", readonly=True)

        # Fetch the emails since a specified date, ordered oldest first
        # 'Since' ensure that only emails received on or after the since date are retrieved and processed.
        status, messages = imap.search(None, f'SINCE "{last_processed_date_str}"')

        if status != "OK":
            raise Exception("Failed to retrieve emails")

        # Get the list of email IDs
        email_ids = messages[0].split()
        
        if not email_ids:
            logger.info(f"No unseen emails found since {last_processed_date_str} for company '{company['name']}'")
            return []

        total_emails = len(email_ids)
        logger.info(f"Found {total_emails} emails for company '{company['name']}', processing up to {max_emails} in this run")

        # Fetch the oldest n number of email IDs (reverse slicing)
        oldest_email_ids = email_ids[:max_emails]

        email_data = []

        # Fetch only the limited UIDs
        for email_id in oldest_email_ids:
            # Fetch the email by ID
            res, msg = imap.fetch(email_id, "(RFC822)")
            
            logger.info(f"Fetched email with UID {email_id.decode('utf-8')}")

            if res != "OK":
                raise Exception(f"Failed to fetch email with UID {email_id.decode('utf-8')}")

            for response_part in msg:
                if isinstance(response_part, tuple):
                    # Parse the raw email content
                    msg_obj = email.message_from_bytes(response_part[1])

                    # Decode email fields
                    subject = decode_header_value(msg_obj.get("Subject"))
                    from_field = decode_header_value(msg_obj.get("From"))
                    to = decode_header_value(msg_obj.get("To"))
                    date = msg_obj.get("Date")
                    message_id = msg_obj.get("Message-ID")

                    # Extract the email body
                    body = ""
                    if msg_obj.is_multipart():
                        for part in msg_obj.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))

                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                            elif content_type == "text/html" and "attachment" not in content_disposition:
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        content_type = msg_obj.get_content_type()
                        if content_type == "text/plain" or content_type == "text/html":
                            body = msg_obj.get_payload(decode=True).decode(errors="ignore")

                    # Extract sender name and email
                    sender_name, sender_email = parse_from_field(from_field)

                    email_data.append({
                        "subject": subject,
                        "message_id": message_id,
                        "from": sender_email,
                        "from_name": sender_name,
                        "from_full": from_field,
                        "to": to,
                        "body": body,
                        "date": date
                    })

        # Logout and close the connection
        imap.logout()

        await process_emails(email_data, company, decrypted_password)

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# Example usage
#if __name__ == "__main__":
    #username = "naveed.butt@workhub.ai"
    #password = "wnpc stgq ixsh fhkb"

    #since_date = "20-Jan-2025"
    #max_emails_to_fetch = 6
    #emails = fetch_emails(username, password, since_date, max_emails_to_fetch)

    #if not emails:
    #    print("No emails found to display.")
    #else:
    #    for idx, email_info in enumerate(emails, 1):
            #print(f"=============================== Email {idx}: ===============================\n")
            #for key, value in email_info.items():
            #    print(f"{key}: {value}")
            #print("\n" + "="*50 + "\n")

async def process_emails(
    emails: List[Dict],
    company: Dict,
    decrypted_password: str
) -> None:
    # Process each email one by one
    for email_data in emails:
        try:
            # Extract email_log_id from the 'To' field. Format of To field in case of our emails: prefix+email_log_id@domain
            # We do this inorder to find out only those emails which are sent by leads/customers back to our system, otherwise we have no track to identify such thing
            # and ignoring all emails which are not related to our system.
            email_log_id_str = email_data['to'].split('+')[1].split('@')[0]
            email_log_id = UUID(email_log_id_str)
            logger.info(f"Extracted email_log_id from 'to' field: {email_log_id}")
        except (IndexError, ValueError) as e:
            logger.info(f"Unable to extract email_log_id from {email_data['to']}. Ignoring this email.")
            continue

        # Parse the email date string into a datetime object
        from email.utils import parsedate_to_datetime
        sent_at = parsedate_to_datetime(email_data['date'])
        # sent_at will already have the correct timezone from the email header

        logger.info(f"Attempting to create email_log_detail with message_id: {email_data['message_id']}")
        await create_email_log_detail(
            email_logs_id=email_log_id,
            message_id=email_data['message_id'],
            email_subject=email_data['subject'],
            email_body=email_data['body'],
            sent_at=sent_at,  # This will now have the original timezone from the email
            sender_type='user',  # This is a user reply
            from_name=email_data['from_name'],
            from_email=email_data['from'],
            to_email=email_data['to']
        )
        logger.info(f"Successfully created email_log_detail for message_id: {email_data['message_id']}")

        # Update has_replied status to True
        success = await update_email_log_has_replied(email_log_id)
        if success:
            logger.info(f"Successfully updated has_replied status for email_log_id: {email_log_id}")
        else:
            logger.error(f"Failed to update has_replied status for email_log_id: {email_log_id}")

        ai_reply = await generate_ai_reply(email_log_id, email_data)

        if ai_reply:
            logger.info(f"Creating email_log_detail for the AI reply")
            response_subject = f"Re: {email_data['subject']}" if not email_data['subject'].startswith('Re:') else email_data['subject']
            await create_email_log_detail(
                email_logs_id=email_log_id,
                message_id=None,
                email_subject=response_subject,
                email_body=ai_reply,
                sender_type='assistant',
                sent_at=datetime.now(timezone.utc),
                from_name=company['name'],
                from_email=company['account_email'],
                to_email=email_data['from']
            )
            logger.info("Successfully created email_log_detail for the AI reply")

            async with SMTPClient(
                account_email=company['account_email'],
                account_password=decrypted_password,  # Use decrypted password
                provider=company['account_type']
            ) as smtp_client:

                # Send email with reply-to header
                await smtp_client.send_email(
                    to_email=email_data['from'],
                    subject=response_subject,
                    html_content=ai_reply,
                    from_name=company["name"],
                    email_log_id=email_log_id
                )
                logger.info(f"Successfully sent AI reply email to {email_data['from']}")

    # After processing all emails, find the maximum date and update the company's last_email_processed_at
    if emails:
        from email.utils import parsedate_to_datetime
        max_date = max(
            parsedate_to_datetime(email['date'])
            for email in emails
        )
        logger.info(f"Updating last_email_processed_at for company '{company['name']}' ({company['id']}) to {max_date}")
        await update_last_processed_email_date(UUID(company['id']), max_date)

async def main():

    """Main function to process emails for all companies"""
    try:
        # Get all companies with email credentials
        companies = await get_companies_with_email_credentials()
        logger.info(f"Found {len(companies)} companies with email credentials added")
        
        # Process emails for each company
        for company in companies:
            try:
                await fetch_emails(company)
            except Exception as e:
                logger.error(f"Error processing company '{company['name']}' {company['id']}: {str(e)}")
                continue
            
            # Add small delay between companies to avoid rate limits
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 