-- Add deleted field to the products table
ALTER TABLE products 
ADD COLUMN IF NOT EXISTS deleted BOOLEAN DEFAULT FALSE;

-- Create index for faster queries on deleted products
CREATE INDEX IF NOT EXISTS idx_products_deleted ON products(deleted);

-- Add comment to explain the column
COMMENT ON COLUMN products.deleted IS 'Flag indicating if the product has been soft deleted'; 