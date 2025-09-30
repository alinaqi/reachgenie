-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    password_hash TEXT NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add new columns to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT,
ADD COLUMN IF NOT EXISTS plan_type TEXT CHECK (plan_type IN ('trial', 'fixed', 'performance')),
ADD COLUMN IF NOT EXISTS lead_tier INTEGER CHECK (lead_tier IN (2500, 5000, 7500, 10000)),
ADD COLUMN IF NOT EXISTS channels_active JSONB,
ADD COLUMN IF NOT EXISTS subscription_id TEXT,
ADD COLUMN IF NOT EXISTS subscription_status TEXT CHECK (subscription_status IN ('active', 'past_due', 'canceled', 'incomplete', 'incomplete_expired', 'trialing', 'unpaid')),
ADD COLUMN IF NOT EXISTS billing_period_start TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS billing_period_end TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS subscription_canceled_at TIMESTAMP WITH TIME ZONE;

-- Companies table
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    name TEXT NOT NULL,
    address TEXT,
    industry TEXT,
    website TEXT,
    overview TEXT,
    background TEXT,
    products_services TEXT,
    account_email TEXT,
    account_password TEXT,
    account_type TEXT,
    cronofy_access_token TEXT,
    cronofy_refresh_token TEXT,
    cronofy_provider TEXT,
    cronofy_linked_email TEXT,
    cronofy_default_calendar_id TEXT,
    cronofy_default_calendar_name TEXT,
    last_processed_uid TEXT,
    voice_agent_settings JSONB,
    custom_calendar_link TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id),
    product_name TEXT NOT NULL,
    file_name TEXT,
    original_filename TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Leads table
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id),
    upload_task_id UUID REFERENCES upload_tasks(id),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT,
    phone_number TEXT,
    company_size TEXT,
    job_title TEXT,
    company_facebook TEXT,
    company_twitter TEXT,
    company_revenue TEXT,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add unique composite index on leads table for company_id and email
CREATE UNIQUE INDEX IF NOT EXISTS leads_company_id_email_unique_idx ON leads (company_id, email) WHERE deleted_at IS NULL;

-- Add unique composite index on leads table for company_id and phone_number (only for non-null phone numbers)
CREATE UNIQUE INDEX IF NOT EXISTS leads_company_id_phone_unique_idx ON leads (company_id, phone_number) WHERE deleted_at IS NULL AND phone_number IS NOT NULL;

-- Calls table
CREATE TABLE IF NOT EXISTS calls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID REFERENCES leads(id),
    product_id UUID REFERENCES products(id),
    campaign_id UUID REFERENCES campaigns(id),
    campaign_run_id UUID REFERENCES campaign_runs(id),
    duration INTEGER,
    sentiment TEXT,
    summary TEXT,
    bland_call_id TEXT,
    has_meeting_booked BOOLEAN DEFAULT FALSE,
    transcripts JSONB,
    script TEXT,
    recording_url TEXT,
    failure_reason TEXT,
    last_reminder_sent VARCHAR(2),
    last_reminder_sent_at TIMESTAMP WITH TIME ZONE,
    is_reminder_eligible BOOLEAN DEFAULT FALSE,
    last_called_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add comment to explain the script column
COMMENT ON COLUMN calls.script IS 'The generated call script used for this call';

-- Add comment to explain the recording_url column
COMMENT ON COLUMN calls.recording_url IS 'URL to the recorded call audio file';

-- Add comment to explain the failure_reason column
COMMENT ON COLUMN calls.failure_reason IS 'Reason for call failure if the call was unsuccessful';

-- Add comment to explain the last_reminder_sent column
COMMENT ON COLUMN calls.last_reminder_sent IS 'The type of the last reminder sent (e.g., r1, r2)';

-- Add comment to explain the last_reminder_sent_at column
COMMENT ON COLUMN calls.last_reminder_sent_at IS 'Timestamp of when the last reminder was sent';

-- Add comment to explain the is_reminder_eligible column
COMMENT ON COLUMN calls.is_reminder_eligible IS 'Indicates whether the call is eligible for reminders';

