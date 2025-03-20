import logging
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from uuid import UUID
import asyncio

from fastapi import HTTPException
from src.database import (
    get_email_throttle_settings,
    get_next_emails_to_process,
    update_queue_item_status,
    get_emails_sent_count,
    get_pending_emails_count,
    get_running_campaign_runs,
    get_campaign_by_id,
    get_lead_by_id,
    get_company_by_id,
    update_campaign_run_status,
    update_campaign_run_progress,
    create_email_log,
    create_email_log_detail,
    get_email_queue_items,
    get_product_by_id,
    is_email_in_do_not_email_list,
    add_to_do_not_email_list
)
from src.services.email_generation import generate_company_insights, generate_email_content
from src.utils.smtp_client import SMTPClient
from src.utils.encryption import decrypt_password
from src.utils.email_utils import add_tracking_pixel
from src.services.perplexity_service import perplexity_service
from src.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

def _extract_name_from_email(email: str) -> str:
    """
    Extract name from email address and format it as a proper name
    (e.g., 'Jack Doe' from 'jack.doe@gmail.com')
    """
    # Get the part before @
    local_part = email.split('@')[0]
    
    # Replace common separators with spaces
    name = local_part.replace('.', ' ').replace('_', ' ').replace('-', ' ')
    
    # Split into parts and capitalize each part
    name_parts = [part.capitalize() for part in name.split() if part]
    
    # If we have at least one part, return the formatted name
    if name_parts:
        return ' '.join(name_parts)
    
    # Fallback to just capitalize the local part if splitting produces no valid parts
    return local_part.capitalize()

async def process_email_queues():
    """Process email queues for all companies"""
    try:
        logger.info("Starting email queue processing")
        
        # Get unique company IDs with pending emails using DISTINCT
        from src.database import supabase
        response = supabase.from_('email_queue')\
            .select('company_id')\
            .eq('status', 'pending')\
            .execute(count='exact', head=True, distinct=True)
            
        if not response.data:
            logger.info("No pending emails in queue for any company")
            return
            
        logger.info(f"Found {len(response.data)} companies with pending emails")
            
        # Process queue for each company
        for item in response.data:
            await process_company_email_queue(UUID(item['company_id']))
            
        logger.info("Email queue processing completed")
    except Exception as e:
        logger.error(f"Error processing email queues: {str(e)}")
        

async def process_company_email_queue(company_id: UUID):
    """Process the email queue for a specific company"""
    try:
        logger.info(f"Processing email queue for company {company_id}")
        
        # Get throttle settings
        throttle_settings = await get_email_throttle_settings(company_id)
        
        if not throttle_settings.get('enabled', True):
            logger.info(f"Throttling disabled for company {company_id}, skipping")
            return
        
        # Check hourly limit
        hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        emails_sent_last_hour = await get_emails_sent_count(company_id, hour_ago)
        
        hourly_limit = throttle_settings.get('max_emails_per_hour', 300)
        if emails_sent_last_hour >= hourly_limit:
            logger.info(f"Company {company_id} reached hourly limit ({emails_sent_last_hour}/{hourly_limit})")
            return
        
        # Check daily limit
        day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        emails_sent_last_day = await get_emails_sent_count(company_id, day_ago)
        
        daily_limit = throttle_settings.get('max_emails_per_day', 300)
        if emails_sent_last_day >= daily_limit:
            logger.info(f"Company {company_id} reached daily limit ({emails_sent_last_day}/{daily_limit})")
            return
        
        # Calculate how many emails we can send in this batch
        hourly_remaining = hourly_limit - emails_sent_last_hour
        daily_remaining = daily_limit - emails_sent_last_day
        batch_size = min(hourly_remaining, daily_remaining, 10)  # Max 10 at once for safety
        
        if batch_size <= 0:
            logger.info(f"No capacity to send emails for company {company_id}")
            return
        
        # Get next batch of emails to process
        queue_items = await get_next_emails_to_process(company_id, batch_size)
        
        if not queue_items:
            logger.info(f"No pending emails in queue for company {company_id}")
            return
        
        logger.info(f"Processing {len(queue_items)} emails for company {company_id}")
        
        # Get company details
        company = await get_company_by_id(company_id)
        if not company:
            logger.error(f"Company {company_id} not found")
            return
        
        # Process each queued email
        for queue_item in queue_items:
            await process_queued_email(queue_item, company)
        
        # Check if all emails for any campaign run are completed
        await check_campaign_runs_completion(company_id)
        
    except Exception as e:
        logger.error(f"Error processing email queue for company {company_id}: {str(e)}")


