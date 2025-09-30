-- Migration: Create do_not_email table
-- This table tracks email addresses that should not be contacted, either due to bounces,
-- unsubscribe requests, or other reasons

CREATE TABLE IF NOT EXISTS do_not_email (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT NOT NULL,
    reason TEXT NOT NULL, -- bounce, unsubscribe, complaint, manual, etc.
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE, -- NULL means global (applies to all companies)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create a unique index on email (global) or email+company_id (company-specific)
CREATE UNIQUE INDEX IF NOT EXISTS do_not_email_email_company_id_idx ON do_not_email (email, COALESCE(company_id, '00000000-0000-0000-0000-000000000000'::UUID));

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS do_not_email_email_idx ON do_not_email (email);
CREATE INDEX IF NOT EXISTS do_not_email_company_id_idx ON do_not_email (company_id);

-- Add comment
COMMENT ON TABLE do_not_email IS 'Stores email addresses that should not be contacted, with optional company-specific exclusions'; 