-- Add comment to explain the last_called_at column
COMMENT ON COLUMN calls.last_called_at IS 'Timestamp of when the call was last initiated';

-- Email Campaigns table
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    company_id UUID REFERENCES companies(id),
    product_id UUID REFERENCES products(id),
    type TEXT NOT NULL DEFAULT 'email',
    template TEXT,
    number_of_reminders INTEGER DEFAULT 0,
    days_between_reminders INTEGER DEFAULT 0,
    phone_number_of_reminders INTEGER DEFAULT 0,
    phone_days_between_reminders INTEGER DEFAULT 0,
    auto_reply_enabled BOOLEAN DEFAULT FALSE,
    trigger_call_on TEXT,
    scheduled_at TIMESTAMP WITH TIME ZONE,
    auto_run_triggered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add comment to explain the column usage
COMMENT ON COLUMN campaigns.type IS 'Type of campaign (e.g., email, call, etc.)';
COMMENT ON COLUMN campaigns.product_id IS 'Reference to the product associated with this campaign';
COMMENT ON COLUMN campaigns.template IS 'Template content for the campaign';
COMMENT ON COLUMN campaigns.auto_reply_enabled IS 'Flag to enable/disable automatic replies for the campaign';
COMMENT ON COLUMN campaigns.phone_number_of_reminders IS 'Number of phone call reminders to be made';
COMMENT ON COLUMN campaigns.phone_days_between_reminders IS 'Number of days to wait between phone call reminders';
COMMENT ON COLUMN campaigns.trigger_call_on IS 'Specifies the condition or event that triggers a call in the campaign';
COMMENT ON COLUMN campaigns.scheduled_at IS 'Timestamp when the campaign is scheduled to start';
COMMENT ON COLUMN campaigns.auto_run_triggered IS 'Flag indicating whether the campaign has been automatically triggered based on schedule';

-- Email Logs table
CREATE TABLE IF NOT EXISTS email_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID REFERENCES campaigns(id),
    campaign_run_id UUID REFERENCES campaign_runs(id),
    lead_id UUID REFERENCES leads(id),
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL,
    has_replied BOOLEAN DEFAULT FALSE,
    has_opened BOOLEAN DEFAULT FALSE,
    has_meeting_booked BOOLEAN DEFAULT FALSE,
    last_reminder_sent VARCHAR(2),
    last_reminder_sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Email log details table
CREATE TABLE IF NOT EXISTS email_log_details (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_logs_id UUID REFERENCES email_logs(id),
    message_id TEXT NOT NULL UNIQUE,
    email_subject TEXT,
    email_body TEXT,
    sender_type TEXT NOT NULL CHECK (sender_type IN ('user', 'assistant')),
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL,
    from_name TEXT,
    from_email TEXT,
    to_email TEXT,
    reminder_type VARCHAR(2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Booked Meetings table
CREATE TABLE IF NOT EXISTS booked_meetings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) NOT NULL,
    company_id UUID REFERENCES companies(id) NOT NULL,
    item_id UUID NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('email', 'call')),
    booked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reported_to_stripe BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS booked_meetings_user_id_idx ON booked_meetings(user_id);
CREATE INDEX IF NOT EXISTS booked_meetings_company_id_idx ON booked_meetings(company_id);
CREATE INDEX IF NOT EXISTS booked_meetings_item_id_idx ON booked_meetings(item_id);
CREATE INDEX IF NOT EXISTS booked_meetings_type_idx ON booked_meetings(type);
CREATE INDEX IF NOT EXISTS booked_meetings_reported_to_stripe_idx ON booked_meetings(reported_to_stripe);

-- Add comments to explain the columns
COMMENT ON TABLE booked_meetings IS 'Tracks all booked meetings from both email and call campaigns';
COMMENT ON COLUMN booked_meetings.item_id IS 'References either email_logs.id or calls.id depending on type';
COMMENT ON COLUMN booked_meetings.type IS 'Type of meeting booking (email or call)';
COMMENT ON COLUMN booked_meetings.reported_to_stripe IS 'Indicates whether the meeting has been reported to Stripe for billing';

