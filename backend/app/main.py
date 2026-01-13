from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import engine, close_db_connections, test_db_connection
from app.models import models
from app.api import auth
from app.api import appointments
from app.api import availability
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events"""
    # Startup
    logger.info("Starting up Appointment Scheduling System...")
    
    # Create database tables
    try:
        models.Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    
    # Test database connection
    if not test_db_connection():
        logger.error("Database connection test failed during startup")
        raise RuntimeError("Database connection failed")
    
    logger.info("Application startup completed successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Appointment Scheduling System...")
    
    # Close database connections
    close_db_connections()
    
    logger.info("Application shutdown completed successfully")


app = FastAPI(
    title="Appointment Scheduling System",
    description="A production-grade appointment scheduling system with Cal.com integration",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(appointments.router)
app.include_router(availability.router)

@app.get("/")
async def root():
    return {"message": "Appointment Scheduling System API"}

@app.get("/health")
async def health_check():
    """Health check endpoint that verifies database connectivity"""
    try:
        db_healthy = test_db_connection()
        if db_healthy:
            return {"status": "healthy", "database": "connected"}
        else:
            return {"status": "unhealthy", "database": "disconnected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}