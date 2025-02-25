# Outbound AI SDR API Documentation

## Overview
This API provides functionality for automated SDR (Sales Development Representative) operations, including lead management, email campaigns, and AI-powered calling capabilities.

## Key Features
- User Authentication & Management
- Company & Product Management
- Lead Management & Enrichment
- Lead-Product Personalized Enrichment (Coming Soon)
- Email Campaign Automation
- AI-Powered Calling Integration
- Calendar Integration
- Task Management

## Documentation Sections

### Development Guides
- [Installation Guide](installation.md)
- [Development Guide](development.md)
- [Architecture Overview](architecture.md)

### Workflow Documentation
- [Campaign Workflows](workflows.md)

### API Reference
- [API Endpoints](api/endpoints.md)

### Frontend Implementation
- [Product Management](frontend/product-management.md)

### Database
- [Database Schema](database/schema.md)

## System Architecture

### Core Components
1. FastAPI Backend (`src/main.py`)
2. Database Layer (`src/database.py`)
3. Authentication System (`src/auth.py`)
4. AI Integration Services
   - OpenAI Integration
   - Perplexity Integration
   - Bland AI Integration
5. Email Services
6. Calendar Integration

### Bland AI Integration
The system uses Bland AI for automated calling capabilities. Here's how it works:

1. **Tool Registration**
   - The system registers a custom appointment booking tool with Bland AI
   - Endpoint: `/register-bland-tool`
   - This returns a `BLAND_TOOL_ID` which must be stored in environment variables
   - The tool ID is used for all subsequent calls to enable appointment booking functionality

2. **Environment Configuration**
   ```env
   BLAND_API_KEY=your_bland_api_key
   BLAND_TOOL_ID=your_tool_id  # Obtained from /register-bland-tool
   BLAND_SECRET_KEY=your_secret_key  # Used for webhook authentication
   ```

3. **Call Flow**
   - When initiating a call, the system includes the registered tool ID
   - This enables the AI agent to book appointments during calls
   - The tool communicates with your backend via webhooks for appointment scheduling

4. **Webhook Security**
   - All webhook calls from Bland AI include the secret key for authentication
   - The system verifies this key before processing webhook requests

### Directory Structure
```
src/
├── main.py              # Main application entry point
├── database.py          # Database operations
├── auth.py             # Authentication logic
├── config.py           # Configuration management
├── bland_client.py     # Bland AI integration
├── services/
│   ├── email_service.py
│   ├── bland_calls.py
│   └── perplexity_service.py
└── utils/
    ├── encryption.py
    └── calendar_utils.py
```

## Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL
- Redis
- API Keys for:
  - OpenAI
  - Perplexity
  - Bland AI
  - Mailjet
  - Cronofy/Calendly

### Installation
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables (see `.env.example`)
4. Register Bland AI tool: `curl http://localhost:8000/register-bland-tool`
5. Update `.env` with received `BLAND_TOOL_ID`
6. Start the server: `uvicorn src.main:app --reload`

## Additional Documentation
- [API Endpoints](./api/endpoints.md)
- [Database Schema](./database/schema.md)
- [Development Guide](./development.md)
- [AI Integration](./components/ai.md) 