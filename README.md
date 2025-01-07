# Outbound AI SDR API

A comprehensive sales enablement platform designed to help companies manage their outbound sales processes efficiently.

## Features

- User Authentication (signup, login, password reset)
- Company Management
- Product Management
- Lead Management with CSV upload
- Call Management with summaries and statistics

## Tech Stack

- FastAPI (Python web framework)
- Supabase (Database)
- JWT Authentication
- Pydantic for data validation

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd api_sdr_ai
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

For bcrypt system level dependency errors, you need to install/update by running the following command inside your virtual environment:

```bash
pip install --upgrade pip setuptools wheel
```

4. Copy the `.env.example` file to create your own `.env` file:
```bash
cp .env.example .env
```

5. Update the `.env` file with your actual credentials


6. To run the development server with auto-reload:
```bash
uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

MIT 