async def process_queued_email(queue_item: dict, company: dict):
    """Process a single queued email"""
    try:
        # Mark as processing
        await update_queue_item_status(
            queue_id=UUID(queue_item['id']),
            status='processing'
        )
        
        # Get campaign and lead details
        campaign_id = UUID(queue_item['campaign_id'])
        lead_id = UUID(queue_item['lead_id'])
        campaign_run_id = UUID(queue_item['campaign_run_id'])
        
        campaign = await get_campaign_by_id(campaign_id)
        lead = await get_lead_by_id(lead_id)
        
        if not campaign or not lead:
            logger.error(f"Campaign or lead not found for queue item {queue_item['id']}")
            await update_queue_item_status(
                queue_id=UUID(queue_item['id']),
                status='failed',
                processed_at=datetime.now(timezone.utc),
                error_message="Campaign or lead not found"
            )
            return
        
        # Check for email addresses
        if not lead.get('email'):
            logger.error(f"Lead {lead_id} has no email address")
            await update_queue_item_status(
                queue_id=UUID(queue_item['id']),
                status='failed',
                processed_at=datetime.now(timezone.utc),
                error_message="Lead has no email address"
            )
            return
            
        # Verify campaign template
        template = campaign.get('template')
        if not template:
            logger.error(f"Campaign {campaign_id} missing email template")
            await update_queue_item_status(
                queue_id=UUID(queue_item['id']),
                status='failed',
                processed_at=datetime.now(timezone.utc),
                error_message="Campaign missing email template"
            )
            return
        
        # Check if email is in do_not_email list before proceeding
        if await is_email_in_do_not_email_list(lead['email'], UUID(company['id'])):
            logger.warning(f"Email {lead['email']} is in do_not_email list, skipping")
            await update_queue_item_status(
                queue_id=UUID(queue_item['id']),
                status='skipped',
                processed_at=datetime.now(timezone.utc),
                error_message=f"Email {lead['email']} is in do_not_email list"
            )
            return

        try:
            subject = queue_item['subject']
            body = queue_item['email_body']

            body_without_tracking_pixel = body
        
            # Create email log
            email_log = await create_email_log(
                campaign_id=campaign_id,
                lead_id=lead_id,
                sent_at=datetime.now(timezone.utc),
                campaign_run_id=campaign_run_id
            )
            logger.info(f"Created email_log with id: {email_log['id']}")

            # Add tracking pixel to the email body
            final_body_with_tracking = add_tracking_pixel(body, email_log['id'])
            
            # Send email using SMTP client
            # Decrypt the password
            try:
                decrypted_password = decrypt_password(company["account_password"])
            except Exception as e:
                logger.error(f"Failed to decrypt email password: {str(e)}")
                await update_queue_item_status(
                    queue_id=UUID(queue_item['id']),
                    status='failed',
                    processed_at=datetime.now(timezone.utc),
                    error_message=f"Failed to decrypt password: {str(e)}"
                )
                return
                
            # Initialize SMTP client and send email
            async with SMTPClient(
                account_email=company["account_email"],
                account_password=decrypted_password,
                provider=company["account_type"]
            ) as smtp_client:
                # Extract name from email or use company name as fallback
                sender_name = None
                if company.get("account_email"):
                    sender_name = _extract_name_from_email(company["account_email"])
                
                # If extraction failed or produced a generic result, use company name
                account_email_local = company.get("account_email", "").split('@')[0].capitalize() if company.get("account_email") else ""
                if not sender_name or sender_name == account_email_local:
                    sender_name = company["name"]
                    
                # Send email with reply-to header
                await smtp_client.send_email(
                    to_email=lead['email'],
                    subject=subject,
                    html_content=final_body_with_tracking,
                    from_name=sender_name,  # Use extracted name or company name
                    email_log_id=email_log['id']
                )
                logger.info(f"Successfully sent email to {lead['email']} from {sender_name}")
                
                # Create email log detail
                await create_email_log_detail(
                    email_logs_id=email_log['id'],
                    message_id=None,
                    email_subject=subject,
                    email_body=body_without_tracking_pixel,
                    sender_type='assistant',
                    sent_at=datetime.now(timezone.utc),
                    from_name=sender_name,  # Use the same sender name here
                    from_email=company['account_email'],
                    to_email=lead['email']
                )
                logger.info(f"Created email log detail for email_log_id: {email_log['id']}")
            
            # Mark as sent
            await update_queue_item_status(
                queue_id=UUID(queue_item['id']),
                status='sent',
                processed_at=datetime.now(timezone.utc)
            )
            
            # Update campaign run progress
            await update_campaign_run_progress(
                campaign_run_id=campaign_run_id,
                leads_processed=1,
                increment=True
            )
            
        except Exception as e:
            logger.error(f"Error processing email for {lead.get('email')}: {str(e)}")
            
            # Increment retry count
            retry_count = queue_item.get('retry_count', 0) + 1
            max_retries = queue_item.get('max_retries', 3)
            
            if retry_count >= max_retries:
                # Mark as failed after max retries
                await update_queue_item_status(
                    queue_id=UUID(queue_item['id']),
                    status='failed',
                    processed_at=datetime.now(timezone.utc),
                    error_message=str(e)
                )
            else:
                # Schedule for retry with exponential backoff
                retry_delay = 2 ** retry_count  # 2, 4, 8, 16... minutes
                next_attempt = datetime.now(timezone.utc) + timedelta(minutes=retry_delay)
                
                # Update retry count and reschedule
                from src.database import supabase
                await supabase.table('email_queue')\
                    .update({
                        'status': 'pending',
                        'retry_count': retry_count,
                        'scheduled_for': next_attempt.isoformat(),
                        'error_message': str(e)
                    })\
                    .eq('id', str(queue_item['id']))\
                    .execute()
                    
    except Exception as e:
        logger.error(f"Error processing queued email {queue_item.get('id')}: {str(e)}")
        
        # Try to mark as failed
        try:
            await update_queue_item_status(
                queue_id=UUID(queue_item['id']),
                status='failed',
                processed_at=datetime.now(timezone.utc),
                error_message=f"Unexpected error: {str(e)}"
            )
        except:
            pass


