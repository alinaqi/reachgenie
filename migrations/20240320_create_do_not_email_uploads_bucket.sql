-- Create storage bucket for do-not-email uploads
INSERT INTO storage.buckets (id, name) 
VALUES ('do-not-email-uploads', 'do-not-email-uploads')
ON CONFLICT (id) DO NOTHING;

-- Set up storage policies
CREATE POLICY "Allow authenticated users to upload files"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (bucket_id = 'do-not-email-uploads');

CREATE POLICY "Allow authenticated users to read their files"
ON storage.objects FOR SELECT TO authenticated
USING (bucket_id = 'do-not-email-uploads'); 