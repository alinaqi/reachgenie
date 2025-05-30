-- Migration to make phone_number optional in leads table
-- Date: 2024-12-30

-- Make phone_number nullable
ALTER TABLE leads ALTER COLUMN phone_number DROP NOT NULL;

-- Update the unique index to handle NULL phone numbers properly
DROP INDEX IF EXISTS leads_company_id_phone_unique_idx;
CREATE UNIQUE INDEX leads_company_id_phone_unique_idx 
ON leads (company_id, phone_number) 
WHERE deleted_at IS NULL AND phone_number IS NOT NULL;

-- Add comment to explain the change
COMMENT ON COLUMN leads.phone_number IS 'Lead phone number (optional). Can be mobile, direct, or office phone.';
