# Installation Guide

## Prerequisites

### System Requirements
- Python 3.8 or higher
- PostgreSQL 12 or higher
- Redis (for background tasks)
- Git

### Required API Keys
1. **Supabase**
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `SUPABASE_SERVICE_KEY`

2. **OpenAI**
   - `OPENAI_API_KEY`

3. **Perplexity**
   - `PERPLEXITY_API_KEY`

4. **Bland AI**
   - `BLAND_API_KEY`
   - `BLAND_SECRET_KEY`
   - `BLAND_TOOL_ID` (obtained during setup)

5. **Mailjet**
   - `MAILJET_API_KEY`
   - `MAILJET_API_SECRET`

6. **Calendar Integration**
   - `CRONOFY_CLIENT_ID`
   - `CRONOFY_CLIENT_SECRET`

## Installation Steps

### 1. Clone the Repository
```bash
git clone <repository-url>
cd backend
```

### 2. Set Up Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Update `.env` with your API keys and configuration:
   ```env
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   SUPABASE_SERVICE_KEY=your_service_key
   
   OPENAI_API_KEY=your_openai_key
   PERPLEXITY_API_KEY=your_perplexity_key
   
   BLAND_API_KEY=your_bland_key
   BLAND_SECRET_KEY=your_bland_secret
   # BLAND_TOOL_ID will be obtained in step 5
   
   MAILJET_API_KEY=your_mailjet_key
   MAILJET_API_SECRET=your_mailjet_secret
   
   CRONOFY_CLIENT_ID=your_cronofy_id
   CRONOFY_CLIENT_SECRET=your_cronofy_secret
   
   # Encryption settings (generate secure random values)
   ENCRYPTION_KEY=your-32-character-encryption-key
   ENCRYPTION_SALT=your-16-character-salt
   ```

### 4. Database Setup
1. Start PostgreSQL database:
   ```bash
   docker compose up -d db
   ```

2. Run database migrations:
   ```bash
   alembic upgrade head
   ```

### 5. Bland AI Tool Setup
1. Start the application temporarily:
   ```bash
   uvicorn src.main:app --reload
   ```

2. Register the Bland AI tool:
   ```bash
   curl http://localhost:8000/register-bland-tool
   ```

3. Update `.env` with the received tool ID:
   ```env
   BLAND_TOOL_ID=TL-xxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```

4. Restart the application

### 6. Start the Application
```bash
# Development mode with auto-reload
uvicorn src.main:app --reload

# Production mode
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## Verification

### 1. Check API Documentation
- Visit `http://localhost:8000/docs` for Swagger UI
- Visit `http://localhost:8000/redoc` for ReDoc

### 2. Verify Environment
```bash
# Check database connection
curl http://localhost:8000/api/health/db

# Check API status
curl http://localhost:8000/api/health
```

### 3. Test Authentication
```bash
# Create a test user
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"your_password"}'
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify PostgreSQL is running: `docker compose ps`
   - Check database credentials in `.env`
   - Ensure database migrations are up to date

2. **API Key Issues**
   - Verify all required API keys are set in `.env`
   - Check API key permissions and quotas
   - Ensure keys are properly formatted

3. **Bland AI Tool Registration**
   - If registration fails, check `BLAND_API_KEY` and `BLAND_SECRET_KEY`
   - Verify webhook URL is accessible
   - Check server logs for detailed error messages

### Getting Help
- Check the [Development Guide](./development.md) for more details
- Review [API Documentation](./api/endpoints.md)
- Submit issues on the project repository 