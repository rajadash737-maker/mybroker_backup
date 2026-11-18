from sqlalchemy import Column, DateTime, Integer, String, Boolean, Float, Numeric, func

from app.database import Base


class SocialLinks(Base):
    __tablename__ = "social_links"

    id = Column(Integer, primary_key=True)
    whatsapp = Column(String(255), nullable=True)
    instagram = Column(String(255), nullable=True)
    telegram = Column(String(255), nullable=True)
    youtube = Column(String(255), nullable=True)
    facebook = Column(String(255), nullable=True)
    linkedin = Column(String(255), nullable=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class Banner(Base):
    __tablename__ = "banners"

    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String(255), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class ProcessingFeeSettings(Base):
    __tablename__ = "processing_fee_settings"

    id = Column(Integer, primary_key=True, index=True)
    seller_processing_fee = Column(Float, nullable=False, default=999.0, server_default="999.0")
    buyer_processing_fee = Column(Float, nullable=False, default=1000.0, server_default="1000.0")
    site_visit_fee = Column(Numeric(10, 2), nullable=False, default=0, server_default="0.00")
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
