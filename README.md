# ReachGenie - AI-Powered Sales Automation Platform

ReachGenie is a comprehensive AI-powered sales automation platform that enables businesses to run multi-channel outbound campaigns through email, phone calls, and LinkedIn. The platform leverages AI for personalized content generation, lead enrichment, and intelligent follow-ups to maximize sales efficiency and meeting bookings.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Installation & Setup](#installation--setup)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [Background Jobs & Cron Tasks](#background-jobs--cron-tasks)
- [Integrations](#integrations)
- [Development Guide](#development-guide)
- [Project Structure](#project-structure)

## Overview

ReachGenie is an AI SDR (Sales Development Representative) platform that automates the entire outbound sales process. It helps companies:

- Manage products and value propositions
- Upload and enrich leads with company intelligence
- Create and execute multi-channel campaigns (Email, Phone, LinkedIn)
- Generate personalized AI-driven content for each prospect
- Track engagement and automatically follow up
- Book meetings directly into calendars
- Monitor campaign performance with detailed analytics

## Key Features

### Multi-Channel Campaign Execution

ReachGenie supports **3 primary communication channels** for outbound sales automation:

#### 1. Email Channel
- **AI-Generated Content**: Personalized emails using GPT-4/Claude based on lead data
- **SMTP Integration**: Support for Gmail, Outlook, Yahoo, and custom SMTP servers
- **Reply Detection**: Automatic IMAP monitoring for prospect replies
- **Smart Follow-ups**: Context-aware reminder emails with engagement tracking
- **Email Threading**: Proper Message-ID and References headers for conversation threads
- **Open Tracking**: Pixel-based open detection
- **Bounce Handling**: Automatic bounce processing and suppression list management
- **Throttling**: Configurable hourly/daily sending limits to protect sender reputation
- **Queue System**: Redis-based email queue with retry logic and priority handling
- **Auto-Reply AI**: Intelligent AI responses to prospect replies when enabled

#### 2. Phone/Voice Channel
- **AI Voice Agent**: Natural conversations powered by Bland AI
- **Dynamic Scripts**: AI-generated call scripts personalized per prospect
- **Real-time Conversations**: Natural language understanding and response
- **Meeting Booking**: Direct calendar integration during calls via tools
- **Call Recording**: Automatic recording and transcription
- **Sentiment Analysis**: AI-powered call sentiment detection
- **Call Queue**: Redis-based queue with business hours respect
- **Call Reminders**: Automatic follow-up calls based on previous outcomes
- **Voicemail Detection**: Smart handling of voicemail scenarios
- **Multi-timezone Support**: Respects prospect local business hours

#### 3. LinkedIn Channel
- **Automated Connection Requests**: Personalized invitation messages
- **Direct Messaging**: AI-generated messages to 1st-degree connections
- **Profile Views**: Automated profile viewing to increase visibility
- **Message Threading**: Maintains conversation context
- **Rate Limiting**: Built-in safety limits (80 invites/day, 100 views/day)
- **Human-like Delays**: Randomized delays between actions
- **Account Management**: Multi-account support via Unipile
- **Webhook Integration**: Real-time message and connection status updates
- **Campaign Tracking**: Full analytics on connection acceptance and reply rates

### Campaign Types
- **Email Only**: Pure email outreach campaigns
- **Call Only**: Voice-only campaigns
- **Email + Call**: Hybrid campaigns with email first, call as follow-up
- **LinkedIn Only**: LinkedIn-exclusive campaigns
- **Multi-Channel**: Combined email, call, and LinkedIn sequences

### AI-Powered Intelligence
- **Lead Enrichment**: Automatic company and prospect research using Perplexity AI
- **Content Generation**: Personalized email and call scripts using OpenAI GPT-4 and Anthropic Claude
- **Smart Follow-ups**: Context-aware reminder emails based on engagement patterns
- **Sentiment Analysis**: AI-powered call analysis and lead scoring

### Advanced Campaign Management
- **Queue System**: Redis-based email and call queues with retry logic
- **Throttling**: Configurable email sending limits to protect sender reputation
- **Schedule Management**: Campaign scheduling and automated execution
- **A/B Testing**: Test campaigns before full deployment

### Calendar Integration
- **Cronofy Integration**: Seamless calendar booking with availability checking
- **Custom Calendar Links**: Support for Calendly and other scheduling tools
- **Meeting Tracking**: Automatic meeting confirmation and follow-up

### Subscription & Billing
- **Stripe Integration**: Multi-tier subscription plans (Trial, Fixed, Performance)
- **Usage-based Billing**: Metered billing for performance plans
- **Channel Management**: Per-channel subscription add-ons

### Team Collaboration
- **Multi-user Support**: Company-level user management with role-based access (Admin, SDR)
- **Team Invitations**: Invite team members with automatic onboarding

### Analytics & Reporting
- **Email Tracking**: Open rates, reply rates, and engagement metrics
- **Call Analytics**: Duration, sentiment, and conversion tracking
- **Campaign Reports**: Automated summary emails with performance benchmarks
- **Lead History**: Complete communication timeline for each prospect

## Tech Stack

### Core Framework
- **FastAPI 0.104.1**: Modern Python web framework for building APIs
- **Uvicorn 0.24.0**: ASGI server for FastAPI
- **Pydantic 2.4.2**: Data validation using Python type annotations
- **Pydantic Settings 2.0.3**: Configuration management
- **Python 3.12+**: Latest Python features and performance improvements

### Database & Storage
- **PostgreSQL**: Primary database (via Supabase)
- **Supabase 2.6.0**: Backend-as-a-Service platform
- **Asyncpg 0.30.0**: High-performance asynchronous PostgreSQL driver
- **Redis 6.1.0**: Queue management and caching

### Background Processing
- **Celery 5.5.2**: Distributed task queue for campaign execution
- **Flower**: Real-time Celery monitoring
- **Watchdog 6.0.0**: File system monitoring for auto-reload

### AI & ML Services
- **OpenAI 1.59.4**: GPT-4 for email and script generation
- **Anthropic (latest)**: Claude for advanced content generation
- **Perplexity API**: Company research and lead enrichment

### Communication Services
- **Bland AI**: AI-powered voice calling platform
- **Mailjet Rest 1.3.4**: Email delivery and tracking
- **aiosmtplib 3.0.1**: Asynchronous SMTP client
- **IMAP**: Direct email integration for reply processing
- **Unipile**: LinkedIn automation and messaging

### Third-Party Integrations
- **Stripe 12.0.1**: Payment processing and subscription management
- **Cronofy 2.0.7**: Calendar integration and meeting scheduling
- **Bugsnag 4.6.1**: Error tracking and monitoring

### Security & Authentication
- **python-jose 3.3.0**: JWT token handling
- **passlib 1.7.4**: Password hashing
- **bcrypt 4.2.1**: Secure password hashing
- **cryptography 42.0.2**: Email credential encryption
- **email-validator 2.2.0**: Email format validation

### HTTP & Networking
- **httpx 0.27.2**: Async HTTP client with HTTP/2 support
- **requests 2.31.0**: Synchronous HTTP library
- **urllib3 2.0.7**: HTTP client library
- **python-multipart 0.0.6**: Form data parsing

### Document Processing
- **python-docx 0.8.11**: Word document processing
- **PyPDF2 3.0.1**: PDF document parsing

### Utilities
- **pytz 2025.2**: Timezone handling
- **chardet 5.2.0**: Character encoding detection
- **charset-normalizer 3.3.2**: Unicode string normalization
- **python-dotenv 1.0.0**: Environment variable management

## Architecture

### System Architecture

```
┌─────────────────┐
│   Frontend UI   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │   Auth   │  │  Routes  │  │ Services │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────┬───────────────────────────────────────────────┘
          │
          ├─────────────┬──────────────┬──────────────┬────────────┐
          ▼             ▼              ▼              ▼            ▼
    ┌──────────┐  ┌─────────┐   ┌─────────┐   ┌──────────┐  ┌──────────┐
    │PostgreSQL│  │  Redis  │   │ Celery  │   │   AI     │  │External  │
    │   DB     │  │  Queue  │   │ Workers │   │Services  │  │  APIs    │
    └──────────┘  └─────────┘   └─────────┘   └──────────┘  └──────────┘
```

### Campaign Execution Flow

```
User Creates Campaign
        │
        ▼
Campaign Queued (Redis)
        │
        ▼
Celery Worker Picks Up Task
        │
        ├─── Email Campaign ──────┐
        │    1. Fetch Leads        │
        │    2. AI Enrichment      │
        │    3. Generate Email     │
        │    4. Queue in Redis     │
        │    5. SMTP Send          │
        │    6. Track Opens/Replies│
        │                          │
        ├─── Call Campaign ────────┤
        │    1. Fetch Leads        │
        │    2. Generate Script    │
        │    3. Queue Calls        │
        │    4. Bland AI Execute   │
        │    5. Process Results    │
        │    6. Book Meetings      │
        │                          │
        └─── LinkedIn Campaign ────┘
             1. Fetch Leads
             2. Generate Messages
             3. Queue Actions
             4. Unipile Execute
             5. Track Engagement
```

### Data Flow

1. **User Registration** → Email verification → Trial plan activation
2. **Company Setup** → Add products → Enrich with Perplexity
3. **Lead Upload** → CSV processing → Data validation → Enrichment
4. **Campaign Creation** → Template selection → Target audience
5. **Campaign Execution** → Queue processing → AI generation → Delivery
6. **Engagement Tracking** → Opens/Replies → Sentiment analysis → Follow-ups
7. **Meeting Booking** → Calendar check → Slot booking → Confirmation
8. **Reporting** → Analytics aggregation → Email summaries

## Database Schema

### Core Tables

#### users
Stores user authentication and subscription information.
```sql
- id: UUID (Primary Key)
- email: TEXT (Unique)
- name: TEXT
- password_hash: TEXT
- verified: BOOLEAN
- stripe_customer_id: TEXT
- plan_type: TEXT (trial, fixed, performance)
- lead_tier: INTEGER (2500, 5000, 7500, 10000)
- channels_active: JSONB
- subscription_id: TEXT
- subscription_status: TEXT
- billing_period_start: TIMESTAMP
- billing_period_end: TIMESTAMP
- created_at: TIMESTAMP
```

#### companies
Company profiles and configuration.
```sql
- id: UUID (Primary Key)
- user_id: UUID (Foreign Key)
- name: TEXT
- address: TEXT
- industry: TEXT
- website: TEXT
- overview: TEXT
- background: TEXT
- products_services: TEXT
- account_email: TEXT (for email campaigns)
- account_password: TEXT (encrypted)
- account_type: TEXT (gmail, outlook, etc.)
- cronofy_access_token: TEXT
- cronofy_refresh_token: TEXT
- cronofy_provider: TEXT
- voice_agent_settings: JSONB
- custom_calendar_link: TEXT
- last_processed_uid: TEXT (for bounce processing)
- created_at: TIMESTAMP
```

#### products
Product/service offerings for targeting.
```sql
- id: UUID (Primary Key)
- company_id: UUID (Foreign Key)
- product_name: TEXT
- file_name: TEXT (uploaded document)
- original_filename: TEXT
- description: TEXT
- enriched_information: JSONB
- ideal_icps: JSONB (Ideal Customer Profiles)
- created_at: TIMESTAMP
```

#### leads
Prospect database with enrichment.
```sql
- id: UUID (Primary Key)
- company_id: UUID (Foreign Key)
- upload_task_id: UUID (Foreign Key)
- name: TEXT
- first_name: TEXT
- last_name: TEXT
- email: TEXT
- company: TEXT
- phone_number: TEXT
- job_title: TEXT
- lead_source: TEXT
- education: TEXT
- personal_linkedin_url: TEXT
- country: TEXT
- website: TEXT
- company_linkedin_url: TEXT
- company_description: TEXT
- technologies: JSONB
- financials: JSONB
- enriched_data: JSONB (AI-generated insights)
- deleted_at: TIMESTAMP (soft delete)
- created_at: TIMESTAMP
```

#### campaigns
Multi-channel campaign definitions.
```sql
- id: UUID (Primary Key)
- company_id: UUID (Foreign Key)
- product_id: UUID (Foreign Key)
- name: TEXT
- description: TEXT
- type: TEXT (email, call, email_and_call, linkedin)
- template: TEXT
- number_of_reminders: INTEGER
- days_between_reminders: INTEGER
- phone_number_of_reminders: INTEGER
- phone_days_between_reminders: INTEGER
- auto_reply_enabled: BOOLEAN
- trigger_call_on: TEXT
- scheduled_at: TIMESTAMP
- auto_run_triggered: BOOLEAN
- created_at: TIMESTAMP
```

#### campaign_runs
Execution history and status.
```sql
- id: UUID (Primary Key)
- campaign_id: UUID (Foreign Key)
- run_at: TIMESTAMP
- leads_total: INTEGER
- status: TEXT (idle, running, completed, failed)
- failure_reason: TEXT
- celery_task_id: TEXT
- created_at: TIMESTAMP
```

### Communication Tables

#### email_logs
Email campaign tracking.
```sql
- id: UUID (Primary Key)
- campaign_id: UUID (Foreign Key)
- campaign_run_id: UUID (Foreign Key)
- lead_id: UUID (Foreign Key)
- sent_at: TIMESTAMP
- has_replied: BOOLEAN
- has_opened: BOOLEAN
- has_meeting_booked: BOOLEAN
- last_reminder_sent: VARCHAR(2)
- last_reminder_sent_at: TIMESTAMP
- created_at: TIMESTAMP
```

#### email_log_details
Individual email messages in threads.
```sql
- id: UUID (Primary Key)
- email_logs_id: UUID (Foreign Key)
- message_id: TEXT (Unique)
- email_subject: TEXT
- email_body: TEXT
- sender_type: TEXT (user, assistant)
- sent_at: TIMESTAMP
- from_name: TEXT
- from_email: TEXT
- to_email: TEXT
- reminder_type: VARCHAR(2)
- created_at: TIMESTAMP
```

#### calls
Voice call records.
```sql
- id: UUID (Primary Key)
- lead_id: UUID (Foreign Key)
- product_id: UUID (Foreign Key)
- campaign_id: UUID (Foreign Key)
- campaign_run_id: UUID (Foreign Key)
- duration: INTEGER
- sentiment: TEXT
- summary: TEXT
- bland_call_id: TEXT
- has_meeting_booked: BOOLEAN
- transcripts: JSONB
- script: TEXT
- recording_url: TEXT
- failure_reason: TEXT
- last_reminder_sent: VARCHAR(2)
- last_reminder_sent_at: TIMESTAMP
- is_reminder_eligible: BOOLEAN
- last_called_at: TIMESTAMP
- created_at: TIMESTAMP
```

### Queue Tables

#### email_queue
Email delivery queue with retry logic.
```sql
- id: UUID (Primary Key)
- company_id: UUID (Foreign Key)
- campaign_id: UUID (Foreign Key)
- campaign_run_id: UUID (Foreign Key)
- lead_id: UUID (Foreign Key)
- email_log_id: UUID (Foreign Key)
- subject: TEXT
- email_body: TEXT
- status: TEXT (pending, processing, sent, failed)
- priority: INTEGER
- retry_count: INTEGER
- max_retries: INTEGER
- error_message: TEXT
- message_id: TEXT
- reference_ids: TEXT (for threading)
- scheduled_for: TIMESTAMP
- processed_at: TIMESTAMP
- created_at: TIMESTAMP
```

#### call_queue
Call execution queue.
```sql
- id: UUID (Primary Key)
- company_id: UUID (Foreign Key)
- campaign_id: UUID (Foreign Key)
- campaign_run_id: UUID (Foreign Key)
- lead_id: UUID (Foreign Key)
- call_log_id: UUID (Foreign Key)
- status: TEXT (pending, processing, sent, failed)
- priority: INTEGER
- retry_count: INTEGER
- max_retries: INTEGER
- error_message: TEXT
- call_script: TEXT
- work_time_start: TIME
- work_time_end: TIME
- processed_at: TIMESTAMP
- created_at: TIMESTAMP
```

### Supporting Tables

#### user_company_profiles
Multi-user company access with roles.
```sql
- id: UUID (Primary Key)
- user_id: UUID (Foreign Key)
- company_id: UUID (Foreign Key)
- role: VARCHAR(5) (admin, sdr)
- created_at: TIMESTAMP
```

#### booked_meetings
Tracks successful meeting bookings for billing.
```sql
- id: UUID (Primary Key)
- user_id: UUID (Foreign Key)
- company_id: UUID (Foreign Key)
- item_id: UUID (email_logs or calls id)
- type: TEXT (email, call)
- booked_at: TIMESTAMP
- reported_to_stripe: BOOLEAN
- created_at: TIMESTAMP
```

#### upload_tasks
Async CSV upload processing.
```sql
- id: UUID (Primary Key)
- company_id: UUID (Foreign Key)
- user_id: UUID (Foreign Key)
- file_url: TEXT (storage location)
- file_name: TEXT
- type: TEXT (leads, do_not_email)
- status: TEXT (pending, processing, completed, failed)
- result: TEXT (JSON result)
- celery_task_id: TEXT
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

#### do_not_email_list
Global and company-specific suppression list.
```sql
- id: UUID (Primary Key)
- email: TEXT
- reason: TEXT
- company_id: UUID (NULL for global)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

## API Endpoints

### Authentication
- `POST /api/auth/signup` - User registration
- `POST /api/auth/login` - User login (returns JWT)
- `POST /api/auth/verify` - Email verification
- `POST /api/auth/resend-verification` - Resend verification email
- `POST /api/auth/forgot-password` - Request password reset
- `POST /api/auth/reset-password` - Reset password with token
- `GET /api/users/me` - Get current user details
- `PATCH /api/users/me` - Update user profile

### Company Management
- `POST /api/companies` - Create company
- `GET /api/companies` - List user's companies
- `GET /api/companies/{company_id}` - Get company details
- `PATCH /api/companies/{company_id}` - Update company
- `DELETE /api/companies/{company_id}` - Soft delete company
- `PATCH /api/companies/{company_id}/account-credentials` - Update email credentials
- `GET /api/companies/{company_id}/account-email/check` - Check if email exists in other companies
- `PATCH /api/companies/{company_id}/voice-agent-settings` - Update call settings
- `GET /api/companies/{company_id}/users` - List company team members
- `POST /api/companies/{company_id}/invite-users` - Invite team members
- `DELETE /api/companies/{company_id}/users/{user_company_profile_id}` - Remove team member

### Product Management
- `POST /api/companies/{company_id}/products` - Create product
- `GET /api/companies/{company_id}/products` - List products
- `GET /api/products/{product_id}` - Get product details
- `PATCH /api/products/{product_id}` - Update product
- `DELETE /api/products/{product_id}` - Soft delete product
- `GET /api/products/{product_id}/icps` - Get ideal customer profiles
- `PATCH /api/products/{product_id}/icps` - Update ICPs

### Lead Management
- `POST /api/companies/{company_id}/leads/upload` - Upload leads CSV
- `POST /api/companies/{company_id}/leads` - Create single lead
- `GET /api/companies/{company_id}/leads` - List leads (paginated)
- `GET /api/leads/{lead_id}` - Get lead details with communication history
- `DELETE /api/leads/{lead_id}` - Delete lead
- `POST /api/leads/{lead_id}/enrich` - Manually trigger enrichment
- `GET /api/leads/search` - Search leads by email or phone

### Campaign Management
- `POST /api/companies/{company_id}/campaigns` - Create campaign
- `GET /api/companies/{company_id}/campaigns` - List campaigns
- `GET /api/campaigns/{campaign_id}` - Get campaign details
- `POST /api/campaigns/{campaign_id}/run` - Execute campaign
- `POST /api/campaigns/{campaign_id}/test-run` - Test campaign with single lead
- `GET /api/campaigns/{campaign_id}/runs` - List campaign execution history
- `POST /api/campaigns/{campaign_id}/retry` - Retry failed campaign items
- `POST /api/campaigns/{campaign_id}/generate-campaign` - AI-generate campaign content

### Email Management
- `GET /api/companies/{company_id}/emails` - List email logs (paginated)
- `GET /api/emails/{email_log_id}` - Get email conversation thread
- `POST /api/companies/{company_id}/emails/throttle` - Update email throttle settings
- `GET /api/companies/{company_id}/emails/throttle` - Get throttle settings

### Call Management
- `GET /api/companies/{company_id}/calls` - List call logs (paginated)
- `GET /api/calls/{call_id}` - Get call details
- `POST /api/webhooks/bland` - Bland AI webhook for call updates

### Queue Management
- `GET /api/companies/{company_id}/email-queues` - View email queue
- `GET /api/companies/{company_id}/call-queues` - View call queue
- `GET /api/campaign-runs/{campaign_run_id}/email-queues` - View run-specific email queue
- `POST /api/call-queues/{queue_id}/retry` - Retry failed call queue item

### Calendar Integration
- `GET /api/calendar/connect` - Initiate Cronofy OAuth
- `GET /api/calendar/callback` - Cronofy OAuth callback
- `POST /api/calendar/disconnect` - Disconnect calendar
- `POST /api/book-appointment` - Book meeting slot

### LinkedIn Integration
- `POST /api/linkedin/auth` - Create LinkedIn hosted auth link
- `GET /api/linkedin/accounts` - List connected LinkedIn accounts
- `DELETE /api/linkedin/accounts/{account_id}` - Disconnect LinkedIn account
- `GET /api/linkedin/messaging/stats` - Get LinkedIn messaging statistics
- `POST /api/webhooks/unipile` - Unipile webhook for LinkedIn events

### Subscription & Billing
- `POST /api/checkout-sessions` - Create Stripe checkout session
- `GET /api/subscriptions/current` - Get current subscription details
- `POST /api/subscriptions/cancel` - Cancel subscription
- `POST /api/subscriptions/update` - Update subscription
- `POST /api/webhooks/stripe` - Stripe webhook handler

### Partner Applications
- `POST /api/partner-applications` - Submit partnership application
- `GET /api/partner-applications` - List applications (admin)
- `GET /api/partner-applications/{application_id}` - Get application details
- `PATCH /api/partner-applications/{application_id}/status` - Update application status
- `POST /api/partner-applications/{application_id}/notes` - Add note to application
- `GET /api/partner-applications/stats` - Get application statistics

### Web Agent (Bland AI Integration)
- `POST /api/web-agent/create` - Create web voice agent
- `POST /api/web-agent/webhook` - Web agent webhook handler

### File Management
- `GET /api/upload-tasks` - List upload tasks (paginated)
- `GET /api/upload-tasks/{task_id}/skipped-rows` - Get skipped rows from upload
- `POST /api/files/download/leads` - Download leads template
- `POST /api/files/download/do-not-email` - Download do-not-email template

### Do Not Email Management
- `POST /api/do-not-email/add` - Add email to suppression list
- `GET /api/do-not-email/list` - List suppressed emails
- `DELETE /api/do-not-email/{id}` - Remove from suppression list
- `POST /api/do-not-email/bulk-import` - Bulk import suppression list
- `GET /api/do-not-email/check` - Check if email is suppressed

### Script Generation (Testing/Preview)
- `POST /api/campaigns/{campaign_id}/generate-call-script` - Generate call script preview
- `POST /api/campaigns/{campaign_id}/generate-email-script` - Generate email preview

## Installation & Setup

### Prerequisites
- Python 3.12+
- PostgreSQL (via Supabase or self-hosted)
- Redis
- Required API keys (OpenAI, Bland AI, Stripe, etc.)

### Installation Methods

#### Option 1: Install from PyPI (Recommended)

```bash
pip install reachgenie
```

Then run:
```bash
reachgenie
```

#### Option 2: Install from GitHub

```bash
pip install git+https://github.com/alinaqi/reachgenie.git
```

#### Option 3: Development Installation

1. **Clone the repository**
```bash
git clone https://github.com/alinaqi/reachgenie.git
cd reachgenie/backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install in development mode**
```bash
# Install package in editable mode
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

### Configuration

1. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

2. **Set up database**
```bash
# Run schema.sql on your PostgreSQL database
psql -U postgres -d your_database -f schema.sql

# Run any pending migrations
# Check the migrations/ directory for migration files
```

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

### Docker Deployment

1. **Build and start services**
```bash
docker compose up -d
```

This starts:
- **web**: FastAPI application (port 8000)
- **redis**: Redis server (port 6379)
- **celery_worker**: Background task processor
- **flower**: Celery monitoring dashboard (port 5555)

2. **View logs**
```bash
docker compose logs -f
```

3. **Stop services**
```bash
docker compose down
```

## Environment Variables

Create a `.env` file in the root directory with the following variables:

### Database & Core
```bash
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_role_key
JWT_SECRET_KEY=your_jwt_secret_key_here
```

### AI Services
```bash
OPENAI_API_KEY=sk-your-openai-api-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
PERPLEXITY_API_KEY=pplx-your-perplexity-key
```

### Voice Calls (Bland AI)
```bash
BLAND_API_KEY=your_bland_api_key
BLAND_TOOL_ID=your_bland_tool_id
BLAND_SECRET_KEY=your_bland_tool_secret
WEBHOOK_BASE_URL=https://your-domain.com
```

### Email Services
```bash
MAILJET_API_KEY=your_mailjet_api_key
MAILJET_API_SECRET=your_mailjet_api_secret
MAILJET_SENDER_EMAIL=verified-sender@yourdomain.com
MAILJET_SENDER_NAME=ReachGenie
MAILJET_WEBHOOK_SECRET=your_mailjet_webhook_secret
MAILJET_PARSE_EMAIL=parse@yourdomain.com
```

### Partner Application Emails
```bash
NOREPLY_EMAIL=noreply@yourdomain.com
NOREPLY_PASSWORD=your_email_app_password
NOREPLY_PROVIDER=gmail  # or outlook, yahoo
```

### Calendar Integration
```bash
CRONOFY_CLIENT_ID=your_cronofy_client_id
CRONOFY_CLIENT_SECRET=your_cronofy_client_secret
CALENDLY_USERNAME=your_calendly_username
```

### LinkedIn (Unipile)
```bash
UNIPILE_API_KEY=your_unipile_api_key
UNIPILE_DSN=your_unipile_dsn
UNIPILE_WEBHOOK_SECRET=your_unipile_webhook_secret
LINKEDIN_MESSAGING_ENABLED=true
LINKEDIN_DAILY_INVITE_LIMIT=80
LINKEDIN_DAILY_PROFILE_VIEW_LIMIT=100
LINKEDIN_MESSAGE_DELAY_SECONDS=20
```

### Payment Processing (Stripe)
```bash
STRIPE_SECRET_KEY=sk_test_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_MEETINGS_BOOKED_METER_ID=mtr_your_meter_id

# Fixed Plan Price IDs
STRIPE_PRICE_FIXED_2500=price_xxx
STRIPE_PRICE_FIXED_5000=price_xxx
STRIPE_PRICE_FIXED_7500=price_xxx
STRIPE_PRICE_FIXED_10000=price_xxx

# Performance Plan Price IDs
STRIPE_PRICE_PERFORMANCE_2500=price_xxx
STRIPE_PRICE_PERFORMANCE_5000=price_xxx
STRIPE_PRICE_PERFORMANCE_7500=price_xxx
STRIPE_PRICE_PERFORMANCE_10000=price_xxx
STRIPE_PRICE_PERFORMANCE_MEETINGS=price_xxx

# Channel Add-on Price IDs
STRIPE_PRICE_EMAIL_FIXED=price_xxx
STRIPE_PRICE_PHONE_FIXED=price_xxx
STRIPE_PRICE_LINKEDIN_FIXED=price_xxx
STRIPE_PRICE_EMAIL_PERFORMANCE=price_xxx
STRIPE_PRICE_PHONE_PERFORMANCE=price_xxx
STRIPE_PRICE_LINKEDIN_PERFORMANCE=price_xxx
```

### Security & Monitoring
```bash
ENCRYPTION_KEY=your_32_byte_encryption_key
ENCRYPTION_SALT=your_salt_value
BUGSNAG_API_KEY=your_bugsnag_api_key
ENVIRONMENT=development  # or staging, production
```

### Application Settings
```bash
FRONTEND_URL=http://localhost:3000
REDIS_URL=redis://localhost:6379/0
```

### PostgreSQL (if self-hosting)
```bash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_DB=reachgenie
POSTGRES_PORT=5432
```

## Running the Application

### Development Mode

**Using Python directly:**
```bash
# Activate virtual environment
source venv/bin/activate

# Run FastAPI with auto-reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# In separate terminal, start Redis
redis-server

# In another terminal, start Celery worker
celery -A src.celery_app.tasks worker --loglevel=info

# (Optional) Start Flower for Celery monitoring
celery -A src.celery_app.tasks flower --port=5555
```

**Using Docker Compose:**
```bash
docker compose up
```

### Production Mode

1. **Build the Docker image:**
```bash
docker compose build
```

2. **Start services:**
```bash
docker compose up -d
```

3. **Set up reverse proxy (nginx example):**
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

4. **Set up SSL with Let's Encrypt:**
```bash
sudo certbot --nginx -d api.yourdomain.com
```

### Accessing the Application

- **API Documentation**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **Flower Dashboard**: http://localhost:5555 (admin/password)
- **Health Check**: http://localhost:8000/

## Background Jobs & Cron Tasks

ReachGenie uses cron jobs for automated background processing. These scripts should be scheduled using crontab or a task scheduler.

### Cron Schedule Configuration

Add these to your crontab (`crontab -e`):

```bash
# Process email queue every minute
* * * * * cd /path/to/backend && bash crons/process_email_queue.sh

# Process call queue every minute
* * * * * cd /path/to/backend && bash crons/process_call_queue.sh

# Process incoming emails every 5 minutes (replies, bounces)
*/5 * * * * cd /path/to/backend && bash crons/process_emails.sh

# Process email bounces every 10 minutes
*/10 * * * * cd /path/to/backend && bash crons/process_bounces.sh

# Send email reminders every hour
0 * * * * cd /path/to/backend && bash crons/send_reminders.sh

# Send call reminders every 2 hours
0 */2 * * * cd /path/to/backend && bash crons/send_call_reminders.sh

# Update call statistics daily at 2 AM
0 2 * * * cd /path/to/backend && bash crons/update_call_stats.sh

# Run scheduled campaigns every hour
0 * * * * cd /path/to/backend && bash crons/run_scheduled_campaigns.sh

# Populate campaign schedule daily at 1 AM
0 1 * * * cd /path/to/backend && bash crons/campaign_schedule_populator.sh

# Send campaign statistics email daily at 9 AM
0 9 * * * cd /path/to/backend && bash crons/send_campaign_run_stats_email.sh
```

### Cron Job Descriptions

#### Email Queue Processor (`process_email_queue.sh`)
- **Frequency**: Every minute
- **Purpose**: Processes pending emails in the queue
- **Features**:
  - Respects throttle limits (hourly/daily)
  - Handles retries with exponential backoff
  - Tracks email delivery status
  - Updates email logs

#### Call Queue Processor (`process_call_queue.sh`)
- **Frequency**: Every minute
- **Purpose**: Processes pending calls in the queue
- **Features**:
  - Respects business hours
  - Initiates Bland AI calls
  - Handles call failures and retries
  - Updates call logs

#### Email Processor (`process_emails.sh`)
- **Frequency**: Every 5 minutes
- **Purpose**: Monitors inbox for replies and processes them
- **Features**:
  - Detects email replies
  - AI-powered response generation
  - Updates conversation threads
  - Detects meeting booking intent

#### Bounce Processor (`process_bounces.sh`)
- **Frequency**: Every 10 minutes
- **Purpose**: Processes email bounces and updates suppression list
- **Features**:
  - Parses bounce notifications
  - Automatically adds to do-not-email list
  - Categorizes bounce types (hard/soft)
  - Updates lead status

#### Email Reminder Sender (`send_reminders.sh`)
- **Frequency**: Every hour
- **Purpose**: Sends follow-up emails to non-responders
- **Features**:
  - Checks reminder eligibility
  - AI-generated contextual reminders
  - Respects reminder limits
  - Tracks reminder sequence

#### Call Reminder Sender (`send_call_reminders.sh`)
- **Frequency**: Every 2 hours
- **Purpose**: Follows up on unsuccessful calls
- **Features**:
  - Identifies callback candidates
  - Schedules retry attempts
  - Respects call limits
  - Different scripts for different call outcomes

#### Call Stats Updater (`update_call_stats.sh`)
- **Frequency**: Daily at 2 AM
- **Purpose**: Updates call analytics and statistics
- **Features**:
  - Aggregates call metrics
  - Calculates conversion rates
  - Updates dashboard data
  - Generates reports

#### Scheduled Campaign Runner (`run_scheduled_campaigns.sh`)
- **Frequency**: Every hour
- **Purpose**: Executes campaigns scheduled for specific times
- **Features**:
  - Checks scheduled_at timestamps
  - Triggers campaign execution
  - Handles timezone conversions
  - Prevents duplicate runs

#### Campaign Schedule Populator (`campaign_schedule_populator.sh`)
- **Frequency**: Daily at 1 AM
- **Purpose**: Pre-schedules campaign messages for optimal delivery
- **Features**:
  - Analyzes best send times
  - Creates message schedule
  - Optimizes for time zones
  - Balances sending load

#### Campaign Stats Emailer (`send_campaign_run_stats_email.sh`)
- **Frequency**: Daily at 9 AM
- **Purpose**: Sends performance summaries to users
- **Features**:
  - Aggregates campaign metrics
  - AI-generated insights
  - Benchmark comparisons
  - Actionable recommendations

### Celery Background Tasks

#### Campaign Execution (`run_campaign`)
- **Trigger**: User initiates campaign
- **Purpose**: Asynchronous campaign processing
- **Process**:
  1. Fetch campaign and company details
  2. Retrieve eligible leads
  3. Generate personalized content for each lead
  4. Queue emails/calls for delivery
  5. Update campaign run status

#### Lead Upload Processing (`process_leads`)
- **Trigger**: CSV file upload
- **Purpose**: Async lead import and validation
- **Process**:
  1. Download CSV from storage
  2. Validate data format
  3. Check for duplicates
  4. Enrich with AI where possible
  5. Save to database
  6. Track skipped rows

#### Do Not Contact Processing (`process_do_not_contact`)
- **Trigger**: Bulk suppression list upload
- **Purpose**: Import bounce/unsubscribe lists
- **Process**:
  1. Parse CSV file
  2. Validate email format
  3. Add to suppression table
  4. Prevent duplicates

## Integrations

### OpenAI (Content Generation)
- **Purpose**: Email content and call script generation
- **Models Used**: GPT-4, GPT-3.5-turbo
- **Use Cases**:
  - Personalized email composition
  - Subject line generation
  - Follow-up email crafting
  - Call script personalization
  - Response analysis

### Anthropic Claude (Advanced AI)
- **Purpose**: Enhanced content generation and analysis
- **Models Used**: Claude 3 (Opus, Sonnet)
- **Use Cases**:
  - Long-form content generation
  - Complex personalization
  - Strategic messaging
  - Campaign summaries

### Perplexity AI (Lead Enrichment)
- **Purpose**: Company and prospect research
- **Use Cases**:
  - Company background research
  - Industry analysis
  - Pain point identification
  - Recent news and events
  - Technology stack detection

### Bland AI (Voice Calls)
- **Purpose**: Automated AI-powered phone calls
- **Features**:
  - Natural voice synthesis
  - Real-time conversation
  - Meeting booking via tools
  - Call recording and transcription
  - Sentiment analysis
  - Webhook callbacks
- **Integration Points**:
  - `/start-call` endpoint for initiation
  - Webhook receiver for call updates
  - Tool integration for calendar booking

### Stripe (Payments & Subscriptions)
- **Purpose**: Subscription billing and metering
- **Features**:
  - Trial management (14 days)
  - Fixed plan subscriptions ($99-$399/month)
  - Performance plan metering ($50/meeting)
  - Channel add-ons ($49-$99/month)
  - Usage-based billing
  - Webhook event processing
- **Events Handled**:
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`

### Cronofy (Calendar Integration)
- **Purpose**: Meeting scheduling automation
- **Features**:
  - OAuth authentication
  - Multi-calendar support (Google, Outlook, iCloud)
  - Availability checking
  - Event creation
  - Meeting confirmations
- **Flow**:
  1. User connects calendar via OAuth
  2. System checks availability
  3. Prospect selects time slot
  4. Meeting auto-booked
  5. Both parties notified

### Mailjet (Email Delivery)
- **Purpose**: Transactional and campaign email delivery
- **Features**:
  - High deliverability rates
  - Email tracking (opens, clicks)
  - Bounce handling
  - Template management
  - Webhook events
- **Use Cases**:
  - Campaign email delivery
  - Welcome emails
  - Verification emails
  - Password reset
  - System notifications

### Unipile (LinkedIn Automation)
- **Purpose**: LinkedIn outreach automation
- **Features**:
  - Account connection via hosted auth
  - Connection request automation
  - Automated messaging
  - Profile viewing
  - Message threading
  - Rate limiting (80 invites/day, 100 views/day)
- **Safety Features**:
  - Human-like delays
  - Daily limit enforcement
  - Activity randomization

### Bugsnag (Error Monitoring)
- **Purpose**: Error tracking and alerting
- **Features**:
  - Automatic error capture
  - Stack trace analysis
  - Release tracking
  - User impact analysis
  - Team notifications

## Development Guide

### Code Structure Principles

1. **Separation of Concerns**: Routes handle HTTP, services contain business logic
2. **Async/Await**: All I/O operations are asynchronous
3. **Type Hints**: Pydantic models for request/response validation
4. **Error Handling**: Comprehensive exception handling with Bugsnag integration
5. **Security**: JWT authentication, password hashing, encrypted credentials

### Adding a New Feature

1. **Define Pydantic Models** (`src/models.py`)
```python
class NewFeatureRequest(BaseModel):
    name: str
    description: Optional[str] = None

class NewFeatureResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
```

2. **Create Database Functions** (`src/database.py`)
```python
async def create_new_feature(name: str, description: str):
    query = """
        INSERT INTO new_features (name, description)
        VALUES ($1, $2)
        RETURNING *
    """
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(query, name, description)
        return dict(row)
```

3. **Add Business Logic** (`src/services/new_feature_service.py`)
```python
class NewFeatureService:
    async def process_feature(self, data: dict):
        # Business logic here
        return result
```

4. **Create Route** (`src/routes/new_feature.py`)
```python
router = APIRouter(prefix="/api/new-features", tags=["New Features"])

@router.post("/", response_model=NewFeatureResponse)
async def create_feature(
    request: NewFeatureRequest,
    current_user: dict = Depends(get_current_user)
):
    result = await create_new_feature(request.name, request.description)
    return result
```

5. **Register Router** (`src/main.py`)
```python
from src.routes.new_feature import router as new_feature_router
app.include_router(new_feature_router)
```

### Testing

Run the test suite:
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py

# Run with coverage
pytest --cov=src tests/

# Run with verbose output
pytest -v
```

### Database Migrations

1. Create migration file in `migrations/` directory
2. Name it with timestamp: `YYYY-MM-DD-description.sql`
3. Run migration:
```bash
psql -U postgres -d reachgenie -f migrations/2025-09-30-add-new-feature.sql
```

### Debugging

**Enable debug logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Use Flower to monitor Celery:**
```bash
# Access at http://localhost:5555
# Default credentials: admin/password
```

**Check Redis queue:**
```bash
redis-cli
> LLEN celery
> LRANGE celery 0 -1
```

## Project Structure

```
backend/
├── src/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Configuration and settings
│   ├── models.py              # Pydantic models
│   ├── database.py            # Database operations
│   ├── auth.py                # Authentication logic
│   ├── bland_client.py        # Bland AI integration
│   ├── perplexity_enrichment.py  # Lead enrichment
│   │
│   ├── routes/                # API route handlers
│   │   ├── accounts.py        # Account management
│   │   ├── calendar.py        # Calendar integration
│   │   ├── call_queues.py     # Call queue management
│   │   ├── call_queue_status.py
│   │   ├── campaign_retry.py  # Campaign retry logic
│   │   ├── checkout_sessions.py  # Stripe checkout
│   │   ├── companies.py       # Company CRUD
│   │   ├── do_not_email.py    # Suppression list
│   │   ├── email_queues.py    # Email queue management
│   │   ├── file_downloads.py  # Template downloads
│   │   ├── linkedin.py        # LinkedIn integration
│   │   ├── partner_applications.py
│   │   ├── skipped_rows.py    # Upload error handling
│   │   ├── stripe_webhooks.py # Stripe webhooks
│   │   ├── subscriptions.py   # Subscription management
│   │   ├── unipile_webhooks.py # LinkedIn webhooks
│   │   ├── upload_tasks.py    # Async upload tracking
│   │   └── web_agent.py       # Web voice agent
│   │
│   ├── services/              # Business logic layer
│   │   ├── advanced_reminders/
│   │   │   ├── behavioral_triggers.py
│   │   │   ├── dynamic_content.py
│   │   │   ├── enhanced_reminder_generator.py
│   │   │   └── reminder_strategies.py
│   │   ├── bland_calls.py     # Call initiation
│   │   ├── call_generation.py # Script generation
│   │   ├── call_queue_processor.py
│   │   ├── campaign_schedule_populator.py
│   │   ├── campaign_stats_emailer.py
│   │   ├── campaigns.py       # Campaign orchestration
│   │   ├── company_personalization_service.py
│   │   ├── email_generation.py # Email content generation
│   │   ├── email_open_detector.py
│   │   ├── email_queue_processor.py
│   │   ├── email_service.py   # Email sending
│   │   ├── linkedin_campaign_processor.py
│   │   ├── linkedin_service.py
│   │   ├── partner_application_service.py
│   │   ├── perplexity_service.py
│   │   ├── stripe_service.py
│   │   └── subscriptions.py
│   │
│   ├── ai_services/           # AI integration layer
│   │   ├── anthropic_service.py
│   │   └── message_generation.py
│   │
│   ├── celery_app/            # Celery configuration
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── tasks/
│   │       ├── __init__.py
│   │       ├── process_do_not_contact.py
│   │       ├── process_leads.py
│   │       └── run_campaign.py
│   │
│   ├── scripts/               # Cron job scripts
│   │   ├── campaign_schedule_populator.py
│   │   ├── check_mailjet_config.py
│   │   ├── check_postgres_connection.py
│   │   ├── create_bland_web_agent.py
│   │   ├── enhanced_reminders/
│   │   ├── generate_campaign_summary_email.py
│   │   ├── generate_company_campaign_summary.py
│   │   ├── list_campaigns.py
│   │   ├── process_bounces.py
│   │   ├── process_call_queues.py
│   │   ├── process_email_queues.py
│   │   ├── process_emails.py
│   │   ├── run_email_processor.py
│   │   ├── run_scheduled_campaigns.py
│   │   ├── send_call_reminders.py
│   │   ├── send_campaign_run_stats_email.py
│   │   ├── send_reminders.py
│   │   ├── send_reminders_enhanced.py
│   │   ├── setup_stripe_products.py
│   │   ├── test_*.py          # Various test scripts
│   │   └── update_call_stats.py
│   │
│   ├── utils/                 # Utility functions
│   │   ├── calendar_utils.py  # Calendar helpers
│   │   ├── email_utils.py     # Email formatting
│   │   ├── encryption.py      # Password encryption
│   │   ├── file_parser.py     # CSV parsing
│   │   ├── llm.py             # LLM utilities
│   │   ├── smtp_client.py     # SMTP client
│   │   └── string_utils.py    # String operations
│   │
│   ├── prompts/               # AI prompts
│   │   ├── company_info_prompt.py
│   │   └── company_insights_prompt.py
│   │
│   ├── templates/             # Email templates
│   │   └── email_templates.py
│   │
│   └── web/                   # Web assets
│       └── tracker.png        # Email tracking pixel
│
├── crons/                     # Cron shell scripts
│   ├── campaign_schedule_populator.sh
│   ├── process_bounces.sh
│   ├── process_call_queue.sh
│   ├── process_email_queue.sh
│   ├── process_emails.sh
│   ├── run_scheduled_campaigns.sh
│   ├── send_call_reminders.sh
│   ├── send_campaign_run_stats_email.sh
│   ├── send_reminders.sh
│   └── update_call_stats.sh
│
├── docs/                      # Documentation
│   ├── README.md
│   ├── architecture.md
│   ├── campaign_summary_email.md
│   ├── development.md
│   ├── email_ai_reply.md
│   ├── email_bounce_handling.md
│   ├── email_campaigns.md
│   ├── installation.md
│   ├── marketing_guide.md
│   ├── partnership_flow.md
│   ├── partnership_frontend_guide.md
│   ├── product_enrichment_guideline.md
│   ├── stripe-integration.md
│   ├── web_agent.md
│   └── workflows.md
│
├── migrations/                # Database migrations
│   └── *.sql
│
├── tests/                     # Test suite
│   ├── test_auth.py
│   ├── test_campaigns.py
│   └── ...
│
├── .env.example               # Environment template
├── .gitignore
├── docker-compose.yml         # Docker orchestration
├── Dockerfile                 # Container definition
├── leads_fields.json          # Lead CSV mapping
├── postgres_functions.sql     # PostgreSQL functions
├── requirements.txt           # Python dependencies
├── schema.sql                 # Database schema
└── README.md                  # This file
```

## Key Services Explained

### Campaign Execution Flow
1. User creates campaign via API
2. Campaign queued in Celery
3. Worker picks up task
4. Fetches eligible leads
5. For each lead:
   - AI enrichment (if needed)
   - Content generation (email/script)
   - Queue in Redis
6. Queue processor sends/calls
7. Track responses and engagement
8. Trigger follow-ups based on rules

### Email Processing Flow
1. Email added to Redis queue
2. Queue processor checks throttle limits
3. SMTP client sends email
4. Message-ID and References headers set for threading
5. Email log created with tracking pixel
6. IMAP monitor watches for replies
7. AI generates contextual response
8. Response sent and logged

### Call Processing Flow
1. Call added to Redis queue
2. Queue processor checks business hours
3. Script generated with AI
4. Bland AI initiates call
5. Real-time conversation with tools
6. Calendar booking if interest shown
7. Webhook receives call results
8. Sentiment analysis and logging

---

## Support & Contributing

For issues, questions, or contributions, please:
1. Check existing documentation in `/docs`
2. Review API documentation at `/docs` endpoint
3. Submit issues with detailed reproduction steps
4. Follow code style and testing requirements

## Campaign Summary Email Feature

ReachGenie now includes a comprehensive Campaign Summary Email feature that provides customers with detailed reports on their campaign performance, prospect enrichment, and email management activities.

### Features

- Detailed prospect enrichment information with examples
- Automated email management metrics (bounces and unsubscribes)
- Comprehensive campaign results with industry benchmark comparisons
- Next steps information and scheduling

### Usage

Send a campaign summary email via API:

```bash
curl -X POST "https://api.reachgenie.com/api/campaigns/{campaign_id}/summary-email" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"recipient_email": "user@example.com"}'
```

For testing or manual generation, use the command-line script:

```bash
# Send the email
python -m src.scripts.generate_campaign_summary_email <campaign_id> <recipient_email>

# Save to file for testing
python -m src.scripts.test_campaign_summary <campaign_id> <recipient_email> --save-to-file
```

See the full documentation in [docs/campaign_summary_email.md](docs/campaign_summary_email.md).

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

### Commercial Use

For commercial use or if you need a commercial license, please contact:
**Ali Shaheen** - ashaheen@workhub.ai

The AGPL-3.0 license requires that:
- Any modifications to the software must be made available under the same license
- If you run a modified version on a server, you must make the source code available to users
- Commercial deployments may require a separate commercial license

See the [LICENSE](LICENSE) file for full details.

---

**Built with FastAPI, powered by AI, designed for scale.**
