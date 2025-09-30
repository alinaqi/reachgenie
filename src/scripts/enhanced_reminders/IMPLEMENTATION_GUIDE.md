# Enhanced Reminder System Implementation Guide

## Overview
This guide shows how to integrate the enhanced 7-stage reminder system with progressive strategies, dynamic content, and behavioral triggers into the existing ReachGenie backend.

## Key Features Implemented

### 1. Progressive Reminder Strategies (7 Stages)
- **Reminder 1**: Gentle Follow-up - acknowledges they're busy
- **Reminder 2**: Value Addition - shares new insights/resources
- **Reminder 3**: Social Proof - shares success stories
- **Reminder 4**: Problem-Solution Fit - addresses specific pain points
- **Reminder 5**: Urgency Creation - time-sensitive opportunities
- **Reminder 6**: Alternative Approach - asks for referral/right person
- **Reminder 7**: Professional Break-up - final respectful message

### 2. Dynamic Content Elements
- Time-based references (start of week, end of month, etc.)
- Role-based messaging (executive vs manager focus)
- Industry-specific challenges and language
- Company size considerations

### 3. Behavioral Triggers
- Engagement level tracking (none, low, medium, high)
- Strategy adjustment based on opens/clicks
- Different approaches for non-engaged leads
- Subject line variations based on engagement

## Integration Steps

### Step 1: Update Database Schema (if needed)
Add email engagement tracking tables if not already present:
```sql
-- Email opens tracking
CREATE TABLE IF NOT EXISTS email_opens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_log_id UUID REFERENCES email_logs(id),
    opened_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT,
    ip_address TEXT
);

-- Email clicks tracking  
CREATE TABLE IF NOT EXISTS email_clicks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_log_id UUID REFERENCES email_logs(id),
    clicked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    link_url TEXT,
    user_agent TEXT
);
```

### Step 2: Update the existing send_reminders.py
Replace the get_reminder_content function with the enhanced version that includes:
- Lead information lookup
- Email metrics retrieval
- Progressive strategy selection
- Dynamic content generation
- Behavioral adjustments

### Step 3: Modify Email Generation
Update the reminder generation to use the enhanced system with all context