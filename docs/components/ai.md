# AI Integration Documentation

## Overview
The system integrates multiple AI services to provide intelligent features for sales automation:
1. OpenAI GPT-4 for content generation and conversation
2. Perplexity API for company research and lead enrichment
3. Bland AI for voice calls and conversation

## OpenAI Integration

### Content Generation
Located in `src/utils/llm.py`, the OpenAI integration handles:
- Email content generation
- Call script generation
- Campaign content generation

### Key Components

#### 1. Email Content Generation
```python
async def generate_email_content(lead: dict, campaign: dict, company: dict, insights: str) -> tuple[str, str]:
    """
    Generates personalized email content using GPT-4.
    
    Args:
        lead: Lead information
        campaign: Campaign details
        company: Company information
        insights: Generated company insights
        
    Returns:
        Tuple of (subject, body)
    """
```

#### 2. Call Script Generation
```python
async def generate_call_script(lead: dict, campaign: dict, company: dict, insights: str) -> str:
    """
    Generates personalized call scripts using GPT-4.
    
    Args:
        lead: Lead information
        campaign: Campaign details
        company: Company information
        insights: Generated company insights
        
    Returns:
        Generated call script
    """
```

#### 3. Campaign Content Generation
```python
async def generate_campaign(achievement_text: str) -> dict:
    """
    Generates campaign content based on achievement text.
    
    Args:
        achievement_text: Description of achievement
        
    Returns:
        Dictionary containing campaign content
    """
```

## Perplexity Integration

### Company Research
Located in `src/services/perplexity_service.py`, handles:
- Company information gathering
- Lead enrichment
- Industry insights

### Key Components

#### 1. Company Information
```python
async def fetch_company_info(website: str) -> dict:
    """
    Fetches detailed company information from website.
    
    Args:
        website: Company website URL
        
    Returns:
        Dictionary containing company details
    """
```

#### 2. Company Insights
```python
async def get_company_insights(
    company_name: str,
    company_website: str,
    company_description: str
) -> str:
    """
    Generates company insights for personalization.
    
    Args:
        company_name: Name of the company
        company_website: Company website
        company_description: Company description
        
    Returns:
        Generated insights
    """
```

## Bland AI Integration

### Tool Registration and Setup
1. **Initial Setup**
   ```bash
   # Register the appointment booking tool
   curl http://localhost:8000/register-bland-tool
   
   # Response will contain the tool_id:
   {
     "status": "success",
     "tool_id": "TL-xxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
   }
   ```

2. **Environment Configuration**
   ```env
   BLAND_API_KEY=your_bland_api_key
   BLAND_TOOL_ID=your_tool_id  # From registration response
   BLAND_SECRET_KEY=your_secret_key
   WEBHOOK_BASE_URL=your_webhook_url
   ```

### Components

1. **BlandClient** (`src/bland_client.py`)
   - Handles communication with Bland AI API
   - Manages call initiation and tool registration
   - Example usage:
     ```python
     client = BlandClient(
         api_key=settings.bland_api_key,
         bland_tool_id=settings.bland_tool_id,
         bland_secret_key=settings.bland_secret_key
     )
     ```

2. **Call Service** (`src/services/bland_calls.py`)
   - Manages call campaigns
   - Generates call scripts
   - Handles webhook responses

### Features

1. **Automated Calls**
   - Initiates calls using AI agent
   - Dynamic script generation based on context
   - Real-time appointment booking capability

2. **Appointment Booking Tool**
   - Custom tool for scheduling meetings
   - Integrates with calendar system
   - Secure webhook communication

3. **Call Analysis**
   - Sentiment analysis of calls
   - Call level classification
   - Detailed call summaries

### Webhook Integration

1. **Endpoint**: `/api/calls/webhook`
   - Receives call updates
   - Processes call summaries
   - Updates database with results

2. **Security**
   - Bearer token authentication
   - Secret key verification
   - Secure data transmission

### Example Call Flow

```python
# 1. Start a call
call = await bland_client.start_call(
    phone_number="1234567890",
    script="Your call script here",
)

# 2. Webhook receives updates
@app.post("/api/calls/webhook")
async def handle_bland_webhook(payload: BlandWebhookPayload):
    # Process call updates
    await update_call_webhook_data(
        bland_call_id=payload.call_id,
        duration=payload.duration,
        sentiment=payload.sentiment,
        summary=payload.summary
    )

# 3. Book appointment (via tool)
@app.post("/api/calls/book-appointment")
async def book_appointment(request: BookAppointmentRequest):
    await calendar_book_appointment(
        company_id=request.company_uuid,
        email=request.email,
        start_time=request.start_time
    )
```

## Prompt Templates

### Location
Prompts are stored in `src/prompts/` directory:
- `company_info_prompt.py`: Company research prompts
- `company_insights_prompt.py`: Insight generation prompts

### Example Prompt
```python
COMPANY_INFO_PROMPT = """
Analyze the following company website and extract key information:
Website: {website}

Please provide:
1. Company Overview
2. Background
3. Products/Services
4. Industry
5. Location/Address

Format the response as JSON with these exact fields.
"""
```

## Configuration

### Environment Variables
```env
# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Perplexity
PERPLEXITY_API_KEY=your-perplexity-api-key

# Bland AI
BLAND_API_KEY=your-bland-api-key
BLAND_API_URL=https://api.bland.ai
WEBHOOK_BASE_URL=your-webhook-base-url
```

## Best Practices

### 1. Error Handling
- Implement retries for API calls
- Handle rate limits gracefully
- Log all AI interactions
- Provide fallback content

### 2. Content Generation
- Use clear, specific prompts
- Include context in prompts
- Validate generated content
- Handle edge cases

### 3. Performance
- Cache frequently used data
- Use async calls when possible
- Implement request batching
- Monitor API usage

### 4. Security
- Secure API keys
- Validate all inputs
- Monitor for abuse
- Regular security audits

## Monitoring

### Logging
```python
logger = logging.getLogger(__name__)

# Log AI interactions
logger.info("Generating content for lead: %s", lead_id)
logger.error("API call failed: %s", error)
```

### Metrics to Track
1. API Response Times
2. Success/Failure Rates
3. Content Quality Metrics
4. Usage Patterns
5. Error Rates

## Testing

### Unit Tests
```python
def test_generate_email_content():
    """Test email content generation"""
    result = generate_email_content(...)
    assert "subject" in result
    assert "body" in result

def test_company_insights():
    """Test company insight generation"""
    result = get_company_insights(...)
    assert result is not None
```

### Integration Tests
```python
async def test_full_campaign_generation():
    """Test end-to-end campaign generation"""
    campaign = await generate_campaign(...)
    assert campaign["name"]
    assert campaign["content"]
``` 