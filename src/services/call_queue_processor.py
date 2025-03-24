import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID

from src.database import (
    get_running_campaign_runs,
    get_campaign_by_id,
    get_lead_by_id,
    get_company_by_id,
    update_campaign_run_status,
    update_campaign_run_progress,
    get_calls_initiated_count,
    get_next_calls_to_process,
    update_call_queue_item_status,
    get_pending_calls_count,
    supabase
)
from src.services.call_generation import generate_call_script
from src.services.email_generation import get_or_generate_insights_for_lead
from src.config import get_settings
from src.services.bland_calls import initiate_call

settings = get_settings()
logger = logging.getLogger(__name__)

async def process_call_queues():
    """Process call queues for all companies"""
    try:
        logger.info("Starting call queue processing")
        
        # Process companies in batches of 10
        page_size = 10
        start = 0
        
        while True:
            # Get paginated list of companies
            response = supabase.from_('companies')\
                .select('id')\
                .eq('deleted', False)\
                .range(start, start + page_size - 1)\
                .execute()
                
            if not response.data:
                logger.info("No more companies to process")
                break
                
            logger.info(f"Processing batch of {len(response.data)} companies")
            
            # Process queue for each company in this batch
            for company in response.data:
                await process_company_call_queue(UUID(company['id']))
            
            # Move to next page
            start += page_size
            
        logger.info("Call queue processing completed")
    except Exception as e:
        logger.error(f"Error processing call queues: {str(e)}")
        

async def process_company_call_queue(company_id: UUID):
    """Process the call queue for a specific company"""
    try:
        logger.info(f"Processing call queue for company {company_id}")
        
        # Check hourly limit
        hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        calls_initiated_last_hour = await get_calls_initiated_count(hour_ago)
        
        hourly_limit = 1000 # Bland limit: 1000 calls per hour
        if calls_initiated_last_hour >= hourly_limit:
            logger.info(f"Reached Bland's hourly limit ({calls_initiated_last_hour}/{hourly_limit})")
            return
        
        # Check daily limit
        day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        calls_initiated_last_day = await get_calls_initiated_count(day_ago)
        
        daily_limit = 2000 # Bland limit: 2000 calls per day
        if calls_initiated_last_day >= daily_limit:
            logger.info(f"Reached Bland's daily limit ({calls_initiated_last_day}/{daily_limit})")
            return
        
        # Calculate how many calls we can initiate in this batch
        hourly_remaining = hourly_limit - calls_initiated_last_hour
        daily_remaining = daily_limit - calls_initiated_last_day
        batch_size = min(hourly_remaining, daily_remaining, 10)  # Max 10 at once for safety
        
        if batch_size <= 0:
            logger.info(f"No capacity to initiate calls")
            return
        
        # Get next batch of calls to process
        queue_items = await get_next_calls_to_process(company_id, batch_size)
        
        if not queue_items:
            logger.info(f"No pending calls in queue for company {company_id}")
            return
        
        logger.info(f"Processing {len(queue_items)} calls for company {company_id}")
        
        # Get company details
        company = await get_company_by_id(company_id)
        if not company:
            logger.error(f"Company {company_id} not found")
            return
        
        # Process each queued call
        for queue_item in queue_items:
            await process_queued_call(queue_item, company)
        
        # Check if all calls for any campaign run are completed
        await check_calls_campaign_runs_completion(company_id)
        
    except Exception as e:
        logger.error(f"Error processing call queue for company {company_id}: {str(e)}")


