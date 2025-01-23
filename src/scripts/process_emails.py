import imaplib
import email
from email.header import decode_header
import logging
import asyncio
from typing import List, Dict
from datetime import datetime, timedelta
from uuid import UUID

from src.database import (
    get_companies_with_email_credentials,
    update_last_processed_email_date,
    create_email_log,
    create_email_log_detail,
    decrypt_password
)

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

# Function to fetch the oldest Unseen N emails from IMAP Server based on the since date
async def fetch_emails(company: Dict):
    """
    Process emails for a single company
    
    Args:
        company: Company data dictionary
    """
    max_emails = 5 # Number of emails to fetch per run
    company_id = UUID(company['id'])
    logger.info(f"Processing emails for company '{company['name']}' ({company_id})")

    try:
        # Get the last processed email date
        last_processed_date = company.get('last_email_processed_at')
        if not last_processed_date:
            raise ValueError(f"No last processed email date found for company '{company['name']}'. Please set an initial processing date.")
        
        last_processed_date = last_processed_date.strftime("%d-%b-%Y")
        #print(last_processed_date)

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
        imap.select("INBOX")

        # Fetch the emails since a specified date, ordered oldest first, and filter unseen emails
        # 'Since' ensure that only emails received on or after the since date are retrieved and processed.
        status, messages = imap.search(None, f'UNSEEN SINCE "{last_processed_date}"')

        if status != "OK":
            raise Exception("Failed to retrieve emails")

        # Get the list of email IDs
        email_ids = messages[0].split()
        
        if not email_ids:
            logger.info(f"No unseen emails found for company '{company['name']}' since: {last_processed_date}")
            return []

        # Fetch the oldest X number of email IDs (reverse slicing)
        oldest_email_ids = email_ids[:max_emails]

        email_data = []

        for email_id in oldest_email_ids:
            # Fetch the email by ID
            res, msg = imap.fetch(email_id, "(RFC822)")

            if res != "OK":
                raise Exception(f"Failed to fetch email with ID {email_id}")

            for response_part in msg:
                if isinstance(response_part, tuple):
                    # Parse the raw email content
                    msg_obj = email.message_from_bytes(response_part[1])

                    # Decode email fields
                    subject = decode_header_value(msg_obj.get("Subject"))
                    from_ = decode_header_value(msg_obj.get("From"))
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

                    email_data.append({
                        "Subject": subject,
                        "MessageID": message_id,
                        "From": from_,
                        "To": to,
                        "Body": body,
                        "Date": date
                    })

        # Logout and close the connection
        imap.logout()

        await process_emails(email_data)

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
    emails: List[Dict]
) -> None:
    
   for email_data in emails:
       print(email_data)
       # Do all the processing here
       # 1. Fetch the To: email address and identifier after the +, it will be our email_log_id
       # 2. Add a message against this email_log_id in email_log_detail table
       # 3. Generate an AI message for this email reply, save the reply in email_log_detail table, and send the reply via SMTP Client Library 

async def main():

    """Main function to process emails for all companies"""
    try:
        # Get all companies with email credentials
        companies = await get_companies_with_email_credentials()
        logger.info(f"Found {len(companies)} companies with email credentials")
        
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