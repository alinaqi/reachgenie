import logging
import asyncio
from typing import Dict
from uuid import UUID
from openai import AsyncOpenAI
from src.config import get_settings
from datetime import datetime, timezone

from src.utils.smtp_client import SMTPClient
from src.database import (
    get_email_logs_for_reminder1, 
    get_first_email_detail,
    create_email_log_detail,
    update_reminder_sent_status
)
from src.utils.encryption import decrypt_password

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure OpenAI
settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)

async def get_reminder_content(original_email_body: str) -> str:
    """
    Generate reminder email content using OpenAI based on the original email
    """
    system_prompt = """You are an AI assistant helping to generate reminder emails. 
    Your task is to create a polite and professional follow-up email that references 
    the original email content while maintaining a courteous tone.
    
    Important guidelines:
    1. Generate ONLY the email body content
    2. DO NOT include any subject line
    3. DO NOT include any signature, name, or "Best regards" type closings
    4. DO NOT use placeholder values like [Your Name]
    5. End the email naturally with the last sentence of the message"""
    
    user_prompt = f"""Please generate a reminder email body for the following original email.
    The reminder should:
    1. Reference the original email content
    2. Be professional and courteous
    3. Express interest in following up
    4. Ask if they had a chance to review the previous email
    5. Ask if they have any questions or concerns
    
    Remember:
    - Only provide the email body content
    - Do not include subject, signature, or any placeholder values
    - End with the last meaningful sentence
    
    Original email:
    {original_email_body}
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        reminder_content = response.choices[0].message.content.strip()
        return reminder_content
    except Exception as e:
        logger.error(f"Error generating reminder content: {str(e)}")
        return None

async def send_reminder1_emails(company: Dict) -> None:
    """
    Send reminder1 emails for a single company's campaign
    
    Args:
        company: Company data dictionary containing email credentials and settings
    """
    try:
        company_id = UUID(company['id'])
        logger.info(f"Processing reminder1 emails for company '{company['name']}' ({company_id})")
        
        # Decrypt the password
        try:
            decrypted_password = decrypt_password(company['account_password'])
        except Exception as e:
            logger.error(f"Failed to decrypt password for company {company_id}: {str(e)}")
            return
            
        # Initialize SMTP client
        async with SMTPClient(
            account_email=company['account_email'],
            account_password=decrypted_password,
            provider=company['account_type']
        ) as smtp_client:
            # Process each email log for the company
            for log in company['logs']:
                try:
                    email_log_id = UUID(log['email_log_id'])
                    
                    # Get the original email content
                    original_email = await get_first_email_detail(email_log_id)
                    if not original_email:
                        logger.warning(f"No email detail found for email log {email_log_id}")
                        continue
                    
                    # Generate reminder content using LLM
                    reminder_content = await get_reminder_content(original_email['email_body'])
                    if not reminder_content:
                        logger.error(f"Failed to generate reminder content for email log {email_log_id}")
                        continue
                    
                    logger.info(f"Generated reminder content for email log {email_log_id}")
                    logger.info(f"Generated reminder: {reminder_content}")
                    
                    # Create subject line for reminder
                    subject = f"Re: {original_email['email_subject']}" if not original_email['email_subject'].startswith('Re:') else original_email['email_subject']
                    
                    # Create email log detail for the reminder
                    await create_email_log_detail(
                        email_logs_id=email_log_id,
                        message_id=None,  # New message, no ID yet
                        email_subject=subject,
                        email_body=reminder_content,
                        sender_type='assistant',
                        sent_at=datetime.now(timezone.utc),
                        from_name=company['name'],
                        from_email=company['account_email'],
                        to_email=log['lead_email'],  # Using lead's email address
                        reminder_type='r1'  # First reminder type
                    )
                    
                    # Send the reminder email
                    await smtp_client.send_email(
                        to_email=log['lead_email'],  # Using lead's email address
                        subject=subject,
                        html_content=reminder_content,
                        from_name=company['name'],
                        email_log_id=email_log_id
                    )
                    
                    # Update the reminder status in database with current timestamp
                    current_time = datetime.now(timezone.utc)
                    success = await update_reminder_sent_status(
                        email_log_id=email_log_id,
                        reminder_type='r1',
                        last_reminder_sent_at=current_time
                    )
                    if success:
                        logger.info(f"Successfully updated reminder status for log {email_log_id}")
                    else:
                        logger.error(f"Failed to update reminder status for log {email_log_id}")
                    
                    logger.info(f"Successfully sent reminder email for log {email_log_id} to {log['lead_email']}")
                    
                except Exception as e:
                    logger.error(f"Error processing log {log['email_log_id']}: {str(e)}")
                    continue
        
    except Exception as e:
        logger.error(f"Error processing reminders for company {company['name']}: {str(e)}")

async def main():
    """Main function to process reminder emails for all companies"""
    try:
        # Fetch all email logs that need first reminder
        email_logs = await get_email_logs_for_reminder1()
        logger.info(f"Found {len(email_logs)} email logs to process for first reminder")
        
        # Group email logs by company for batch processing
        company_logs = {}
        for log in email_logs:
            company_id = str(log['company_id'])
            if company_id not in company_logs:
                company_logs[company_id] = {
                    'id': company_id,
                    'name': log['company_name'],
                    'account_email': log['account_email'],
                    'account_password': log['account_password'],
                    'account_type': log['account_type'],
                    'logs': []
                }
            company_logs[company_id]['logs'].append(log)
        
        # Process reminder1 for each company
        for company_data in company_logs.values():
            await send_reminder1_emails(company_data)
            
    except Exception as e:
        logger.error(f"Error in main reminder process: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 