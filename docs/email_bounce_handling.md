# Email Bounce Handling System

## Overview

The Email Bounce Handling System is an automated solution that monitors company email inboxes for bounce notifications, processes them to identify undeliverable email addresses, and maintains a "Do Not Email" list to prevent sending to invalid or problematic addresses in the future.

## Architecture Components

The system consists of several key components:

1. **Bounce Detection Service**: A scheduled process that connects to company email inboxes via IMAP to check for bounce notifications.
2. **Bounce Classification**: Identifies and categorizes bounces as either hard (permanent) or soft (temporary) failures.
3. **Do Not Email Registry**: A database table that maintains a list of email addresses that should not be contacted.
4. **Queue Integration**: Pre-send checking of email addresses against the Do Not Email list.

## Workflow

The email bounce handling system follows this workflow:

1. **Bounce Detection**:
   - Periodically connects to each company's email inbox using IMAP
   - Searches for email bounce notifications using common subject patterns
   - Tracks processing progress using UIDs to avoid re-processing

2. **Bounce Processing**:
   - Extracts the bounced email address from bounce notifications
   - Determines the bounce type (hard vs. soft)
   - Identifies the original email that triggered the bounce when possible
   - Logs bounce details for reporting

3. **Do Not Email Management**:
   - Adds email addresses from hard bounces to the Do Not Email list
   - Records the reason for adding to the list
   - Optionally associates the exclusion with a specific company
   - Maintains global exclusions that apply across all companies

4. **Queue Integration**:
   - Checks each outgoing email against the Do Not Email list
   - Skips sending to addresses on the list
   - Logs skipped emails with appropriate reason

## Database Schema

### Do Not Email Table

```sql
CREATE TABLE do_not_email (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT NOT NULL,
    reason TEXT NOT NULL, -- bounce, unsubscribe, complaint, manual, etc.
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE, -- NULL means global (applies to all companies)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Companies Table Updates

```sql
ALTER TABLE companies 
ADD COLUMN IF NOT EXISTS last_processed_bounce_uid TEXT DEFAULT NULL;
```

## Bounce Classification

The system differentiates between different types of bounces:

1. **Hard Bounces** (Permanent Failures):
   - Invalid email addresses
   - Non-existent domains
   - Recipient accounts that no longer exist
   - Email addresses added to the Do Not Email list

2. **Soft Bounces** (Temporary Failures):
   - Mailbox full errors
   - Server temporarily unavailable
   - Message too large
   - Rate limiting or greylisting
   - Not added to the Do Not Email list

## Implementation Components

### Bounce Detection Script (`process_bounces.py`)

This script runs periodically to:
- Connect to each company's email account
- Search for bounce messages using common subject patterns
- Extract bounced email addresses and classify bounce types
- Add hard bounces to the Do Not Email list
- Track the most recent processed bounce message

### Database Functions

Key database functions include:
- `add_to_do_not_email_list`: Add an email to the exclusion list
- `is_email_in_do_not_email_list`: Check if an email should be excluded
- `get_do_not_email_list`: Retrieve entries from the exclusion list
- `remove_from_do_not_email_list`: Remove an entry from the list
- `update_last_processed_bounce_uid`: Track bounce processing progress
- `get_email_log_by_message_id`: Find original emails from bounce notifications

### Email Queue Integration

The email queue processor:
- Checks each email against the Do Not Email list before sending
- Skips sending to excluded addresses
- Records skipped emails with appropriate reason

## Recommended Cron Schedule

For optimal performance:
- Run the bounce processing script every 30 minutes
- This balances timely processing with server load

## Best Practices

1. **Hard Bounce Handling**: 
   - Immediately add to Do Not Email list
   - Flag the lead record for review

2. **Soft Bounce Handling**:
   - Monitor frequency of soft bounces
   - Consider adding to Do Not Email list after multiple consecutive soft bounces

3. **Email Address Correction**:
   - Consider implementing a process to notify users of bounced emails
   - Provide a mechanism for users to correct invalid email addresses

## Limitations and Considerations

- Different email providers format bounce notifications differently
- Some bounce messages may not be detected if they don't match common patterns
- Bounce processing relies on access to the email account that sent the original messages 