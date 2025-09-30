# LinkedIn Campaign - API Sequence

## Complete Campaign Flow - API Calls

### 1. Initial Setup (One-time per company)

```bash
# Step 1: Create LinkedIn connection
POST /api/v1/linkedin/connect
{
  "company_id": "550e8400-e29b-41d4-a716-446655440000"
}

# Response:
{
  "auth_url": "https://account.unipile.com/auth/...",
  "expires_in": 3600
}

# Step 2: User completes auth on Unipile
# Webhook received at: POST /api/v1/webhooks/unipile/account-connected
{
  "status": "CREATION_SUCCESS",
  "account_id": "unipile_account_123",
  "name": "550e8400-e29b-41d4-a716-446655440000:user_id"
}
```

### 2. Lead Preparation

```bash
# Step 1: Upload leads
POST /api/v1/leads/upload
Content-Type: multipart/form-data
{
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "file": leads.csv
}

# Step 2: Sync LinkedIn profiles for leads
POST /api/v1/linkedin/sync-lead-profile
{
  "lead_id": "lead_uuid_123",
  "linkedin_url": "https://www.linkedin.com/in/john-doe"
}

# Response:
{
  "status": "success",
  "message": "LinkedIn profile synced successfully",
  "profile_data": {
    "provider_id": "ACoAAAcDMMQBODyLwZrRcgYhrkCafURGqva0U4E",
    "headline": "CEO at Example Corp",
    "network_distance": "DISTANCE_2",
    "is_premium": true
  }
}
```

### 3. Campaign Creation

```bash
# Create LinkedIn campaign
POST /api/v1/campaigns
{
  "name": "Q1 2024 Outreach",
  "description": "LinkedIn outreach for product launch",
  "type": "linkedin",
  "product_id": "product_uuid_123",
  "linkedin_message_template": "Hi {lead_first_name},\n\nI noticed {lead_company} is expanding...",
  "linkedin_invitation_template": "Hi {lead_first_name}, I'd like to connect regarding...",
  "linkedin_inmail_enabled": false,
  "linkedin_number_of_reminders": 2,
  "linkedin_days_between_reminders": 3
}

# Response:
{
  "id": "campaign_uuid_456",
  "name": "Q1 2024 Outreach",
  "type": "linkedin",
  "created_at": "2024-01-15T10:00:00Z"
}
```

### 4. Campaign Execution

```bash
# Run campaign
POST /api/v1/campaigns/{campaign_id}/run
{
  "lead_ids": ["lead_1", "lead_2", "lead_3"]  # Optional, uses all if not specified
}

# Response:
{
  "campaign_run_id": "run_uuid_789",
  "status": "processing",
  "leads_total": 50
}

# Backend processes each lead:
# For each lead, internally calls Unipile API:

# If 2nd/3rd degree connection:
POST https://api.unipile.com/api/v1/users/invite
{
  "account_id": "unipile_account_123",
  "provider_id": "ACoAAAcDMMQBODyLwZrRcgYhrkCafURGqva0U4E",
  "message": "Hi John, I'd like to connect..."
}

# If 1st degree or after invitation accepted:
POST https://api.unipile.com/api/v1/chats
{
  "account_id": "unipile_account_123",
  "attendees_ids": ["ACoAAAcDMMQBODyLwZrRcgYhrkCafURGqva0U4E"],
  "text": "Hi John,\n\nI noticed Example Corp is expanding..."
}
```

### 5. Response Handling

```bash
# Webhook: New message received
POST /api/v1/webhooks/unipile/new-message
{
  "account_id": "unipile_account_123",
  "account_type": "LINKEDIN",
  "event": "message_received",
  "chat_id": "chat_123",
  "message_id": "msg_456",
  "message": "Thanks for reaching out! I'd be interested in learning more.",
  "sender": {
    "attendee_provider_id": "ACoAAAcDMMQBODyLwZrRcgYhrkCafURGqva0U4E",
    "attendee_name": "John Doe"
  }
}

# Get campaign statistics
GET /api/v1/linkedin/campaign-stats/{campaign_id}

# Response:
{
  "campaign": {
    "id": "campaign_uuid_456",
    "name": "Q1 2024 Outreach"
  },
  "stats": {
    "total_sent": 45,
    "replied": 12,
    "invitations_accepted": 8,
    "meetings_booked": 3
  },
  "reply_rate": 26.7,
  "meeting_rate": 6.7
}
```

### 6. Conversation Management

```bash
# Get LinkedIn chats
GET /api/v1/linkedin/chats/{connection_id}?limit=50&offset=0

# Response:
{
  "chats": [
    {
      "id": "chat_uuid_123",
      "unipile_chat_id": "unipile_chat_456",
      "last_message": "Thanks for reaching out!",
      "last_message_at": "2024-01-15T14:30:00Z",
      "message_count": 3
    }
  ]
}

# Reply to a message
POST /api/v1/linkedin/messages
{
  "chat_id": "chat_uuid_123",
  "text": "I'd be happy to schedule a call. Here's my calendar link..."
}
```

### 7. Error Scenarios

```bash
# Account disconnection webhook
POST /api/v1/webhooks/unipile/account-status
{
  "AccountStatus": {
    "account_id": "unipile_account_123",
    "account_type": "LINKEDIN",
    "message": "CREDENTIALS"
  }
}

# Reconnect account
POST /api/v1/linkedin/reconnect/{connection_id}

# Response:
{
  "auth_url": "https://account.unipile.com/reconnect/...",
  "expires_in": 3600
}

# Rate limit handling (internal)
# If daily limit reached:
{
  "error": "Daily invitation limit reached (80)",
  "retry_after": "2024-01-16T00:00:00Z"
}
```

## Rate Limiting Headers

All API responses include rate limit information:
```
X-RateLimit-Invitations-Remaining: 20
X-RateLimit-Invitations-Reset: 2024-01-16T00:00:00Z
X-RateLimit-Messages-Delay: 20
```

## Campaign Status Updates

```bash
# Get campaign run status
GET /api/v1/campaign-runs/{run_id}

# Response:
{
  "id": "run_uuid_789",
  "status": "completed",
  "leads_total": 50,
  "leads_processed": 50,
  "linkedin_sent": 45,
  "linkedin_failed": 2,
  "linkedin_skipped": 3,
  "completed_at": "2024-01-15T12:00:00Z"
}
```

## Bulk Operations

```bash
# Bulk sync LinkedIn profiles
POST /api/v1/linkedin/bulk-sync-profiles
{
  "lead_ids": ["lead_1", "lead_2", "lead_3", "lead_4", "lead_5"]
}

# Response:
{
  "synced": 4,
  "failed": 1,
  "results": [
    {"lead_id": "lead_1", "status": "success"},
    {"lead_id": "lead_2", "status": "success"},
    {"lead_id": "lead_3", "status": "failed", "error": "Profile not found"},
    {"lead_id": "lead_4", "status": "success"},
    {"lead_id": "lead_5", "status": "success"}
  ]
}
```

## Authentication Headers

All API calls require authentication:
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

## Error Responses

Standard error format:
```json
{
  "detail": "Error message",
  "code": "ERROR_CODE",
  "field": "field_name" // Optional
}
```

Common error codes:
- `LINKEDIN_NOT_CONNECTED` - No LinkedIn account connected
- `RATE_LIMIT_EXCEEDED` - Daily limit reached
- `PROFILE_NOT_FOUND` - LinkedIn profile doesn't exist
- `NETWORK_NOT_CONNECTED` - Target is not a connection
- `INSUFFICIENT_CREDITS` - No InMail credits available
