# LinkedIn Integration Flow in ReachGenie

## Overview
The LinkedIn integration allows users to send personalized messages, connection invitations, and manage conversations directly from ReachGenie using their LinkedIn account.

## 1. Initial Setup Flow

### Step 1: Company LinkedIn Connection
```
User Journey:
1. User navigates to Company Settings
2. Clicks "Connect LinkedIn Account" button
3. System generates Unipile auth link
4. User is redirected to Unipile hosted auth page
5. User logs into LinkedIn through Unipile
6. Upon success, redirected back to ReachGenie
7. LinkedIn connection is saved and associated with company
```

### API Flow:
```
Frontend                    Backend                     Unipile API
    |                          |                            |
    |-- POST /linkedin/connect |                            |
    |                          |-- Create auth link ------->|
    |                          |<-- Return auth URL --------|
    |<-- Return auth URL ------|                            |
    |                                                       |
    |-- Redirect to Unipile -------------------------------->|
    |                                                       |
    |<-- User authenticates on LinkedIn --------------------|
    |                                                       |
    |<-- Redirect back with success -----------------------|
    |                          |                            |
    |                          |<-- Webhook: account created-|
    |                          |-- Store connection -------->|
```

## 2. Lead Enrichment Flow

### LinkedIn Profile Sync
```
User Journey:
1. User views lead details
2. Clicks "Sync LinkedIn Profile" button
3. System fetches LinkedIn profile data
4. Lead is enriched with LinkedIn information
5. Network distance is displayed (1st, 2nd, 3rd connection)
```

### Data Retrieved:
- Full name and headline
- Current position and company
- Skills and endorsements
- Work experience
- Education
- Network distance
- Profile URL
- Premium status

## 3. Campaign Creation Flow

### Multi-Channel Campaign Setup
```
User Journey:
1. User creates new campaign
2. Selects campaign type (LinkedIn, LinkedIn+Email, etc.)
3. Configures LinkedIn-specific settings:
   - Message template
   - Invitation template (if targeting non-connections)
   - InMail option (for premium accounts)
   - Number of reminders
   - Days between reminders
4. Uploads or selects leads
5. Schedules or runs campaign
```

### LinkedIn Template Variables:
- `{lead_first_name}` - Lead's first name
- `{lead_company}` - Lead's company name
- `{lead_title}` - Lead's job title
- `{lead_headline}` - LinkedIn headline
- `{company_name}` - Your company name
- `{product_name}` - Product being promoted

## 4. Campaign Execution Flow

### Message Sending Logic
```
For each lead in campaign:
1. Check LinkedIn connection status
   - If 1st degree → Send direct message
   - If 2nd/3rd degree → Send invitation first (if template provided)
   - If InMail enabled → Send InMail

2. Apply rate limiting
   - Max 80-100 invitations/day
   - 20-second delay between messages
   - Track daily limits per account

3. Message personalization
   - AI generates personalized content
   - Replaces template variables
   - Ensures message relevance

4. Send and track
   - Message sent via Unipile API
   - Store in database
   - Create campaign log entry
```

### Flow Diagram:
```
Campaign Start
    |
    v
Load Leads
    |
    v
For Each Lead:
    |
    ├─> Check LinkedIn ID exists?
    |     |
    |     No ──> Skip (log as skipped)
    |     |
    |     Yes
    |     v
    ├─> Check connection status
    |     |
    |     ├─> 1st degree ──> Send Message
    |     |
    |     ├─> 2nd/3rd degree
    |     |     |
    |     |     ├─> Has invitation template?
    |     |     |     |
    |     |     |     Yes ──> Send Invitation
    |     |     |     |
    |     |     |     No ──> Skip
    |     |     |
    |     |     └─> InMail enabled?
    |     |           |
    |     |           Yes ──> Send InMail
    |     |
    |     └─> Not connected ──> Send Invitation
    |
    ├─> Apply rate limiting (20s delay)
    |
    └─> Log results
```

## 5. Response Handling Flow

### Webhook Processing
```
Unipile Webhook Events:
1. New Message Received
   - Check if reply to campaign
   - Mark lead as "replied"
   - Trigger auto-reply if enabled
   - Notify user

2. Connection Accepted
   - Update lead status
   - Enable direct messaging
   - Trigger follow-up if configured

3. Account Status Change
   - Handle disconnections
   - Send reconnection alerts
   - Pause affected campaigns
```

### Conversation Management
```
User Journey:
1. User views campaign results
2. Sees reply rates and engagement
3. Clicks to view conversations
4. Can reply directly from ReachGenie
5. All messages synced bidirectionally
```

## 6. Analytics & Reporting Flow

### Campaign Performance Metrics
```
Tracked Metrics:
- Messages sent
- Invitations sent
- Invitations accepted
- Reply rate
- Meeting booking rate
- Response time
- Engagement by message variant
```

### Dashboard View:
```
LinkedIn Campaign: Q1 Outreach
├── Total Reached: 250
├── Messages Sent: 150
├── Invitations Sent: 100
├── Replies: 45 (30%)
├── Meetings Booked: 12 (8%)
└── Status: Active

Daily Breakdown:
- Monday: 50 messages, 10 replies
- Tuesday: 50 messages, 15 replies
- Wednesday: 50 messages, 12 replies
- Thursday: 50 messages, 8 replies
```

## 7. Error Handling & Recovery

### Common Scenarios:
1. **Rate Limit Exceeded**
   - Pause campaign
   - Queue remaining messages
   - Resume next day

2. **Account Disconnected**
   - Mark account as "CREDENTIALS"
   - Notify user via email
   - Provide reconnection link
   - Pause all campaigns

3. **Profile Not Found**
   - Log error
   - Skip lead
   - Continue with next

4. **Network Issues**
   - Retry with exponential backoff
   - Max 3 retries
   - Log failures

## 8. Security & Compliance

### Data Handling:
- LinkedIn tokens never stored directly
- All connections through Unipile (OAuth compliant)
- Webhook signatures verified
- User permissions checked at every step
- Audit logs for all LinkedIn operations

### LinkedIn Compliance:
- Respect daily limits
- Human-like delays between actions
- No spam or bulk messaging
- Personalized, relevant content only
- Clear opt-out mechanisms

## 9. User Interface Components

### Key UI Elements:
1. **Company Settings**
   - LinkedIn connection status
   - Connect/Reconnect buttons
   - Connection details

2. **Lead Management**
   - LinkedIn sync button
   - Profile preview
   - Network distance indicator

3. **Campaign Builder**
   - Channel selector
   - LinkedIn template editor
   - Preview with variable replacement

4. **Campaign Dashboard**
   - Real-time statistics
   - Conversation threads
   - Reply management

5. **Notifications**
   - New replies
   - Connection accepts
   - Account issues

## 10. Implementation Priority

### Phase 1 (MVP):
- Account connection
- Basic message sending
- Simple templates
- Reply tracking

### Phase 2:
- AI personalization
- Invitation management
- InMail support
- Advanced analytics

### Phase 3:
- Auto-reply sequences
- A/B testing
- Sales Navigator integration
- Bulk operations

This flow ensures a seamless LinkedIn integration that respects platform limits while providing powerful outreach capabilities.
