-- Add ideal_icps field to the products table as a JSONB array
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS ideal_icps JSONB DEFAULT '[]';

-- Create index for better query performance on JSONB data
CREATE INDEX IF NOT EXISTS idx_products_ideal_icps ON products USING GIN (ideal_icps);

-- Add comment to explain the column
COMMENT ON COLUMN products.ideal_icps IS 'Array of ideal customer profiles in JSON format'; 