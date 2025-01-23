-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Companies table
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    name TEXT NOT NULL,
    address TEXT,
    industry TEXT,
    account_email TEXT,
    account_password TEXT,
    account_type TEXT,
    cronofy_access_token TEXT,
    cronofy_refresh_token TEXT,
    cronofy_provider TEXT,
    cronofy_linked_email TEXT,
    cronofy_default_calendar_id TEXT,
    cronofy_default_calendar_name TEXT,
    last_email_processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id),
    product_name TEXT NOT NULL,
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
    company_id UUID REFERENCES companies(id),
    lead_id UUID REFERENCES leads(id),
    product_id UUID REFERENCES products(id),
    duration INTEGER,
    sentiment TEXT,
    summary TEXT,
    bland_call_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Email Campaigns table
CREATE TABLE IF NOT EXISTS email_campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    company_id UUID REFERENCES companies(id),
    email_subject TEXT NOT NULL,
    email_body TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Email Logs table
CREATE TABLE IF NOT EXISTS email_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID REFERENCES email_campaigns(id),
    lead_id UUID REFERENCES leads(id),
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL,
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
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);