-- Password Reset Tokens table
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) NOT NULL,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Email Verification Tokens table
CREATE TABLE IF NOT EXISTS verification_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) NOT NULL,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Invite Tokens table
CREATE TABLE IF NOT EXISTS invite_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) NOT NULL,
    token TEXT NOT NULL UNIQUE,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User Company Profiles table
CREATE TABLE IF NOT EXISTS user_company_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) NOT NULL,
    company_id UUID REFERENCES companies(id) NOT NULL,
    role VARCHAR(5) NOT NULL CHECK (role IN ('admin', 'sdr')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add unique composite index on user_id, company_id, and role
CREATE UNIQUE INDEX IF NOT EXISTS user_company_profiles_unique_idx ON user_company_profiles (user_id, company_id, role);

-- Campaign Runs table
CREATE TABLE IF NOT EXISTS campaign_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID REFERENCES campaigns(id) NOT NULL,
    run_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    leads_total INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'idle' CHECK (status IN ('idle', 'failed', 'running', 'completed')),
    failure_reason TEXT,
    celery_task_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add comments to explain the columns
COMMENT ON COLUMN campaign_runs.leads_total IS 'Number of call/email leads that were available when this run was executed';
COMMENT ON COLUMN campaign_runs.status IS 'Status of the campaign run: idle (default), running, completed, or failed';
COMMENT ON COLUMN campaign_runs.failure_reason IS 'Reason for failure if the campaign run status is failed';
COMMENT ON COLUMN campaign_runs.celery_task_id IS 'ID of the Celery task that is processing this campaign run';

-- Email Queue table
CREATE TABLE IF NOT EXISTS email_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    campaign_id UUID REFERENCES campaigns(id) NOT NULL,
    campaign_run_id UUID REFERENCES campaign_runs(id) NOT NULL,
    lead_id UUID REFERENCES leads(id) NOT NULL,
    email_log_id UUID REFERENCES email_logs(id),
    subject TEXT NOT NULL,
    email_body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'sent', 'failed')),
    priority INTEGER NOT NULL DEFAULT 0,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    error_message TEXT,
    message_id TEXT,
    reference_ids TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    scheduled_for TIMESTAMP WITH TIME ZONE,
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Add comments to explain the columns
COMMENT ON COLUMN email_queue.subject IS 'Subject line of the email to be sent';
COMMENT ON COLUMN email_queue.email_body IS 'Body content of the email to be sent';
COMMENT ON COLUMN email_queue.status IS 'Status of the queued email: pending (default), processing, sent, or failed';
COMMENT ON COLUMN email_queue.processed_at IS 'Timestamp when the email was processed (sent or failed)';
COMMENT ON COLUMN email_queue.message_id IS 'Message ID of the email';
COMMENT ON COLUMN email_queue.reference_ids IS 'References header value for email threading';

-- Create index for faster querying of pending emails
CREATE INDEX IF NOT EXISTS email_queue_status_idx ON email_queue(status);
CREATE INDEX IF NOT EXISTS email_queue_campaign_run_id_idx ON email_queue(campaign_run_id);

