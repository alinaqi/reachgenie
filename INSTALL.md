# ReachGenie Installation Guide

## Installation Methods

### Method 1: Install from PyPI (Recommended for Users)

Once published to PyPI, you can install ReachGenie with:

```bash
pip install reachgenie
```

### Method 2: Install from GitHub (Latest Development Version)

```bash
pip install git+https://github.com/alinaqi/reachgenie.git
```

### Method 3: Install from Source (For Development)

1. **Clone the repository:**
```bash
git clone https://github.com/alinaqi/reachgenie.git
cd reachgenie/backend
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install in development mode:**
```bash
pip install -e .
```

Or with development dependencies:
```bash
pip install -e ".[dev]"
```

## Quick Start

After installation, you can run ReachGenie in multiple ways:

### 1. Using the CLI Command

```bash
reachgenie
```

This will start the FastAPI server on `http://localhost:8000`

### 2. Using Uvicorn Directly

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Using Docker

```bash
docker compose up -d
```

## Configuration

1. **Copy the environment template:**
```bash
cp .env.example .env
```

2. **Edit `.env` with your credentials:**
- Database credentials (Supabase or PostgreSQL)
- API keys (OpenAI, Bland AI, Stripe, etc.)
- SMTP/IMAP settings
- Other service credentials

See [README.md](README.md#environment-variables) for complete environment variable documentation.

## Database Setup

1. **Run the schema:**
```bash
psql -U postgres -d your_database -f schema.sql
```

2. **Run migrations (if any):**
```bash
# Check migrations/ directory for SQL files
psql -U postgres -d your_database -f migrations/your_migration.sql
```

## Verify Installation

1. **Access the API documentation:**
   - Open `http://localhost:8000/docs` in your browser

2. **Check health endpoint:**
```bash
curl http://localhost:8000/
```

## Development Setup

For development with auto-reload:

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run with auto-reload
uvicorn src.main:app --reload

# Run tests
pytest

# Run with coverage
pytest --cov=src tests/

# Format code
black src/

# Lint code
flake8 src/
```

## Troubleshooting

### Import Errors
If you encounter import errors, ensure you're in the correct directory and the virtual environment is activated.

### Database Connection Issues
Check your database credentials in `.env` and ensure PostgreSQL is running.

### Missing Dependencies
Try reinstalling:
```bash
pip install --upgrade --force-reinstall -r requirements.txt
```

## Next Steps

- Read the [README.md](README.md) for detailed documentation
- Check the [API documentation](http://localhost:8000/docs) for endpoint reference
- Review the [docs/](docs/) directory for architecture and workflows

## Support

For issues or questions:
- GitHub Issues: https://github.com/alinaqi/reachgenie/issues
- Commercial licensing: ashaheen@workhub.ai
