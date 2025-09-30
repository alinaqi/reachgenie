# Email AI Reply System

## Overview

The Email AI Reply System is an automated solution that monitors company email inboxes, detects customer replies to campaign emails, and generates contextually relevant AI-powered responses. This system creates an end-to-end communication loop that can maintain ongoing conversations with leads while minimizing manual intervention.

## Architecture Components

The system consists of several key components:

1. **Email Monitoring Service**: A scheduled process that connects to company email inboxes via IMAP to check for new replies.
2. **Message Processor**: Identifies relevant replies, extracts conversation context, and manages email threading.
3. **AI Generation Service**: Leverages OpenAI's GPT models to generate contextually appropriate responses.
4. **Email Delivery Service**: Sends AI-generated replies via SMTP with proper email threading metadata.
5. **Conversation History Store**: Maintains the full conversation context for improved response quality.

## Workflow

The email AI reply system follows this workflow:

1. **Inbox Monitoring**:
   - Periodically connects to each company's email inbox using IMAP
   - Identifies new emails since the last check using UIDs
   - Filters for emails that are replies to system-generated emails

2. **Reply Processing**:
   - Extracts email content, headers, and metadata
   - Identifies the original conversation by extracting the `email_log_id` from the recipient address
   - Updates the conversation history to mark the email as replied

3. **AI Response Generation**:
   - Retrieves the full conversation history for context
   - Constructs a prompt with conversation history and system instructions
   - Sends the prompt to OpenAI's GPT model
   - Processes the response, including special handling for appointment scheduling requests

4. **Response Delivery**:
   - Formats the AI-generated response with proper HTML structure
   - Saves the response to the conversation history
   - Sends the email via SMTP with proper threading headers
   - Updates tracking information for future reference

## Configuration Requirements

To use the Email AI Reply system, companies need:

1. **Email Credentials**:
   - SMTP/IMAP access to an email account
   - Supported providers: Gmail, Outlook, Yahoo
   - Proper authentication credentials stored securely

2. **OpenAI API Integration**:
   - Valid API key with access to GPT models
   - Usage limits and monitoring

3. **Optional Calendar Integration**:
   - Cronofy credentials for automated meeting scheduling
   - Calendar availability configuration

## Key Features

### Conversation Awareness
The system maintains full conversation history, allowing the AI to generate contextually relevant responses that reference previous exchanges.

### Email Threading
All replies are properly threaded using email headers (`In-Reply-To` and `References`), ensuring that the conversation appears as a continuous thread in recipients' email clients.

### Meeting Scheduling (Optional)
The system can detect meeting requests and automatically schedule meetings if Cronofy integration is available. It handles vague requests by asking for clarification and only books when specific times are provided.

### Secure Credential Management
Email credentials are encrypted in the database and only decrypted at runtime when needed for IMAP/SMTP connections.

### Multi-Provider Support
The system works with multiple email providers including Gmail, Outlook, and Yahoo.

## Technical Implementation

### Email Identification
The system identifies which emails to respond to by extracting an `email_log_id` from the recipient address. When sending campaign emails, each message uses a format like `prefix+email_log_id@domain` in the Reply-To header, allowing the system to track which campaign/sequence the reply belongs to.

### AI Response Configuration
- Uses OpenAI's GPT-4o-mini model (configurable)
- Temperature setting of 0.7 for balanced creativity/consistency
- System prompt with specific guidelines on professional tone
- Response formatting with proper email structure
- Function calling for appointment scheduling

### Processing Script
The email processing script (`process_emails.py`) can be scheduled to run at regular intervals to continuously monitor for new replies and maintain conversations.

## Usage Example

1. A campaign email is sent to a lead with a unique tracking ID in the Reply-To field
2. The lead replies to the email with questions
3. The system:
   - Detects the reply during its next IMAP check
   - Identifies which campaign/conversation the reply belongs to
   - Retrieves conversation history
   - Generates an AI response that addresses the lead's questions
   - Sends the response with proper email threading
   - Updates the conversation history

## Error Handling and Logging

The system includes comprehensive error handling and logging:
- Connection failures are logged and retried
- Individual email processing errors don't affect other emails
- Processing status is tracked to avoid duplicate processing
- Detailed logs for monitoring and debugging

## Limitations and Considerations

- Email processing frequency depends on the scheduled run frequency
- API rate limits for OpenAI and email providers need to be considered
- Complex or highly technical requests may require human intervention
- Meeting scheduling requires proper calendar configuration and availability 