from sqlalchemy import Column, String, DateTime, Integer, Time, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from app.core.database import Base
import uuid
from datetime import datetime, timedelta
from typing import Optional


class UUID(TypeDecorator):
    """Platform-independent UUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresUUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    appointments = relationship("Appointment", back_populates="user", cascade="all, delete-orphan")
    availability = relationship("Availability", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    customer_name = Column(String(255), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    calcom_booking_id = Column(String(255), nullable=True)  # Optional Cal.com booking ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="appointments")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('duration_minutes > 0', name='positive_duration'),
        Index('idx_appointments_start_time', 'start_time'),
        Index('idx_appointments_user_start', 'user_id', 'start_time'),
    )
    
    @property
    def end_time(self) -> datetime:
        """Calculate the end time of the appointment"""
        return self.start_time + timedelta(minutes=self.duration_minutes)
    
    def overlaps_with(self, other_start: datetime, other_duration: int) -> bool:
        """Check if this appointment overlaps with another time slot"""
        other_end = other_start + timedelta(minutes=other_duration)
        return (self.start_time < other_end) and (self.end_time > other_start)
    
    def __repr__(self) -> str:
        return f"<Appointment(id={self.id}, customer='{self.customer_name}', start={self.start_time})>"


class Availability(Base):
    __tablename__ = "availability"
    
    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="availability")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('day_of_week >= 0 AND day_of_week <= 6', name='valid_day_of_week'),
        CheckConstraint('start_time < end_time', name='valid_time_range'),
        Index('idx_availability_user_day', 'user_id', 'day_of_week'),
    )
    
    def __repr__(self) -> str:
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_name = days[self.day_of_week] if 0 <= self.day_of_week <= 6 else 'Unknown'
        return f"<Availability(id={self.id}, day={day_name}, time={self.start_time}-{self.end_time})>"