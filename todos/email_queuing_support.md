# Email Queuing and Throttling Implementation

## Database Schema Updates

- [x] Create `email_queue` table with the following fields:
  - `id` (UUID, primary key)
  - `company_id` (UUID, foreign key)
  - `campaign_id` (UUID, foreign key)
  - `campaign_run_id` (UUID, foreign key)
  - `lead_id` (UUID, foreign key)
  - `status` (varchar: pending, processing, sent, failed)
  - `priority` (integer)
  - `created_at` (timestamp)
  - `scheduled_for` (timestamp)
  - `processed_at` (timestamp)
  - `retry_count` (integer)
  - `max_retries` (integer)
  - `error_message` (text)


### DB scheme additions

CREATE TABLE email_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id),
    campaign_id UUID NOT NULL REFERENCES campaigns(id),
    campaign_run_id UUID NOT NULL REFERENCES campaign_runs(id),
    lead_id UUID NOT NULL REFERENCES leads(id),
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, processing, sent, failed
    priority INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    error_message TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

CREATE TABLE email_throttle_settings (
    company_id UUID PRIMARY KEY REFERENCES companies(id),
    max_emails_per_hour INTEGER NOT NULL DEFAULT 50,
    max_emails_per_day INTEGER NOT NULL DEFAULT 500,
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- Index for efficient queue processing
CREATE INDEX email_queue_status_scheduled_idx ON email_queue(status, scheduled_for);
CREATE INDEX email_queue_company_status_idx ON email_queue(company_id, status);


- [x] Create `email_throttle_settings` table with the following fields:
  - `company_id` (UUID, primary key)
  - `max_emails_per_hour` (integer)
  - `max_emails_per_day` (integer)
  - `enabled` (boolean)
  - `created_at` (timestamp)
  - `updated_at` (timestamp)

- [x] Create necessary indexes for performance:
  - [x] Index on `email_queue(status, scheduled_for)`
  - [x] Index on `email_queue(company_id, status)`
  - [x] Index on `email_queue(campaign_run_id, status)`

## Database Functions

- [x] Implement `add_email_to_queue()` function
- [x] Implement `get_next_emails_to_process()` function
- [x] Implement `update_queue_item_status()` function
- [x] Implement `get_email_throttle_settings()` function 
- [x] Implement `update_email_throttle_settings()` function
- [x] Implement `get_emails_sent_count()` function
- [x] Implement `get_pending_emails_count()` function
- [x] Implement `get_running_campaign_runs()` function

## Campaign Execution Modifications

- [x] Modify `run_email_campaign()` function to queue emails instead of sending immediately
- [x] Update campaign progress tracking to work with queued emails
- [x] Implement `check_campaign_runs_completion()` function

### Campaign Execution Modification

async def run_email_campaign(campaign: dict, company: dict, campaign_run_id: UUID):
    """Handle email campaign processing by queueing emails instead of sending immediately"""
    # Validate credentials and campaign data as before
    
    # Get all leads having email addresses
    leads = await get_leads_with_email(campaign['id'])
    logger.info(f"Found {len(leads)} leads with emails for queueing")

    # Update campaign run with status running
    await update_campaign_run_status(
        campaign_run_id=campaign_run_id,
        status="running"
    )
    
    # Queue emails for each lead instead of sending immediately
    for lead in leads:
        try:
            if lead.get('email'):
                # Add to queue
                await add_email_to_queue(
                    company_id=campaign['company_id'],
                    campaign_id=campaign['id'],
                    campaign_run_id=campaign_run_id,
                    lead_id=lead['id']
                )
                logger.info(f"Email for lead {lead['email']} added to queue")
            else:
                logger.warning(f"Skipping lead with no email: {lead.get('id')}")
        except Exception as e:
            logger.error(f"Failed to queue email for {lead.get('email')}: {str(e)}")
            continue
    
    # Don't mark campaign as completed yet - it will be done by the queue processor
    # when all emails have been processed
    logger.info(f"All {len(leads)} emails queued for campaign {campaign['id']}")
    
    return

## Queue Processing System

- [x] Create a new module `src/services/email_queue_processor.py`
- [x] Implement `process_email_queues()` main function
- [x] Implement `process_company_email_queue()` function
- [x] Implement `process_queued_email()` function with:
  - [x] Content generation logic (reusing existing code)
  - [x] Email sending logic (reusing existing code)
  - [x] Error handling and retry mechanism
  - [x] Progress tracking updates

### Queue Management Functions

async def add_email_to_queue(company_id: UUID, campaign_id: UUID, campaign_run_id: UUID, lead_id: UUID, 
                            priority: int = 1, scheduled_for: datetime = None) -> dict:
    """Add an email to the processing queue"""
    if scheduled_for is None:
        scheduled_for = datetime.now(timezone.utc)
        
    queue_data = {
        'company_id': str(company_id),
        'campaign_id': str(campaign_id),
        'campaign_run_id': str(campaign_run_id),
        'lead_id': str(lead_id),
        'status': 'pending',
        'priority': priority,
        'scheduled_for': scheduled_for.isoformat()
    }
    
    response = supabase.table('email_queue').insert(queue_data).execute()
    return response.data[0]

async def get_next_emails_to_process(company_id: UUID, limit: int) -> List[dict]:
    """Get the next batch of emails to process for a company based on throttle settings"""
    # Get the current time
    now = datetime.now(timezone.utc)
    
    # Get pending emails that are scheduled for now or earlier, ordered by priority and creation time
    response = supabase.table('email_queue')\
        .select('*')\
        .eq('company_id', str(company_id))\
        .eq('status', 'pending')\
        .lte('scheduled_for', now.isoformat())\
        .order('priority', desc=True)\
        .order('created_at')\
        .limit(limit)\
        .execute()
        
    return response.data

async def update_queue_item_status(queue_id: UUID, status: str, processed_at: datetime = None, 
                                  error_message: str = None) -> dict:
    """Update the status of a queue item"""
    update_data = {'status': status}
    
    if processed_at:
        update_data['processed_at'] = processed_at.isoformat()
        
    if error_message:
        update_data['error_message'] = error_message
        
    response = supabase.table('email_queue')\
        .update(update_data)\
        .eq('id', str(queue_id))\
        .execute()
        
    return response.data[0]

async def get_email_throttle_settings(company_id: UUID) -> dict:
    """Get the email throttle settings for a company"""
    response = supabase.table('email_throttle_settings')\
        .select('*')\
        .eq('company_id', str(company_id))\
        .execute()
        
    if response.data:
        return response.data[0]
    
    # Return default settings if none exist
    return {
        'company_id': str(company_id),
        'max_emails_per_hour': 50,
        'max_emails_per_day': 500,
        'enabled': True
    }

async def get_emails_sent_count(company_id: UUID, start_time: datetime) -> int:
    """Get the count of emails sent for a company since the start time"""
    response = supabase.table('email_queue')\
        .select('id', count='exact')\
        .eq('company_id', str(company_id))\
        .eq('status', 'sent')\
        .gte('processed_at', start_time.isoformat())\
        .execute()
        
    return response.count

## Email Processing Script

- [x] Create a new script `src/scripts/process_email_queues.py`
- [x] Implement main execution function
- [x] Add proper error handling and logging
- [x] Add Bugsnag integration for error reporting

### Queue Processor Background Service


async def process_email_queues():
    """Process email queues for all companies"""
    # Get all active companies
    companies = await get_active_companies()
    
    for company in companies:
        # Process queue for each company
        await process_company_email_queue(company['id'])
        
async def process_company_email_queue(company_id: UUID):
    """Process the email queue for a specific company"""
    # Get throttle settings
    throttle_settings = await get_email_throttle_settings(company_id)
    
    if not throttle_settings['enabled']:
        logger.info(f"Throttling disabled for company {company_id}, skipping")
        return
    
    # Check hourly limit
    hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    emails_sent_last_hour = await get_emails_sent_count(company_id, hour_ago)
    
    if emails_sent_last_hour >= throttle_settings['max_emails_per_hour']:
        logger.info(f"Company {company_id} reached hourly limit ({emails_sent_last_hour}/{throttle_settings['max_emails_per_hour']})")
        return
    
    # Check daily limit
    day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    emails_sent_last_day = await get_emails_sent_count(company_id, day_ago)
    
    if emails_sent_last_day >= throttle_settings['max_emails_per_day']:
        logger.info(f"Company {company_id} reached daily limit ({emails_sent_last_day}/{throttle_settings['max_emails_per_day']})")
        return
    
    # Calculate how many emails we can send in this batch
    hourly_remaining = throttle_settings['max_emails_per_hour'] - emails_sent_last_hour
    daily_remaining = throttle_settings['max_emails_per_day'] - emails_sent_last_day
    batch_size = min(hourly_remaining, daily_remaining, 10)  # Max 10 at once for safety
    
    if batch_size <= 0:
        logger.info(f"No capacity to send emails for company {company_id}")
        return
    
    # Get next batch of emails to send
    queue_items = await get_next_emails_to_process(company_id, batch_size)
    
    if not queue_items:
        # No emails to process
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
    
    # Check if all emails for any campaign run are processed
    await check_campaign_runs_completion(company_id)

### Email Processing Function

async def process_queued_email(queue_item: dict, company: dict):
    """Process a single queued email"""
    try:
        # Mark as processing
        await update_queue_item_status(
            queue_id=queue_item['id'],
            status='processing'
        )
        
        # Get campaign and lead details
        campaign = await get_campaign_by_id(queue_item['campaign_id'])
        lead = await get_lead_by_id(queue_item['lead_id'])
        
        if not campaign or not lead:
            logger.error(f"Campaign or lead not found for queue item {queue_item['id']}")
            await update_queue_item_status(
                queue_id=queue_item['id'],
                status='failed',
                processed_at=datetime.now(timezone.utc),
                error_message="Campaign or lead not found"
            )
            return
        
        # Generate email content (similar to current flow)
        # Check for enriched data and generate insights as before
        insights = await get_lead_insights(lead)
        subject, body = await generate_email_content(lead, campaign, company, insights)
        
        # Prepare SMTP client
        decrypted_password = decrypt_password(company["account_password"])
        
        async with SMTPClient(
            account_email=company["account_email"],
            account_password=decrypted_password,
            provider=company["account_type"]
        ) as smtp_client:
            # Create email log
            email_log = await create_email_log(
                campaign_id=campaign['id'],
                lead_id=lead['id'],
                sent_at=datetime.now(timezone.utc)
            )
            
            # Add tracking pixel
            final_body_with_tracking = add_tracking_pixel(body, email_log['id'])
            
            # Send email
            await smtp_client.send_email(
                to_email=lead['email'],
                subject=subject,
                html_content=final_body_with_tracking,
                from_name=company["name"],
                email_log_id=email_log['id']
            )
            
            # Create email log detail
            await create_email_log_detail(
                email_logs_id=email_log['id'],
                message_id=None,
                email_subject=subject,
                email_body=body,  # Store without tracking pixel
                sender_type='assistant',
                sent_at=datetime.now(timezone.utc),
                from_name=company['name'],
                from_email=company['account_email'],
                to_email=lead['email']
            )
            
            # Mark as sent
            await update_queue_item_status(
                queue_id=queue_item['id'],
                status='sent',
                processed_at=datetime.now(timezone.utc)
            )
            
            # Update campaign run progress
            await update_campaign_run_progress(
                campaign_run_id=queue_item['campaign_run_id'],
                leads_processed=1,
                increment=True
            )
            
            logger.info(f"Email sent to {lead['email']} for campaign {campaign['id']}")
            
    except Exception as e:
        logger.error(f"Error processing queued email {queue_item['id']}: {str(e)}")
        
        # Increment retry count
        retry_count = queue_item.get('retry_count', 0) + 1
        max_retries = queue_item.get('max_retries', 3)
        
        if retry_count >= max_retries:
            # Mark as failed after max retries
            await update_queue_item_status(
                queue_id=queue_item['id'],
                status='failed',
                processed_at=datetime.now(timezone.utc),
                error_message=str(e)
            )
        else:
            # Schedule for retry with exponential backoff
            retry_delay = 2 ** retry_count  # 2, 4, 8, 16... minutes
            next_attempt = datetime.now(timezone.utc) + timedelta(minutes=retry_delay)
            
            # Update retry count and reschedule
            await supabase.table('email_queue')\
                .update({
                    'status': 'pending',
                    'retry_count': retry_count,
                    'scheduled_for': next_attempt.isoformat(),
                    'error_message': str(e)
                })\
                .eq('id', str(queue_item['id']))\
                .execute()

### Campaign Completion Checking

async def check_campaign_runs_completion(company_id: UUID):
    """Check if any campaign runs for this company are complete"""
    # Get all running campaign runs for the company
    running_runs = await get_running_campaign_runs(company_id)
    
    for run in running_runs:
        # Check if any pending emails remain for this run
        pending_count = await get_pending_emails_count(run['id'])
        
        if pending_count == 0:
            # Mark campaign run as completed
            await update_campaign_run_status(
                campaign_run_id=run['id'],
                status="completed"
            )
            logger.info(f"Campaign run {run['id']} marked as completed")

### Scheduled Task to Process Queues

# In a script file (src/scripts/process_email_queues.py)
async def main():
    """Main function to process email queues"""
    try:
        logger.info("Starting email queue processing")
        await process_email_queues()
        logger.info("Email queue processing completed")
    except Exception as e:
        logger.error(f"Error in email queue processing: {str(e)}")
        # You might want to use bugsnag.notify(e) here

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

*/5 * * * * /usr/bin/python /path/to/src/scripts/process_email_queues.py >> /var/log/email_queue.log 2>&1

## API Endpoints

- [x] Implement `GET /api/companies/{company_id}/email-throttle` endpoint
- [x] Implement `PUT /api/companies/{company_id}/email-throttle` endpoint
- [x] Update API documentation

### API Endpoints for Throttle Settings

@app.get("/api/companies/{company_id}/email-throttle", tags=["Campaigns & Emails"])
async def get_company_email_throttle(
    company_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Get email throttle settings for a company"""
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    settings = await get_email_throttle_settings(company_id)
    return settings

@app.put("/api/companies/{company_id}/email-throttle", tags=["Campaigns & Emails"])
async def update_company_email_throttle(
    company_id: UUID,
    settings: EmailThrottleSettings,
    current_user: dict = Depends(get_current_user)
):
    """Update email throttle settings for a company"""
    # Validate company access
    companies = await get_companies_by_user_id(current_user["id"])
    if not companies or not any(str(company["id"]) == str(company_id) for company in companies):
        raise HTTPException(status_code=404, detail="Company not found")
    
    updated_settings = await update_email_throttle_settings(
        company_id=company_id,
        max_emails_per_hour=settings.max_emails_per_hour,
        max_emails_per_day=settings.max_emails_per_day,
        enabled=settings.enabled
    )
    
    return updated_settings


## Models

- [x] Create `EmailThrottleSettings` Pydantic model
- [x] Create `EmailQueueItem` Pydantic model (if needed for API responses)

## Testing

- [ ] Write unit tests for queue management functions
- [ ] Write integration tests for the queue processor
- [ ] Test throttling logic with various settings
- [ ] Test error handling and retry logic
- [ ] Test campaign completion detection

## Deployment

- [ ] Configure cron job to run the queue processor script every 5 minutes
- [ ] Set up logging for the queue processor
- [ ] Configure monitoring for queue health

## Documentation

- [ ] Update API documentation with new endpoints
- [ ] Update email campaign flow documentation
- [ ] Create operations guide for managing the queue

## UI Updates (if applicable)

- [ ] Add UI for configuring throttle settings
- [ ] Add UI for monitoring queue status
- [ ] Add queue status indicators to campaign status page

## Optional Enhancements

- [ ] Implement campaign pause/resume functionality
- [ ] Add ability to prioritize specific campaigns or leads
- [ ] Add support for scheduled campaigns (specific date/time)
- [ ] Implement analytics for queue performance
- [ ] Add bulk operations for managing queued emails 


sequenceDiagram
    participant User
    participant API as API Server
    participant BG as Background Task
    participant Queue as Email Queue
    participant Processor as Queue Processor
    participant DB as Database
    participant SMTP
    
    User->>API: Create Campaign
    API->>DB: Store Campaign Details
    API->>User: Return Campaign ID
    User->>API: Run Campaign
    API->>BG: Start Campaign Execution
    API->>User: Confirmation
    
    BG->>DB: Get Leads
    
    loop For Each Lead
        BG->>Queue: Add Email to Queue
        Queue->>DB: Store in email_queue table
    end
    
    BG->>DB: Mark Campaign as Running
    
    loop Every 5 minutes
        Processor->>DB: Check Throttle Limits
        Processor->>DB: Get Next Batch of Emails
        
        loop For Each Queued Email
            Processor->>DB: Get Lead & Campaign Data
            Processor->>DB: Generate Email Content
            Processor->>SMTP: Send Email
            Processor->>DB: Log Email & Update Queue
        end
        
        Processor->>DB: Check Campaign Completion
    end