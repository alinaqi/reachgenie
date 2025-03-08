-- Migration: Add do_not_contact field to leads table
-- This field indicates if a lead should not be contacted via any channel (email or phone)

-- Add do_not_contact column to leads table
ALTER TABLE leads ADD COLUMN IF NOT EXISTS do_not_contact BOOLEAN DEFAULT FALSE;

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS leads_do_not_contact_idx ON leads (do_not_contact);

-- Add comment
COMMENT ON COLUMN leads.do_not_contact IS 'Indicates whether this lead should not be contacted via any channel (email, phone, etc.)'; 