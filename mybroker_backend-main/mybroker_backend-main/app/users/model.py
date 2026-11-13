from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, func

from app.database import Base
from app.users.roles import UserRole


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    fullname = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=True)
    mobile = Column(String(15), unique=True)
    profile_image_url = Column(String(255), nullable=True)
    fcm_token = Column(String(512), nullable=True)
    address = Column(String(255), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)
    password_hash = Column(String(255))
    role = Column(String(30), nullable=False, default=UserRole.CUSTOMER.value, server_default=UserRole.CUSTOMER.value)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
