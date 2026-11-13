from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("from_user_id", "property_id", "role", name="uq_ratings_from_property_role"),
    )

    id = Column(Integer, primary_key=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(30), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    review = Column(Text, nullable=True)
    property_id = Column(Integer, ForeignKey("sell_land_requests.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
