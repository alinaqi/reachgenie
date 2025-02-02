# Development Guide

## Development Environment Setup

### IDE Configuration
Recommended VS Code extensions:
- Python
- Pylance
- Black Formatter
- isort
- Docker
- PostgreSQL

### Code Style
We follow PEP 8 with some modifications:
```python
# Maximum line length
max_line_length = 100

# Import order
from std_lib import something
from third_party import another
from src.local_module import function
```

### Pre-commit Hooks
Install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

## Project Structure

### Core Components
```
src/
├── main.py              # FastAPI application and routes
├── database.py          # Database operations
├── auth.py             # Authentication logic
├── config.py           # Configuration management
├── bland_client.py     # Bland AI integration
├── services/           # Business logic services
│   ├── email_service.py
│   ├── bland_calls.py
│   └── perplexity_service.py
├── utils/             # Utility functions
│   ├── encryption.py
│   ├── calendar_utils.py
│   └── smtp_client.py
└── models/            # Pydantic models
    └── __init__.py
```

### Services
```
src/services/
├── bland_calls.py       # Call automation
├── email_service.py     # Email handling
└── perplexity_service.py  # Company research
```

### Utils
```
src/utils/
├── calendar_utils.py    # Calendar integration
├── encryption.py        # Data encryption
├── file_parser.py       # File handling
├── llm.py              # AI utilities
└── smtp_client.py       # Email client
```

### Templates & Prompts
```
src/
├── templates/
│   └── email_templates.py  # Email templates
└── prompts/
    ├── company_info_prompt.py
    └── company_insights_prompt.py
```

## Development Workflow

### 1. Feature Development
1. Create feature branch:
   ```bash
   git checkout -b feat/feature-name
   ```

2. Implement changes following our standards:
   - Type hints everywhere
   - Docstrings for functions
   - Unit tests for new features
   - Update documentation

3. Test locally:
   ```bash
   # Run tests
   pytest

   # Run linting
   flake8
   ```

### 2. API Development

#### Route Structure
```python
@router.get("/{id}", response_model=ResponseModel)
async def endpoint(
    id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Endpoint description.
    
    Args:
        id: Resource ID
        db: Database session
        
    Returns:
        Resource details
        
    Raises:
        HTTPException: If resource not found
    """
    try:
        result = await get_resource(db, id)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### Testing Endpoints
```python
def test_endpoint():
    # Arrange
    test_data = {"key": "value"}
    
    # Act
    response = client.get("/endpoint")
    
    # Assert
    assert response.status_code == 200
    assert response.json() == test_data
```

### 3. AI Integration Development

#### OpenAI Integration
```python
async def generate_content(prompt: str) -> str:
    """Generate content using OpenAI."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
```

#### Bland AI Integration

1. **Tool Registration**
```python
async def register_tool() -> dict:
    """Register a new tool with Bland AI."""
    client = BlandClient(
        api_key=settings.bland_api_key,
        webhook_base_url=settings.webhook_base_url
    )
    return await client.create_book_appointment_tool()
```

2. **Call Initiation**
```python
async def start_call(
    phone_number: str,
    script: str,
    tool_id: str
) -> dict:
    """Start an automated call."""
    client = BlandClient(
        api_key=settings.bland_api_key,
        bland_tool_id=tool_id
    )
    return await client.start_call(phone_number, script)
```

3. **Webhook Handling**
```python
@app.post("/api/calls/webhook")
async def handle_webhook(
    payload: WebhookPayload,
    token: str = Depends(verify_token)
):
    """Handle Bland AI webhooks."""
    return await process_webhook(payload)
```

### 4. Database Development

#### Migrations
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Run migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

#### Models
```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## Testing

### 1. Unit Tests
```python
def test_function():
    # Arrange
    input_data = "test"
    expected = "result"
    
    # Act
    result = function(input_data)
    
    # Assert
    assert result == expected
```

### 2. Integration Tests
```python
async def test_database_operation():
    # Arrange
    async with AsyncSession(engine) as session:
        # Act
        result = await create_resource(session, data)
        
        # Assert
        assert result.id is not None
```

### 3. API Tests
```python
def test_api_endpoint():
    response = client.post(
        "/api/resource",
        json={"data": "test"}
    )
    assert response.status_code == 200
```

## Deployment

### 1. Environment Preparation
```bash
# Production environment variables
cp .env.example .env.prod
# Edit .env.prod with production values
```

### 2. Database Setup
```bash
# Run migrations
alembic upgrade head
```

### 3. Application Deployment
```bash
# Start application
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## Monitoring & Debugging

### 1. Logging
```python
logger = logging.getLogger(__name__)

try:
    result = operation()
    logger.info(f"Operation successful: {result}")
except Exception as e:
    logger.error(f"Operation failed: {str(e)}")
```

### 2. Performance Monitoring
- Use FastAPI's built-in performance middleware
- Monitor database query performance
- Track API response times

### 3. Error Handling
```python
try:
    result = await operation()
except OperationalError as e:
    logger.error(f"Database error: {str(e)}")
    raise HTTPException(status_code=500, detail="Database error")
except ValidationError as e:
    logger.error(f"Validation error: {str(e)}")
    raise HTTPException(status_code=400, detail=str(e))
```

## Security Best Practices

### 1. Authentication
- Use JWT tokens
- Implement refresh tokens
- Rate limiting

### 2. Data Protection
- Encrypt sensitive data
- Use HTTPS
- Input validation

### 3. API Security
- Input validation
- Rate limiting
- CORS configuration

## Documentation

### 1. Code Documentation
```python
def function(param: str) -> dict:
    """
    Function description.
    
    Args:
        param: Parameter description
        
    Returns:
        Description of return value
        
    Raises:
        Exception: Description of when this error occurs
    """
```

### 2. API Documentation
- Keep Swagger/ReDoc documentation updated
- Document all endpoints
- Include example requests/responses

### 3. README Updates
- Document new features
- Update installation steps
- Keep troubleshooting guide current

## Contribution Guidelines

### 1. Code Review Process
- Create feature branch
- Write tests
- Update documentation
- Create pull request
- Address review comments

### 2. Commit Messages
Follow conventional commits:
```
feat: add new feature
fix: bug fix
docs: update documentation
test: add tests
refactor: code refactoring
```

### 3. Pull Request Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added
- [ ] Integration tests added
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Migrations added if needed
``` 