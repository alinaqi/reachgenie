import logging
import asyncio
from typing import Dict
from uuid import UUID
from datetime import datetime, timezone

# Import the new enhanced reminder system
from src.services.advanced_reminders import generate_enhanced_reminder

from src.config import get_settings
from src.database import (
    get_email_logs_reminder, 
    get_first_email_detail,
    update_reminder_sent_status,
    get_campaigns,
    get_company_by_id,
    add_email_to_queue,
    get_email_log_by_id,
    get_campaign_by_id
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure settings
settings = get_settings()

async def send_reminder_emails(company: Dict, reminder_type: str) -> None:
    """
    Send reminder emails for a single company's campaign using the enhanced reminder system
    
    Args:
        company: Company data dictionary containing email credentials and settings
        reminder_type: Type of reminder to send (None, 'r1' through 'r6')
    """
    try:
        company_id = UUID(company['id'])
        company_info = await get_company_by_id(company_id)

        logger.info(f"Processing reminder emails for company '{company['name']}' ({company_id})")
        logger.info(f"Reminder type: {reminder_type} (generating next in sequence)")
        
        # Process each email log for the company
        for log in company['logs']:
            try:
                email_log_id = UUID(log['email_log_id'])
                
                # Set the next reminder type based on current type
                # This will be used to determine the next reminder in sequence
                if reminder_type is None:
                    next_reminder = 'r1'
                else:
                    current_num = int(reminder_type[1])  # Extract number from 'r1', 'r2', etc.
                    next_reminder = f'r{current_num + 1}'
                
                # Get the original email content
                original_email = await get_first_email_detail(email_log_id)
                if not original_email:
                    logger.warning(f"No email detail found for email log {email_log_id}")
                    continue
                
                # Get the full email log data for behavioral analysis
                email_log = await get_email_log_by_id(email_log_id)
                campaign = await get_campaign_by_id(email_log['campaign_id'])
                
                # Generate enhanced reminder using the new system
                try:
                    logger.info(f"Generating enhanced reminder for log {email_log_id}, type: {reminder_type}")
                    
                    subject, reminder_content = await generate_enhanced_reminder(
                        email_log=email_log,
                        lead_id=log['lead_id'],
                        campaign_id=email_log['campaign_id'],
                        company_id=company_id,
                        original_email_body=original_email['email_body'],
                        reminder_type=reminder_type
                    )
                    
                    logger.info(f"Successfully generated enhanced reminder")
                    #logger.debug(f"Subject: {subject}")
                    #logger.debug(f"Preview: {reminder_content[:100]}...")
                    
                except Exception as e:
                    logger.error(f"Failed to generate enhanced reminder, falling back to subject line: {str(e)}")
                    # Fallback subject if generation fails
                    subject = f"Re: {original_email['email_subject']}" if not original_email['email_subject'].startswith('Re:') else original_email['email_subject']
                    reminder_content = None
                
                if not reminder_content:
                    logger.error(f"No reminder content generated for email log {email_log_id}")
                    continue

                # Add email to queue with behavioral insights
                await add_email_to_queue(
                    company_id=campaign['company_id'],
                    campaign_id=email_log['campaign_id'],
                    campaign_run_id=email_log['campaign_run_id'],
                    lead_id=email_log['lead_id'],
                    subject=subject,
                    body=reminder_content,
                    email_log_id=email_log_id
                )                
                
                # Update the reminder status in database with current timestamp, the definition of reminder sent here means that the email was added to the queue
                current_time = datetime.now(timezone.utc)
                success = await update_reminder_sent_status(
                    email_log_id=email_log_id,
                    reminder_type=next_reminder,
                    last_reminder_sent_at=current_time
                )
                
                if success:
                    logger.info(f"Successfully queued enhanced reminder for log {email_log_id} to {log['lead_email']}")
                else:
                    logger.error(f"Failed to update reminder status for log {email_log_id}")
                
            except Exception as e:
                logger.error(f"Error processing log {log['email_log_id']}: {str(e)}")
                continue
        
    except Exception as e:
        logger.error(f"Error processing reminders for company {company['name']}: {str(e)}")

async def main():
    """Main function to process reminder emails for all companies with enhanced 7-stage system"""
    try:
        page_number = 1
        while True:
            # Get campaigns with pagination
            campaigns_response = await get_campaigns(
                campaign_types=["email", "email_and_call"], 
                page_number=page_number, 
                limit=20
            )
            campaigns = campaigns_response['items']
            
            if not campaigns:
                break
                
            logger.info(f"Processing page {page_number} of campaigns")
            logger.info(f"Found {len(campaigns)} campaigns on this page (Total: {campaigns_response['total']})")

            for campaign in campaigns:
                logger.info(f"Processing campaign '{campaign['name']}' ({campaign['id']})")
                logger.info(f"Number of reminders configured: {campaign['number_of_reminders']}")
                
                # Ensure we don't exceed 7 reminders
                num_reminders = min(campaign.get('number_of_reminders', 0), 7)
                
                if num_reminders == 0:
                    logger.info(f"Campaign has no reminders configured, skipping")
                    continue
                
                # Generate reminder types dynamically based on campaign's number_of_reminders
                # None represents the state before first reminder is sent
                reminder_types = [None] + [f'r{i}' for i in range(1, num_reminders)]
                
                logger.info(f"Will process {len(reminder_types)} reminder stages: {reminder_types}")

                # Create dynamic mapping for reminder type descriptions
                reminder_descriptions = {None: 'first (gentle check-in)'}
                strategies = ['value addition', 'social proof', 'problem agitation', 
                             'alternative approach', 'last value drop', 'professional breakup']
                
                for i in range(1, num_reminders):
                    strategy_name = strategies[i-1] if i-1 < len(strategies) else f'{i+1}th'
                    if i == num_reminders - 1:
                        reminder_descriptions[f'r{i}'] = f'{i+1}th and final ({strategy_name})'
                    else:
                        reminder_descriptions[f'r{i}'] = f'{i+1}th ({strategy_name})'

                # Process each reminder type
                for reminder_type in reminder_types:
                    next_reminder_desc = reminder_descriptions.get(reminder_type, 'next')
                    logger.info(f"\nProcessing {next_reminder_desc} reminder for campaign")

                    # Process email logs with keyset pagination
                    last_id = None
                    total_processed = 0
                    
                    while True:
                        # Fetch email logs using keyset pagination
                        email_logs_response = await get_email_logs_reminder(
                            campaign['id'],
                            campaign['days_between_reminders'],
                            reminder_type,
                            last_id=last_id,
                            limit=20
                        )
                        
                        email_logs = email_logs_response['items']
                        if not email_logs:
                            logger.info(f"No email logs found for {next_reminder_desc} reminder")
                            break
                            
                        total_processed += len(email_logs)
                        logger.info(f"Processing batch of {len(email_logs)} email logs for {next_reminder_desc} reminder (Total: {total_processed})")

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
                        
                        # Process reminder for each company
                        for company_data in company_logs.values():
                            await send_reminder_emails(company_data, reminder_type)
                            
                        # Break if no more records
                        if not email_logs_response['has_more']:
                            break
                            
                        # Update cursor for next page
                        last_id = email_logs_response['last_id']
                        
                    logger.info(f"Completed processing {next_reminder_desc} reminder. Total processed: {total_processed}")
            
            # Move to next page of campaigns
            page_number += 1
            
        logger.info("Enhanced reminder processing completed for all campaigns")
        
    except Exception as e:
        logger.error(f"Error in main reminder process: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting enhanced 7-stage reminder system...")
    asyncio.run(main())