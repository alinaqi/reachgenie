-- Create upload_tasks table
CREATE TABLE upload_tasks (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    user_id UUID NOT NULL REFERENCES users(id),
    file_url TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes
CREATE INDEX idx_upload_tasks_company_id ON upload_tasks(company_id);
CREATE INDEX idx_upload_tasks_user_id ON upload_tasks(user_id);
CREATE INDEX idx_upload_tasks_status ON upload_tasks(status);

-- Create storage bucket for lead uploads
INSERT INTO storage.buckets (id, name) 
VALUES ('leads-uploads', 'leads-uploads')
ON CONFLICT (id) DO NOTHING;

-- Set up storage policies
CREATE POLICY "Allow authenticated users to upload files"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'leads-uploads');

CREATE POLICY "Allow authenticated users to read their files"
ON storage.objects FOR SELECT TO authenticated
USING (bucket_id = 'leads-uploads'); 