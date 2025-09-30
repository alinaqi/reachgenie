-- Migration to add LinkedIn campaign support to campaign_leads table
-- Add this migration to your database

-- Add LinkedIn-specific columns to campaign_leads if they don't exist
ALTER TABLE campaign_leads
ADD COLUMN IF NOT EXISTS linkedin_profile_url TEXT,
ADD COLUMN IF NOT EXISTS linkedin_profile_id TEXT,
ADD COLUMN IF NOT EXISTS message_sent BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS message_sent_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS connection_request_sent BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS connection_request_sent_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS connection_accepted BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS connection_accepted_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS last_message_id TEXT,
ADD COLUMN IF NOT EXISTS chat_id TEXT;

-- Create an index for faster LinkedIn campaign queries
CREATE INDEX IF NOT EXISTS idx_campaign_leads_linkedin ON campaign_leads(campaign_id) WHERE linkedin_profile_url IS NOT NULL;

-- Update the status column to support LinkedIn-specific statuses
-- This is safe as it doesn't change existing values
COMMENT ON COLUMN campaign_leads.status IS 'Status: pending, sent, replied, connected, failed';
