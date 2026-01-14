#!/usr/bin/env python3
"""
Script to add default availability for the test user
"""
import sys
import os
from datetime import time

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.models import Availability, User


def add_availability():
    """Add default availability for test user (Monday-Friday, 9 AM - 5 PM)"""
    db = SessionLocal()
    try:
        # Get test user
        user = db.query(User).filter(User.username == "testuser").first()
        if not user:
            print("❌ Test user not found!")
            return
        
        print(f"✅ Found user: {user.username} (ID: {user.id})")
        
        # Delete existing availability
        db.query(Availability).filter(Availability.user_id == user.id).delete()
        
        # Add availability for Monday-Friday (0-4), 9 AM - 5 PM
        days = {
            0: "Monday",
            1: "Tuesday", 
            2: "Wednesday",
            3: "Thursday",
            4: "Friday"
        }
        
        for day_num, day_name in days.items():
            availability = Availability(
                user_id=user.id,
                day_of_week=day_num,
                start_time=time(9, 0),  # 9:00 AM
                end_time=time(17, 0)    # 5:00 PM
            )
            db.add(availability)
            print(f"✅ Added availability for {day_name}: 9:00 AM - 5:00 PM")
        
        db.commit()
        print("\n✅ Availability configured successfully!")
        print("You can now book appointments Monday-Friday between 9:00 AM and 5:00 PM")
        
    except Exception as e:
        print(f"❌ Error adding availability: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    add_availability()
