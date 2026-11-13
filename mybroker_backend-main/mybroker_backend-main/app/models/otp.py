from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from app.database import Base
from app.users.model import User


class Otp(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    mobile = Column(String(15), index=True)
    otp_code = Column(String(10))
    otp_hash = Column(String(64), nullable=True)
    purpose = Column(String(20), default="signup")
    verified = Column(Boolean, default=False)
    attempt_count = Column(Integer, nullable=False, default=0, server_default="0")
    consumed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    jti = Column(String(64), unique=True, index=True, nullable=False)
    token_hash = Column(String(128), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    replaced_by_jti = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_ip = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)

