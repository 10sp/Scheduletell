#!/usr/bin/env python3
"""
Simple test script to verify backend setup
"""
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.main import app
    from app.core.database import engine
    from app.models.models import User, Appointment, Availability
    from sqlalchemy import text
    
    print("✅ All imports successful!")
    
    # Test database connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Database connection successful!")
    
    print("✅ Backend setup complete!")
    print("\nTo start the backend server, run:")
    print("uvicorn app.main:app --reload --port 8000")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)