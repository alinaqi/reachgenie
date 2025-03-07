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
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT,
    phone_number TEXT NOT NULL,
    company_size TEXT,
    job_title TEXT,
    company_facebook TEXT,
    company_twitter TEXT,
    company_revenue TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add comment to explain the script column
COMMENT ON COLUMN calls.script IS 'The generated call script used for this call';

-- Add comment to explain the recording_url column
COMMENT ON COLUMN calls.recording_url IS 'URL to the recorded call audio file';

-- Email Campaigns table
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    company_id UUID REFERENCES companies(id),
    product_id UUID REFERENCES products(id),
    type TEXT NOT NULL DEFAULT 'email',
    template TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add comment to explain the column usage
COMMENT ON COLUMN campaigns.type IS 'Type of campaign (e.g., email, call, etc.)';
COMMENT ON COLUMN campaigns.product_id IS 'Reference to the product associated with this campaign';
COMMENT ON COLUMN campaigns.template IS 'Template content for the campaign';

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
    leads_processed INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'idle' CHECK (status IN ('idle', 'running', 'completed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add comments to explain the columns
COMMENT ON COLUMN campaign_runs.leads_total IS 'Number of call/email leads that were available when this run was executed';
COMMENT ON COLUMN campaign_runs.leads_processed IS 'Number of leads processed so far in this run';
COMMENT ON COLUMN campaign_runs.status IS 'Status of the campaign run: idle (default), running, or completed';