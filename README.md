# Appointment Scheduling System

A production-grade appointment scheduling system that enables a user to manage availability and appointments through a calendar-driven interface.

## Architecture

- **Backend**: FastAPI (Python) with PostgreSQL database
- **Frontend**: React + Vite (TypeScript) with Cal.com Atoms
- **Database**: PostgreSQL (Neon)
- **External Integration**: Cal.com API for scheduling engine

## Project Structure

```
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── core/           # Core configuration and database
│   │   ├── models/         # SQLAlchemy models
│   │   ├── services/       # Business logic services
│   │   ├── api/            # API endpoints
│   │   └── main.py         # FastAPI application
│   ├── alembic/            # Database migrations
│   ├── tests/              # Backend tests
│   └── requirements.txt    # Python dependencies
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── hooks/          # Custom hooks
│   │   ├── services/       # API client
│   │   └── types/          # TypeScript types
│   └── package.json        # Node.js dependencies
└── README.md
```

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - Copy `.env` file and update with your actual values
   - The database URL is already configured for Neon PostgreSQL

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

The frontend will be available at http://localhost:3000 and will proxy API requests to the backend at http://localhost:8000.

## Development

### Running Tests

**Backend:**
```bash
cd backend
pytest
```

**Frontend:**
```bash
cd frontend
npm test
```

### Database Migrations

Create a new migration:
```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

## Features

- Single user authentication with JWT tokens
- Appointment booking with double booking prevention
- Appointment rescheduling with conflict validation
- Calendar-driven interface using Cal.com Atoms
- Real-time availability management
- Cal.com integration for scheduling engine
- Comprehensive property-based testing

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation.