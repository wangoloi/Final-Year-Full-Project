"""
Database Models - SQLAlchemy (no Flask).
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
import bcrypt

from api.database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(10), nullable=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    activity_level = Column(String(20), nullable=True)

    has_diabetes = Column(Boolean, default=False, nullable=False)
    diabetes_type = Column(String(20), nullable=True)
    diagnosis_date = Column(Date, nullable=True)
    current_medications = Column(Text, nullable=True)
    target_blood_glucose_min = Column(Float, nullable=True)
    target_blood_glucose_max = Column(Float, nullable=True)

    profile_completed = Column(Boolean, default=False, nullable=False)
    onboarding_completed = Column(Boolean, default=False, nullable=False)

    def set_password(self, password: str):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        try:
            return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
        except (ValueError, TypeError):
            # Invalid or legacy non-bcrypt hash — treat as failed login, do not 500 the API
            return False

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'age': self.age,
            'has_diabetes': self.has_diabetes,
            'diabetes_type': self.diabetes_type,
            'profile_completed': bool(self.profile_completed),
            # NULL = legacy row (before web onboarding); explicit False = new user must complete flow
            'onboarding_completed': True
            if self.onboarding_completed is None
            else bool(self.onboarding_completed),
        }


class FoodItem(Base):
    __tablename__ = 'food_items'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    local_name = Column(String(100), nullable=True)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)

    calories = Column(Float, nullable=False)
    protein = Column(Float, nullable=False)
    carbohydrates = Column(Float, nullable=False)
    fiber = Column(Float, nullable=False)
    fat = Column(Float, nullable=False)
    sugar = Column(Float, nullable=False)
    glycemic_index = Column(Integer, nullable=True)
    sodium = Column(Float, nullable=True)
    vitamin_c = Column(Float, nullable=True)
    iron = Column(Float, nullable=True)
    calcium = Column(Float, nullable=True)

    diabetes_friendly = Column(Boolean, default=False, nullable=False)
    serving_size = Column(String(80), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GlucoseReading(Base):
    __tablename__ = 'glucose_readings'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    reading_value = Column(Float, nullable=False)
    reading_type = Column(String(20), nullable=False)
    reading_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserFoodFeedback(Base):
    """Lightweight learning signal: like / skip on recommended foods."""

    __tablename__ = 'meal_recommendation_feedback'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    food_id = Column(Integer, ForeignKey('food_items.id'), nullable=False)
    action = Column(String(10), nullable=False)  # like | skip
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    chat_session_id = Column(Integer, ForeignKey('chat_sessions.id'), nullable=True)
    role = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    chat_session = relationship("ChatSession", back_populates="messages")


class ChatSession(Base):
    __tablename__ = 'chat_sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship(
        "ChatMessage",
        back_populates="chat_session",
        cascade="all, delete-orphan",
        order_by=ChatMessage.created_at,
    )
