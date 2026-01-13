#!/usr/bin/env python3
"""
Script to create a test user for authentication testing
"""
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.core.auth import create_user, UserCreate, get_user_by_username


def create_test_user():
    """Create a test user if it doesn't exist"""
    db = SessionLocal()
    try:
        # Check if test user already exists
        existing_user = get_user_by_username(db, "testuser")
        if existing_user:
            print("✅ Test user already exists!")
            print(f"Username: testuser")
            print(f"Password: test123")
            return
        
        # Create test user
        user_data = UserCreate(username="testuser", password="test123")
        user = create_user(db, user_data)
        
        print("✅ Test user created successfully!")
        print(f"Username: {user.username}")
        print(f"Password: test123")
        print(f"User ID: {user.id}")
        
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_test_user()