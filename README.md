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
- Docker & Docker Compose for containerization

## Prerequisites

- Docker and Docker Compose installed on your system
  - [Install Docker](https://docs.docker.com/get-docker/)
  - [Install Docker Compose](https://docs.docker.com/compose/install/)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd api_sdr_ai
```

2. Copy the `.env.example` file to create your own `.env` file:
```bash
cp .env.example .env
```

3. Update the `.env` file with your actual credentials

4. Build and start the containers:
```bash
# Build and start in detached mode
docker compose up -d

# View logs
docker compose logs -f

# Stop the containers
docker compose down
```

The API will be available at `http://localhost:8000`

## Development

- Any changes made to the `src` directory will be automatically reflected in the running container due to volume mounting
- To rebuild the container after changing dependencies (requirements.txt):
```bash
docker compose build --no-cache
docker compose up -d
```

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

MIT 