async def check_campaign_runs_completion(company_id: UUID):
    """Check if any campaign runs for this company are complete"""
    try:
        # Get all running campaign runs for the company
        running_runs = await get_running_campaign_runs(company_id)
        
        for run in running_runs:
            # Check if any pending emails remain for this run
            pending_count = await get_pending_emails_count(UUID(run['id']))
            
            if pending_count == 0:
                # Get the campaign run details to check for complete processing
                from src.database import supabase
                campaign_run = supabase.table('campaign_runs')\
                    .select('*')\
                    .eq('id', str(run['id']))\
                    .execute()
                    
                if campaign_run.data and len(campaign_run.data) > 0:
                    campaign_run_data = campaign_run.data[0]
                    leads_processed = campaign_run_data.get('leads_processed', 0) or 0
                    leads_total = campaign_run_data.get('leads_total', 0) or 0
                    
                    # If we have processed all leads or there are no more pending emails,
                    # mark the campaign run as completed
                    if leads_processed >= leads_total:
                        # Mark campaign run as completed
                        await update_campaign_run_status(
                            campaign_run_id=UUID(run['id']),
                            status="completed"
                        )
                        logger.info(f"Campaign run {run['id']} marked as completed. Processed {leads_processed}/{leads_total} leads.")
                    else:
                        logger.info(f"Campaign run {run['id']} has no pending emails but only processed {leads_processed}/{leads_total} leads. Some emails may have failed.")
                else:
                    # We couldn't get the campaign run details, so mark as completed based on queue only
                    await update_campaign_run_status(
                        campaign_run_id=UUID(run['id']),
                        status="completed"
                    )
                    logger.info(f"Campaign run {run['id']} marked as completed based on empty queue.")
            else:
                logger.info(f"Campaign run {run['id']} has {pending_count} pending emails, not marking as completed.")
    except Exception as e:
        logger.error(f"Error checking campaign run completion: {str(e)}") 