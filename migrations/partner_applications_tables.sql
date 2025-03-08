-- Partner Applications table
CREATE TABLE IF NOT EXISTS partner_applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    contact_phone TEXT,
    website TEXT,
    partnership_type TEXT NOT NULL CHECK (partnership_type IN ('RESELLER', 'REFERRAL', 'TECHNOLOGY')),
    company_size TEXT NOT NULL CHECK (company_size IN ('1-10', '11-50', '51-200', '201-500', '501+')),
    industry TEXT NOT NULL,
    current_solutions TEXT,
    target_market TEXT,
    motivation TEXT NOT NULL,
    additional_information TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'REVIEWING', 'APPROVED', 'REJECTED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Partner Application Notes table
CREATE TABLE IF NOT EXISTS partner_application_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id UUID REFERENCES partner_applications(id) ON DELETE CASCADE,
    author_name TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for faster querying
CREATE INDEX IF NOT EXISTS partner_applications_status_idx ON partner_applications(status);
CREATE INDEX IF NOT EXISTS partner_applications_partnership_type_idx ON partner_applications(partnership_type);
CREATE INDEX IF NOT EXISTS partner_applications_created_at_idx ON partner_applications(created_at);
CREATE INDEX IF NOT EXISTS partner_application_notes_application_id_idx ON partner_application_notes(application_id);

COMMENT ON TABLE partner_applications IS 'Stores partner program applications from potential partners';
COMMENT ON TABLE partner_application_notes IS 'Stores internal notes related to partner applications'; 