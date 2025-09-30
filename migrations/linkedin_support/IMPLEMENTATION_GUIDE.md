# LinkedIn Messaging Implementation Guide for ReachGenie

## Overview
This guide outlines the implementation of LinkedIn messaging support using the Unipile API in ReachGenie.

## 1. Database Setup

Run the migration to create LinkedIn-specific tables:
```bash
psql -U your_user -d your_database -f migrations/linkedin_support/001_add_linkedin_support.sql
```

## 2. Environment Configuration

Add these to your `.env` file:
```env
UNIPILE_API_KEY=DBWJzDK8.f6jvVZxfyOP0Lv+A89gAm7MWVHLqj3IkDRKBR3ZCq60=
UNIPILE_DSN=api-us-01.unipile.com:8033  # Get from Unipile dashboard
UNIPILE_WEBHOOK_SECRET=generate_a_secure_secret_here
LINKEDIN_MESSAGING_ENABLED=true
LINKEDIN_DAILY_INVITE_LIMIT=80
LINKEDIN_DAILY_PROFILE_VIEW_LIMIT=100
LINKEDIN_MESSAGE_DELAY_SECONDS=20
```

## 3. Update Configuration

In `src/config.py`, add the new settings:
```python
# Unipile API settings
unipile_api_key: str = Field(..., env='UNIPILE_API_KEY')
unipile_dsn: str = Field(..., env='UNIPILE_DSN')
unipile_webhook_secret: Optional[str] = Field(None, env='UNIPILE_WEBHOOK_SECRET')

# LinkedIn Feature Configuration
linkedin_messaging_enabled: bool = Field(True, env='LINKEDIN_MESSAGING_ENABLED')
linkedin_daily_invite_limit: int = Field(80, env='LINKEDIN_DAILY_INVITE_LIMIT')
linkedin_daily_profile_view_limit: int = Field(100, env='LINKEDIN_DAILY_PROFILE_VIEW_LIMIT')
linkedin_message_delay_seconds: int = Field(20, env='LINKEDIN_MESSAGE_DELAY_SECONDS')
```

## 4. Core Services

### LinkedIn Service (`src/services/linkedin_service.py`)
- Handles all Unipile API interactions
- Account connection/reconnection
- Profile fetching
- Message sending
- Invitation management

### LinkedIn Campaign Processor (`src/services/linkedin_campaign_processor.py`)
- Processes LinkedIn campaigns
- Handles personalization
- Manages rate limiting
- Tracks campaign performance

### Message Generation Service (`src/ai_services/message_generation.py`)
- AI-powered message personalization
- Template processing
- Invitation message generation

## 5. API Routes

### LinkedIn Routes (`src/routes/linkedin.py`)
- `POST /api/v1/linkedin/connect` - Create connection
- `POST /api/v1/linkedin/reconnect/{connection_id}` - Reconnect account
- `GET /api/v1/linkedin/connections` - List connections
- `POST /api/v1/linkedin/sync-lead-profile` - Sync lead profile
- `GET /api/v1/linkedin/campaign-stats/{campaign_id}` - Campaign statistics
- `GET /api/v1/linkedin/chats/{connection_id}` - List chats

### Webhook Routes (`src/routes/unipile_webhooks.py`)
- `/api/v1/webhooks/unipile/account-status` - Account status updates
- `/api/v1/webhooks/unipile/account-connected` - New connection
- `/api/v1/webhooks/unipile/new-message` - Message received

## 6. Integration Steps

### Step 1: Register Routes
In `src/main.py`, add:
```python
from src.routes import linkedin, unipile_webhooks

app.include_router(linkedin.router)
app.include_router(unipile_webhooks.router)
```

### Step 2: Update Models
Update `src/models.py` with the new campaign types and LinkedIn fields.

### Step 3: Configure Webhooks in Unipile
1. Log into Unipile dashboard
2. Go to Webhooks section
3. Add webhooks for:
   - Account Status: `https://your-domain.com/api/v1/webhooks/unipile/account-status`
   - New Messages: `https://your-domain.com/api/v1/webhooks/unipile/new-message`

### Step 4: Update Campaign Processing
Modify `run_campaign.py` to handle LinkedIn campaign types.

## 7. Frontend Integration

### LinkedIn Connection Flow
1. User clicks "Connect LinkedIn" in company settings
2. Frontend calls `POST /api/v1/linkedin/connect`
3. Redirect user to Unipile auth URL
4. Handle success/failure redirects
5. Show connection status

### Campaign Creation
1. Add LinkedIn as campaign type option
2. Show LinkedIn-specific fields:
   - Message template
   - Invitation template
   - InMail option
   - LinkedIn reminders

### Lead Management
1. Add "Sync LinkedIn" button for leads
2. Display LinkedIn profile data
3. Show network distance

## 8. Testing

### Test Account Connection
```python
# Test creating connection link
response = await client.post(
    "/api/v1/linkedin/connect",
    json={"company_id": "your-company-id"}
)
auth_url = response.json()["auth_url"]
```

### Test Message Sending
```python
# Test sending a message
from src.services.linkedin_service import linkedin_service

result = await linkedin_service.send_message(
    account_id="unipile-account-id",
    attendee_id="linkedin-user-id",
    text="Hello from ReachGenie!",
    inmail=False
)
```

## 9. Rate Limiting Considerations

- **Invitations**: 80-100/day for paid accounts, 15/week for free
- **Profile Views**: 100/day (150 for Sales Navigator)
- **Messages**: 20-second delay between messages
- **Search Results**: 1,000 profiles/day

## 10. Error Handling

Common errors and solutions:
- `CREDENTIALS`: Account needs reconnection
- `429 Error`: Rate limit exceeded
- `cannot_resend_yet`: Invitation limit reached
- `insufficient_credit`: No InMail credits

## 11. Monitoring

Track these metrics:
- Connection status
- Daily invitation count
- Message send rate
- Reply rates
- Campaign performance

## 12. Security

- Always verify webhook signatures
- Encrypt stored Unipile account IDs
- Implement user access controls
- Log all LinkedIn operations

## Next Steps

1. Implement frontend components
2. Add LinkedIn reminder functionality
3. Build analytics dashboard
4. Add bulk lead LinkedIn sync
5. Implement LinkedIn post engagement features
