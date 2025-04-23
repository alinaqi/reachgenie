import imaplib
import email
from email.header import decode_header
import logging
import asyncio
from typing import List, Dict
from datetime import datetime, timezone, timedelta
from uuid import UUID
from src.utils.smtp_client import SMTPClient
from src.config import get_settings
from openai import AsyncOpenAI

from src.database import (
    get_companies_with_email_credentials,
    create_email_log_detail,
    update_email_log_has_replied,
    update_last_processed_uid,
    get_campaign_from_email_log,
    add_to_do_not_email_list,
    update_call_reminder_eligibility,
    get_email_log_by_id,
    get_campaign_by_id,
    get_lead_by_id,
    add_email_to_queue
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
    max_emails = 10 # Number of emails to fetch per run
    company_id = UUID(company['id'])

    try:
        # Decrypt email password
        try:
            decrypted_password = decrypt_password(company['account_password'])
        except Exception as e:
            logger.error(f"Failed to decrypt password for company '{company['name']}' ({company_id}): {str(e)}")
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

        last_processed_uid = company.get('last_processed_uid')
        if not last_processed_uid:
            # if no last_processed_uid is found, fetch all emails from two days ago
            # 'Since' ensure that only emails received on or after the since date are fetched
            last_processed_date = datetime.now(timezone.utc) - timedelta(days=2)
            logger.info(f"No last_processed_uid found for company '{company['name']}' ({company_id}). Fetching all emails from two days ago.")
        
            last_processed_date_str = last_processed_date.strftime("%d-%b-%Y")
            logger.info(f"Processing emails since {last_processed_date_str} for company '{company['name']}' ({company_id})")
            
            # Use uid('search') instead of search() for consistency
            status, messages = imap.uid('search', None, f'SINCE "{last_processed_date_str}"')
        else:
            x = int(last_processed_uid) + 1
            logger.info(f"Processing emails from UID {x} for company '{company['name']}' ({company_id})")
            # Get UIDs after the last processed one using uid() command with UID keyword
            # Using NOT UID 1:(x-1) to ensure we only get UIDs >= x
            status, messages = imap.uid('search', None, f'NOT (UID 1:{x-1})')

        if status != "OK":
            raise Exception("Failed to retrieve emails")

        # Get the list of email IDs (these are now UIDs in both cases)
        email_ids = messages[0].split()
        
        if not email_ids:
            logger.info(f"No emails found for company '{company['name']}'")
            return []

        total_emails = len(email_ids)
        logger.info(f"Found {total_emails} emails for company '{company['name']}', processing up to {max_emails} in this run")

        # Fetch the oldest n number of email IDs (reverse slicing)
        oldest_email_ids = email_ids[:max_emails]

        email_data = []

        # Fetch only the limited UIDs
        for email_id in oldest_email_ids:
            # Fetch the email by UID
            #res, msg = imap.fetch(email_id, "(RFC822)")
            res, msg = imap.uid('fetch', email_id, "(RFC822)")
            
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
                    references = msg_obj.get("References")  # Get References header

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
                        "references": references,  # Add References to the data
                        "from": sender_email,
                        "from_name": sender_name,
                        "from_full": from_field,
                        "to": to,
                        "body": body,
                        "date": date,
                        "uid": email_id.decode('utf-8')  # Add UID to email data
                    })

        # Logout and close the connection
        imap.logout()

        # Process the emails
        await process_emails(email_data, company, decrypted_password)        

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

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
            logger.info(f"Email Subject: {email_data['subject']}")
            logger.info(f"Extracted email_log_id from 'to' field: {email_log_id}")

        except (IndexError, ValueError) as e:
            logger.info(f"Email Subject: {email_data['subject']}")
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
            sent_at=sent_at,
            sender_type='user', # This is a user reply
            from_name=email_data['from_name'],
            from_email=email_data['from'],
            to_email=email_data['to']
        )
        logger.info(f"Successfully created email_log_detail for message_id: {email_data['message_id']}")

        # Update has_replied status to True
        success = await update_email_log_has_replied(email_log_id)

        # Get the campaign and lead
        email_log_obj = await get_email_log_by_id(email_log_id)
        campaign_obj = await get_campaign_by_id(email_log_obj['campaign_id'])
        lead_obj = await get_lead_by_id(email_log_obj['lead_id'])

        # If the campaign is an "email_and_call" campaign, update the is_reminder_eligible to False in the 'calls' table, so that the call reminder/retry is not sent, 
        # since the person has already replied to the email
        if campaign_obj['type'] == 'email_and_call':
            await update_call_reminder_eligibility(
                campaign_id=campaign_obj['id'],
                campaign_run_id=email_log_obj['campaign_run_id'],
                lead_id=lead_obj['id'],
                is_reminder_eligible=False
            )
        
        if success:
            logger.info(f"Successfully updated has_replied status for email_log_id: {email_log_id}")
        else:
            logger.error(f"Failed to update has_replied status for email_log_id: {email_log_id}")

        # Check for unsubscribe request using GPT-4o-mini
        settings = get_settings()
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        try:
            logger.info(f"Checking for unsubscribe request in email: {email_data['subject']}")
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an assistant that analyzes email content to determine if the user is explicitly requesting to unsubscribe or opt-out from emails. Look for phrases like 'please unsubscribe me', 'remove me from your list', 'stop sending emails', etc. Do NOT consider standard unsubscribe links in email footers as unsubscribe requests. Only detect when a human is actively asking to be removed from communications. Respond with 'yes' if the email contains a clear unsubscribe request from the user, and 'no' if it doesn't."},
                    {"role": "user", "content": f"Subject: {email_data['subject']}\n\nBody: {email_data['body']}\n\nDoes this email contain an explicit request from the user to unsubscribe, opt-out, stop receiving emails, or any similar request?"}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            unsubscribe_check = response.choices[0].message.content.strip().lower()
            logger.info(f"Unsubscribe check result: {unsubscribe_check}")
            
            if unsubscribe_check == "yes":
                logger.info(f"Unsubscribe request detected from {email_data['from']} - adding to do_not_email list")
                company_id = UUID(company['id'])
                result = await add_to_do_not_email_list(
                    email=email_data['from'],
                    reason='unsubscribe_request',
                    company_id=company_id
                )
                
                if result.get('success'):
                    logger.info(f"Successfully added {email_data['from']} to do_not_email list for company {company['name']}")
                    
                    # Send confirmation email about unsubscription
                    async with SMTPClient(
                        account_email=company['account_email'],
                        account_password=decrypted_password,
                        provider=company['account_type']
                    ) as smtp_client:
                        unsubscribe_confirmation = f"""
                        <html>
                        <body>
                            <p>Hello {email_data['from_name'] or 'there'},</p>
                            <p>We've received your request to unsubscribe from our emails. You have been successfully removed from our email list.</p>
                            <p>If you have any questions or if this was done in error, please contact us.</p>
                            <p>Best regards</p>
                        </body>
                        </html>
                        """
                        
                        await smtp_client.send_email(
                            to_email=email_data['from'],
                            subject="Unsubscribe Confirmation",
                            html_content=unsubscribe_confirmation,
                            from_name=company["name"],
                            email_log_id=email_log_id,
                            in_reply_to=email_data['message_id'],
                            references=f"{email_data['references']} {email_data['message_id']}" if email_data['references'] else email_data['message_id']
                        )
                        logger.info(f"Sent unsubscribe confirmation to {email_data['from']}")
                    
                    # Skip AI reply since we've already sent an unsubscribe confirmation
                    continue
                else:
                    logger.error(f"Failed to add {email_data['from']} to do_not_email list: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"Error checking for unsubscribe request: {str(e)}")
            # Continue with normal processing if unsubscribe check fails

        # Get campaign details to get the template
        campaign = await get_campaign_from_email_log(email_log_id)
        if not campaign:
            logger.error(f"Failed to get campaign for email_log_id: {email_log_id}")
            continue

        # Get the template
        template = campaign.get('template')
        if not template:
            logger.error(f"Campaign {campaign['id']} missing email template")
            continue
        
        auto_reply_enabled = campaign.get('auto_reply_enabled', False)
        if not auto_reply_enabled:
            logger.info(f"Auto reply is not enabled for campaign {campaign['id']}. Skipping AI reply.")
            continue

        # Generate AI reply
        ai_reply = await generate_ai_reply(email_log_id, email_data)

        if ai_reply:
            # Process the AI reply
            response_subject = f"Re: {email_data['subject']}" if not email_data['subject'].startswith('Re:') else email_data['subject']
            
            # Replace {email_body} placeholder in template with generated AI reply
            final_body = template.replace("{email_body}", ai_reply)

            email_log = await get_email_log_by_id(email_log_id)
            campaign = await get_campaign_by_id(email_log['campaign_id'])

            # Add email to queue
            await add_email_to_queue(
                    company_id=campaign['company_id'],
                    campaign_id=email_log['campaign_id'],
                    campaign_run_id=email_log['campaign_run_id'],
                    lead_id=email_log['lead_id'],
                    subject=response_subject,
                    body=final_body,
                    email_log_id=email_log_id,
                    message_id=email_data['message_id'],
                    reference_ids=email_data['references']
                )

    # After processing all emails, find the maximum uid and update the company's last_processed_uid
    if emails:
        max_uid = max(int(email['uid']) for email in emails)
        logger.info(f"Updating last_processed_uid for company '{company['name']}' ({company['id']}) to {max_uid}")
        await update_last_processed_uid(UUID(company['id']), str(max_uid))

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