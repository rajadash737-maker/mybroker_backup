from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func

from app.database import Base


class RazorpayPaymentOrder(Base):
    __tablename__ = "razorpay_payment_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("sell_land_requests.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    amount_paise = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    payment_context = Column(String(20), nullable=False, default="buyer", server_default="buyer")
    site_visit_request_id = Column(
        Integer,
        ForeignKey(
            "site_visit_requests.id",
            name="fk_payment_order_site_visit",
        ),
        nullable=True,
        index=True,
    )
    order_id = Column(String(64), nullable=False, unique=True, index=True)
    payment_id = Column(String(64), nullable=True)
    signature = Column(String(256), nullable=True)
    status = Column(String(20), nullable=False, default="CREATED")
    buyer_cancel_reported_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    paid_at = Column(DateTime, nullable=True)


class RazorpayWebhookLog(Base):
    __tablename__ = "razorpay_webhook_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(80), nullable=True, index=True)
    # Only provider-issued x-razorpay-event-id values are copied here. Older
    # rows leave this nullable so they remain intact during the unique-index
    # migration even if their legacy event_id values collide.
    event_key = Column(String(80), nullable=True, unique=True, index=True)
    event = Column(String(80), nullable=False)
    order_id = Column(String(64), nullable=True, index=True)
    payment_id = Column(String(64), nullable=True, index=True)
    signature = Column(String(256), nullable=True)
    status = Column(String(30), nullable=False, default="received")
    payment_context = Column(String(20), nullable=False, default="unknown")
    error = Column(String(255), nullable=True)
    payload = Column(Text, nullable=False)
    attempt_count = Column(Integer, nullable=False, default=1)
    last_attempt_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())
