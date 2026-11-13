from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean, UniqueConstraint, func

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    body = Column(String(500), nullable=False)
    type = Column(String(50), nullable=False, index=True)
    role_target = Column(String(50), nullable=True, index=True)
    reference_id = Column(String(50), nullable=True, index=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "reference_id", "type", name="uq_notification_user_reference_type"),
    )


class NotificationRead(Base):
    __tablename__ = "notification_reads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    property_id = Column(String(64), nullable=False, index=True)
    read_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "property_id", name="uq_notification_read_user_property"),
    )