async def process_queued_call(queue_item: dict, company: dict):
    """Process a single queued call"""
    try:
        # Mark as processing
        await update_call_queue_item_status(
            queue_id=UUID(queue_item['id']),
            status='processing'
        )
        
        # Get campaign and lead details
        campaign_id = UUID(queue_item['campaign_id'])
        lead_id = UUID(queue_item['lead_id'])
        campaign_run_id = UUID(queue_item['campaign_run_id'])
        processed_at = queue_item['processed_at']
        
        campaign = await get_campaign_by_id(campaign_id)
        lead = await get_lead_by_id(lead_id)
        
        if not campaign or not lead:
            logger.error(f"Campaign or lead not found for queue item {queue_item['id']}")
            await update_call_queue_item_status(
                queue_id=UUID(queue_item['id']),
                status='failed',
                processed_at=datetime.now(timezone.utc),
                error_message="Campaign or lead not found"
            )
            
            if processed_at is None:
                # Update campaign run progress only if the queue item was not processed before
                await update_campaign_run_progress(
                    campaign_run_id=campaign_run_id,
                    leads_processed=1,
                    increment=True
                )
            return
        
        # Check for phone numbers
        if not lead.get('phone_number'):
            logger.error(f"Lead {lead_id} has no phone number")
            await update_call_queue_item_status(
                queue_id=UUID(queue_item['id']),
                status='failed',
                processed_at=datetime.now(timezone.utc),
                error_message="Lead has no phone number"
            )

            if processed_at is None:
                # Update campaign run progress only if the queue item was not processed before
                await update_campaign_run_progress(
                    campaign_run_id=campaign_run_id,
                    leads_processed=1,
                    increment=True
                )
            return

        try:
            call_script = queue_item['call_script']

            # If the call script is not set, generate insights
            if not call_script:
                insights = await get_or_generate_insights_for_lead(lead)

                if insights:
                    # Generate personalized call script
                    call_script = await generate_call_script(lead, campaign, company, insights)
                    
                    if not call_script:
                        await update_call_queue_item_status(
                                queue_id=UUID(queue_item['id']),
                                status='failed',
                                processed_at=datetime.now(timezone.utc),
                                error_message="Failed to generate call script for lead"
                            )
                        return
                    else:
                        await update_call_queue_item_status(
                                queue_id=UUID(queue_item['id']),
                                status='processing',
                                call_script=call_script
                            )
                else:
                    await update_call_queue_item_status(
                            queue_id=UUID(queue_item['id']),
                            status='failed',
                            processed_at=datetime.now(timezone.utc),
                            error_message="Failed to generate insights for lead"
                        )
                    return
        
            # Initiate call with Bland AI
            await initiate_call(campaign, lead, call_script, campaign_run_id)

            # Mark as sent
            await update_call_queue_item_status(
                queue_id=UUID(queue_item['id']),
                status='sent',
                processed_at=datetime.now(timezone.utc)
            )
            
            if processed_at is None:
                # Update campaign run progress only if the queue item was not processed before
                await update_campaign_run_progress(
                    campaign_run_id=campaign_run_id,
                    leads_processed=1,
                    increment=True
                )
            
        except Exception as e:
            logger.error(f"Error processing call for {lead.get('phone_number')}: {str(e)}")
            
            # Increment retry count
            retry_count = queue_item.get('retry_count', 0) + 1
            max_retries = queue_item.get('max_retries', 3)
            
            if retry_count >= max_retries:
                # Mark as failed after max retries
                await update_call_queue_item_status(
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
                await supabase.table('call_queue')\
                    .update({
                        'status': 'pending',
                        'retry_count': retry_count,
                        'scheduled_for': next_attempt.isoformat(),
                        'error_message': str(e)
                    })\
                    .eq('id', str(queue_item['id']))\
                    .execute()
                    
    except Exception as e:
        logger.error(f"Error processing queued call {queue_item.get('id')}: {str(e)}")
        
        # Try to mark as failed
        try:
            await update_call_queue_item_status(
                queue_id=UUID(queue_item['id']),
                status='failed',
                processed_at=datetime.now(timezone.utc),
                error_message=f"Unexpected error: {str(e)}"
            )
            
            if processed_at is None:
                # Update campaign run progress only if the queue item was not processed before
                await update_campaign_run_progress(
                    campaign_run_id=campaign_run_id,
                    leads_processed=1,
                    increment=True
                )
        except:
            pass


async def check_calls_campaign_runs_completion(company_id: UUID):
    """Check if any campaign runs for this company are complete"""
    try:
        # Get all running 'call' campaign runs for the company
        running_runs = await get_running_campaign_runs(company_id, 'call')
        
        for run in running_runs:
            # Check if any pending calls remain for this run
            pending_count = await get_pending_calls_count(UUID(run['id']))
            
            if pending_count == 0:
                # Get the campaign run details to check for complete processing
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
                logger.info(f"Campaign run {run['id']} has {pending_count} pending calls, not marking as completed.")
    except Exception as e:
        logger.error(f"Error checking campaign run completion: {str(e)}") 