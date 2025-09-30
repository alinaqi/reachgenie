-- Migration to add bounce tracking fields to companies table

-- Add last_processed_bounce_uid to track the last processed bounce email
ALTER TABLE companies 
ADD COLUMN IF NOT EXISTS last_processed_bounce_uid TEXT DEFAULT NULL;

-- Add comment to explain the purpose of the column
COMMENT ON COLUMN companies.last_processed_bounce_uid IS 'Last processed UID for bounce notification emails'; 