-- Campaign Message Schedule table
CREATE TABLE IF NOT EXISTS campaign_message_schedule (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_run_id UUID REFERENCES campaign_runs(id) NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent')),
    data_fetch_date TIMESTAMP WITH TIME ZONE NOT NULL,
    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add index for faster lookups by status and campaign_run_id
CREATE INDEX IF NOT EXISTS campaign_message_schedule_status_idx ON campaign_message_schedule(status);
CREATE INDEX IF NOT EXISTS campaign_message_schedule_campaign_run_id_idx ON campaign_message_schedule(campaign_run_id);

-- Add compound unique index to ensure no duplicate schedules for the same campaign run
CREATE UNIQUE INDEX IF NOT EXISTS campaign_message_schedule_run_schedule_unique_idx 
    ON campaign_message_schedule(campaign_run_id, scheduled_for);

-- Partner Applications table
CREATE TABLE IF NOT EXISTS partner_applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    contact_phone TEXT,
    website TEXT,
    partnership_type TEXT NOT NULL CHECK (partnership_type IN ('RESELLER', 'REFERRAL', 'TECHNOLOGY')),
    company_size TEXT NOT NULL CHECK (company_size IN ('1-10', '11-50', '51-200', '201-500', '501+')),
    industry TEXT NOT NULL,
    current_solutions TEXT,
    target_market TEXT,
    motivation TEXT NOT NULL,
    additional_information TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'REVIEWING', 'APPROVED', 'REJECTED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Partner Application Notes table
CREATE TABLE IF NOT EXISTS partner_application_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id UUID REFERENCES partner_applications(id) ON DELETE CASCADE,
    author_name TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for faster querying
CREATE INDEX IF NOT EXISTS partner_applications_status_idx ON partner_applications(status);
CREATE INDEX IF NOT EXISTS partner_applications_partnership_type_idx ON partner_applications(partnership_type);
CREATE INDEX IF NOT EXISTS partner_applications_created_at_idx ON partner_applications(created_at);
CREATE INDEX IF NOT EXISTS partner_application_notes_application_id_idx ON partner_application_notes(application_id);

COMMENT ON TABLE partner_applications IS 'Stores partner program applications from potential partners';
COMMENT ON TABLE partner_application_notes IS 'Stores internal notes related to partner applications';

CREATE TABLE IF NOT EXISTS call_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    campaign_id UUID REFERENCES campaigns(id) NOT NULL,
    campaign_run_id UUID REFERENCES campaign_runs(id) NOT NULL,
    lead_id UUID REFERENCES leads(id) NOT NULL,
    call_log_id UUID REFERENCES calls(id),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'sent', 'failed')),
    priority INTEGER NOT NULL DEFAULT 0,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    error_message TEXT,
    call_script TEXT,
    work_time_start TIME,
    work_time_end TIME,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Upload Tasks table
CREATE TABLE IF NOT EXISTS upload_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    user_id UUID REFERENCES users(id) NOT NULL,
    file_url TEXT NOT NULL,
    file_name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'leads' CHECK (type IN ('leads', 'do_not_email')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    result TEXT,
    celery_task_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Add indexes for faster querying
CREATE INDEX IF NOT EXISTS upload_tasks_company_id_idx ON upload_tasks(company_id);
CREATE INDEX IF NOT EXISTS upload_tasks_user_id_idx ON upload_tasks(user_id);
CREATE INDEX IF NOT EXISTS upload_tasks_status_idx ON upload_tasks(status);
CREATE INDEX IF NOT EXISTS upload_tasks_type_idx ON upload_tasks(type);

-- Add comments to explain the columns
COMMENT ON TABLE upload_tasks IS 'Tracks lead upload tasks and their progress';
COMMENT ON COLUMN upload_tasks.file_url IS 'Storage URL where the uploaded file is stored';
COMMENT ON COLUMN upload_tasks.file_name IS 'Original name of the uploaded file';
COMMENT ON COLUMN upload_tasks.type IS 'Type of upload task: leads (for lead CSV uploads) or do_not_email (for do not contact list uploads)';
COMMENT ON COLUMN upload_tasks.celery_task_id IS 'ID of the Celery task that is processing this upload task';

-- Skipped Rows table
CREATE TABLE IF NOT EXISTS skipped_rows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    upload_task_id UUID REFERENCES upload_tasks(id) NOT NULL,
    category TEXT NOT NULL,
    row_data TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for faster querying
CREATE INDEX IF NOT EXISTS skipped_rows_upload_task_id_idx ON skipped_rows(upload_task_id);
CREATE INDEX IF NOT EXISTS skipped_rows_category_idx ON skipped_rows(category);

-- Add comments to explain the columns
COMMENT ON TABLE skipped_rows IS 'Stores information about rows that were skipped during the upload process';
COMMENT ON COLUMN skipped_rows.category IS 'Reason category for why the row was skipped (e.g., invalid_email, missing_name)';
COMMENT ON COLUMN skipped_rows.row_data IS 'Original row data that was skipped';