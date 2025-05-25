import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID

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
    create_email_log,
    create_email_log_detail,
    is_email_in_do_not_email_list,
    add_call_to_queue,
    get_email_log_by_id,
    get_processed_leads_count,
    supabase,
    check_existing_email_log_record
)
from src.services.call_generation import generate_call_script
from src.services.email_generation import generate_email_content, get_or_generate_insights_for_lead
from src.utils.smtp_client import SMTPClient
from src.utils.encryption import decrypt_password
from src.utils.email_utils import add_tracking_pixel
from src.config import get_settings
from fastapi import HTTPException

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
        
        # Process companies in batches of 10
        page_size = 10
        start = 0
        
        while True:
            try:
                # Get paginated list of companies with email credentials
                response = supabase.from_('companies')\
                    .select('id')\
                    .not_.is_('account_email', 'null')\
                    .not_.is_('account_password', 'null')\
                    .eq('deleted', False)\
                    .range(start, start + page_size - 1)\
                    .execute()
                    
                if not response.data:
                    logger.info("No more companies to process")
                    break
                    
                logger.info(f"Processing batch of {len(response.data)} companies")
                
                # Process queue for each company in this batch
                for company in response.data:
                    try:
                        await process_company_email_queue(UUID(company['id']))
                    except Exception as e:
                        logger.error(f"Error processing company {company['id']}: {str(e)}")
                        continue  # Continue with next company even if one fails
                
                # Move to next page
                start += page_size
            except Exception as e:
                logger.error(f"Error processing batch starting at {start}: {str(e)}")
                break  # Break the loop if we can't process a batch
            
        #logger.info("Email queue processing completed")
    except Exception as e:
        logger.error(f"Error processing email queues: {str(e)}")
    finally:
        # Ensure we log completion even if there was an error
        logger.info("Email queue processing completed")


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
        processed_at = queue_item['processed_at']
        email_log_id = queue_item['email_log_id']
        message_id = queue_item['message_id']
        reference_ids = queue_item['reference_ids']

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

            # If the email body or subject is not set, generate insights
            if not body or not subject:
                insights = await get_or_generate_insights_for_lead(lead)

                if insights:
                    subject, body = await generate_email_content(lead, campaign, company, insights)

                    if not body or not subject:
                        await update_queue_item_status(
                                queue_id=UUID(queue_item['id']),
                                status='failed',
                                processed_at=datetime.now(timezone.utc),
                                error_message="Failed to generate email content for lead"
                            )
                        return
                    else:
                        await update_queue_item_status(
                                queue_id=UUID(queue_item['id']),
                                status='processing',
                                subject=subject,
                                body=body
                            )
                else:
                    await update_queue_item_status(
                            queue_id=UUID(queue_item['id']),
                            status='failed',
                            processed_at=datetime.now(timezone.utc),
                            error_message="Failed to generate insights for lead"
                        )
                    return
            body_without_tracking_pixel = body
        
            # Create email log only if it doesn't exist already
            if email_log_id is not None:
                email_log = await get_email_log_by_id(email_log_id)
            else:
                existing_log = await check_existing_email_log_record(
                    campaign_id=campaign_id,
                    lead_id=lead_id,
                    campaign_run_id=campaign_run_id
                )
                
                if not existing_log:
                    email_log = await create_email_log(
                        campaign_id=campaign_id,
                        lead_id=lead_id,
                        sent_at=datetime.now(timezone.utc),
                        campaign_run_id=campaign_run_id
                    )
                    logger.info(f"Created email_log with id: {email_log['id']}")
                else:
                    # If log exists but we don't have the ID, fetch it
                    response = supabase.table('email_logs')\
                        .select('id')\
                        .eq('campaign_id', str(campaign_id))\
                        .eq('lead_id', str(lead_id))\
                        .eq('campaign_run_id', str(campaign_run_id))\
                        .execute()
                    if response.data:
                        email_log = await get_email_log_by_id(UUID(response.data[0]['id']))
                    else:
                        logger.error("Failed to retrieve existing email log")
                        raise Exception("Failed to retrieve existing email log")

            # Add tracking pixel to the email body
            final_body_with_tracking = add_tracking_pixel(body, email_log['id'])
            
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
            smtp_client = None
            try:
                smtp_client = SMTPClient(
                    account_email=company["account_email"],
                    account_password=decrypted_password,
                    provider=company["account_type"]
                )
                await smtp_client.connect()
                
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
                    email_log_id=email_log['id'],
                    in_reply_to=message_id if message_id else None,
                    references=f"{reference_ids} {message_id}" if reference_ids else (message_id if message_id is not None else None)
                )
                logger.info(f"Successfully sent email to {lead['email']} from {sender_name}")
            finally:
                if smtp_client:
                    try:
                        await smtp_client.disconnect()
                    except Exception as smtp_cleanup_error:
                        logger.warning(f"Error during SMTP cleanup: {str(smtp_cleanup_error)}")
                
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

            # Do not call if the email log id is set, because the email_log_id is set for reminder emails
            if campaign.get('type') == 'email_and_call' and campaign.get('trigger_call_on') == 'after_email_sent' and lead.get('phone_number') and email_log_id is None:
                
                logger.info(f"Adding call to queue for lead: {lead['name']} ({lead['phone_number']})")

                insights = await get_or_generate_insights_for_lead(lead)

                # Add to call queue
                call_script = await generate_call_script(lead, campaign, company, insights)

                await add_call_to_queue(
                    company_id=campaign['company_id'],
                    campaign_id=campaign['id'],
                    campaign_run_id=campaign_run_id,
                    lead_id=lead['id'],
                    call_script=call_script
                )
            
            # Mark as sent
            await update_queue_item_status(
                queue_id=UUID(queue_item['id']),
                status='sent',
                processed_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Error processing email for {lead.get('email')}", exc_info=True)
            
            # Increment retry count
            retry_count = queue_item.get('retry_count', 0) + 1
            max_retries = queue_item.get('max_retries', 3)
            
            if retry_count >= max_retries:
                # Mark as failed after max retries
                error_message = e.detail if isinstance(e, HTTPException) else str(e)
                await update_queue_item_status(
                    queue_id=UUID(queue_item['id']),
                    status='failed',
                    processed_at=datetime.now(timezone.utc),
                    error_message=error_message
                )

                supabase.table('email_queue')\
                    .update({
                        'retry_count': retry_count
                    })\
                    .eq('id', str(queue_item['id']))\
                    .execute()
            else:
                # Schedule for retry with exponential backoff
                retry_delay = 2 ** retry_count  # 2, 4, 8, 16... minutes
                next_attempt = datetime.now(timezone.utc) + timedelta(minutes=retry_delay)
                current_time = datetime.now(timezone.utc)
                
                error_message = e.detail if isinstance(e, HTTPException) else str(e)
                # Update retry count and reschedule
                supabase.table('email_queue')\
                    .update({
                        'status': 'pending',
                        'retry_count': retry_count,
                        'scheduled_for': next_attempt.isoformat(),
                        'processed_at': current_time.isoformat(),
                        'error_message': error_message
                    })\
                    .eq('id', str(queue_item['id']))\
                    .execute()
                    
    except Exception as e:
        logger.error(f"Error processing queued email {queue_item.get('id')}", exc_info=True)
        
        # Try to mark as failed
        try:
            error_message = e.detail if isinstance(e, HTTPException) else str(e)
            await update_queue_item_status(
                queue_id=UUID(queue_item['id']),
                status='failed',
                processed_at=datetime.now(timezone.utc),
                error_message=error_message
            )

        except:
            pass


async def check_campaign_runs_completion(company_id: UUID):
    """Check if any campaign runs for this company are complete"""
    try:
        # Get all running 'email' or 'email_and_call' campaign runs for the company
        running_runs = await get_running_campaign_runs(company_id, ['email', 'email_and_call'])
        
        for run in running_runs:
            # Check if any pending emails remain for this run
            pending_count = await get_pending_emails_count(UUID(run['id']))
            
            if pending_count == 0:
                # Get the campaign run details to check for complete processing
                campaign_run = supabase.table('campaign_runs')\
                    .select('*')\
                    .eq('id', str(run['id']))\
                    .execute()
                    
                if campaign_run.data and len(campaign_run.data) > 0:
                    campaign_run_data = campaign_run.data[0]

                    # Get processed leads count based on campaign type
                    leads_processed = await get_processed_leads_count(UUID(run['id']), "email")
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