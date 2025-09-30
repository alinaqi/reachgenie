-- LinkedIn Account Connections Table
CREATE TABLE IF NOT EXISTS linkedin_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    unipile_account_id TEXT NOT NULL UNIQUE,
    account_type TEXT NOT NULL DEFAULT 'LINKEDIN',
    account_status TEXT NOT NULL DEFAULT 'CONNECTING',
    account_feature TEXT, -- classic, recruiter, sales_navigator
    account_user_id TEXT, -- LinkedIn provider ID
    display_name TEXT,
    profile_url TEXT,
    connection_email TEXT,
    last_status_update TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- LinkedIn Chats Table
CREATE TABLE IF NOT EXISTS linkedin_chats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    unipile_chat_id TEXT NOT NULL UNIQUE,
    linkedin_connection_id UUID REFERENCES linkedin_connections(id) NOT NULL,
    chat_provider_id TEXT,
    title TEXT,
    is_group BOOLEAN DEFAULT FALSE,
    last_message_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- LinkedIn Messages Table
CREATE TABLE IF NOT EXISTS linkedin_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    unipile_message_id TEXT NOT NULL UNIQUE,
    chat_id UUID REFERENCES linkedin_chats(id) NOT NULL,
    campaign_id UUID REFERENCES campaigns(id),
    campaign_run_id UUID REFERENCES campaign_runs(id),
    lead_id UUID REFERENCES leads(id),
    provider_message_id TEXT,
    sender_id TEXT,
    sender_name TEXT,
    message_text TEXT,
    is_sender BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered BOOLEAN DEFAULT FALSE,
    seen BOOLEAN DEFAULT FALSE,
    reminder_type VARCHAR(2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- LinkedIn Attendees Table (for storing contacts)
CREATE TABLE IF NOT EXISTS linkedin_attendees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    unipile_attendee_id TEXT UNIQUE,
    provider_id TEXT NOT NULL,
    name TEXT,
    headline TEXT,
    profile_url TEXT,
    is_premium BOOLEAN DEFAULT FALSE,
    is_influencer BOOLEAN DEFAULT FALSE,
    network_distance TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- LinkedIn Campaign Logs Table
CREATE TABLE IF NOT EXISTS linkedin_campaign_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID REFERENCES campaigns(id) NOT NULL,
    campaign_run_id UUID REFERENCES campaign_runs(id) NOT NULL,
    lead_id UUID REFERENCES leads(id) NOT NULL,
    linkedin_connection_id UUID REFERENCES linkedin_connections(id) NOT NULL,
    chat_id UUID REFERENCES linkedin_chats(id),
    sent_at TIMESTAMP WITH TIME ZONE,
    has_replied BOOLEAN DEFAULT FALSE,
    has_accepted_invitation BOOLEAN DEFAULT FALSE,
    has_meeting_booked BOOLEAN DEFAULT FALSE,
    last_reminder_sent VARCHAR(2),
    last_reminder_sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add LinkedIn-specific fields to leads table
ALTER TABLE leads
ADD COLUMN IF NOT EXISTS personal_linkedin_id TEXT,
ADD COLUMN IF NOT EXISTS linkedin_profile_synced BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS linkedin_headline TEXT,
ADD COLUMN IF NOT EXISTS linkedin_network_distance TEXT,
ADD COLUMN IF NOT EXISTS linkedin_last_synced_at TIMESTAMP WITH TIME ZONE;

-- Add LinkedIn support to campaigns table
ALTER TABLE campaigns
ADD COLUMN IF NOT EXISTS linkedin_message_template TEXT,
ADD COLUMN IF NOT EXISTS linkedin_invitation_template TEXT,
ADD COLUMN IF NOT EXISTS linkedin_inmail_enabled BOOLEAN DEFAULT FALSE;

-- Add LinkedIn connection ID to companies table
ALTER TABLE companies
ADD COLUMN IF NOT EXISTS primary_linkedin_connection_id UUID REFERENCES linkedin_connections(id);

-- Create indexes for performance
CREATE INDEX idx_linkedin_connections_company_id ON linkedin_connections(company_id);
CREATE INDEX idx_linkedin_connections_status ON linkedin_connections(account_status);
CREATE INDEX idx_linkedin_chats_connection_id ON linkedin_chats(linkedin_connection_id);
CREATE INDEX idx_linkedin_messages_chat_id ON linkedin_messages(chat_id);
CREATE INDEX idx_linkedin_messages_lead_id ON linkedin_messages(lead_id);
CREATE INDEX idx_linkedin_campaign_logs_campaign_run ON linkedin_campaign_logs(campaign_run_id);

-- Add comments
COMMENT ON TABLE linkedin_connections IS 'Stores LinkedIn account connections via Unipile API';
COMMENT ON TABLE linkedin_chats IS 'Stores LinkedIn chat/conversation data';
COMMENT ON TABLE linkedin_messages IS 'Stores individual LinkedIn messages';
COMMENT ON TABLE linkedin_attendees IS 'Stores LinkedIn contact/attendee information';
COMMENT ON TABLE linkedin_campaign_logs IS 'Tracks LinkedIn campaign execution and results';
