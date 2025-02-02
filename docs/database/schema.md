# Database Schema Documentation

## Overview
The system uses PostgreSQL as its primary database. The schema is designed to support multi-tenant architecture with companies, users, and their associated data.

## Tables

### Users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Email Verification Tokens
```sql
CREATE TABLE verification_tokens (
    token TEXT PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Companies
```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    name TEXT NOT NULL,
    address TEXT,
    industry TEXT,
    website TEXT,
    overview TEXT,
    background TEXT,
    products_services TEXT,
    account_email TEXT,
    account_password TEXT,
    account_type TEXT,
    cronofy_access_token TEXT,
    cronofy_refresh_token TEXT,
    cronofy_provider TEXT,
    cronofy_profile_name TEXT,
    cronofy_profile_connected BOOLEAN DEFAULT FALSE,
    cronofy_default_calendar_id TEXT,
    cronofy_default_calendar_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Products
```sql
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id),
    product_name TEXT NOT NULL,
    description TEXT,
    file_name TEXT,
    original_filename TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Leads
```sql
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id),
    name TEXT NOT NULL,
    email TEXT,
    company TEXT,
    phone_number TEXT,
    company_size TEXT,
    job_title TEXT,
    lead_source TEXT,
    education TEXT,
    personal_linkedin_url TEXT,
    country TEXT,
    city TEXT,
    state TEXT,
    mobile TEXT,
    direct_phone TEXT,
    office_phone TEXT,
    hq_location TEXT,
    website TEXT,
    headcount INTEGER,
    industries TEXT[],
    department TEXT,
    sic_code TEXT,
    isic_code TEXT,
    naics_code TEXT,
    company_address TEXT,
    company_city TEXT,
    company_zip TEXT,
    company_state TEXT,
    company_country TEXT,
    company_hq_address TEXT,
    company_hq_city TEXT,
    company_hq_zip TEXT,
    company_hq_state TEXT,
    company_hq_country TEXT,
    company_linkedin_url TEXT,
    company_type TEXT,
    company_description TEXT,
    technologies TEXT[],
    financials JSONB,
    company_founded_year INTEGER,
    seniority TEXT,
    hiring_positions JSONB,
    location_move JSONB,
    job_change JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Campaigns
```sql
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id),
    product_id UUID REFERENCES products(id),
    name TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Calls
```sql
CREATE TABLE calls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID REFERENCES leads(id),
    campaign_id UUID REFERENCES campaigns(id),
    company_id UUID REFERENCES companies(id),
    bland_call_id TEXT,
    duration INTEGER,
    sentiment TEXT,
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Email Logs
```sql
CREATE TABLE email_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID REFERENCES campaigns(id),
    lead_id UUID REFERENCES leads(id),
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Email Log Details
```sql
CREATE TABLE email_log_details (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_logs_id UUID REFERENCES email_logs(id),
    message_id TEXT,
    email_subject TEXT,
    email_body TEXT,
    sender_type TEXT,
    sent_at TIMESTAMP WITH TIME ZONE,
    from_name TEXT,
    from_email TEXT,
    to_email TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Upload Tasks
```sql
CREATE TABLE upload_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID REFERENCES companies(id),
    user_id UUID REFERENCES users(id),
    file_name TEXT NOT NULL,
    status TEXT NOT NULL,
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## Relationships

### One-to-Many
- User → Companies
- Company → Products
- Company → Leads
- Company → Campaigns
- Campaign → Calls
- Campaign → Email Logs
- Email Log → Email Log Details

### Many-to-One
- Companies → User
- Products → Company
- Leads → Company
- Campaigns → Company
- Calls → Lead
- Calls → Campaign
- Email Logs → Campaign
- Email Logs → Lead
- Email Log Details → Email Log

## Indexes
- Users: email (unique)
- Companies: user_id
- Products: company_id
- Leads: company_id
- Campaigns: company_id
- Calls: lead_id, campaign_id
- Email Logs: campaign_id, lead_id
- Email Log Details: email_logs_id
- Upload Tasks: company_id, user_id 