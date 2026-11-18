from sqlalchemy.orm import Session
from sqlalchemy import func

from app.payments.models import RazorpayPaymentOrder, RazorpayWebhookLog


def create_payment_order(
    db: Session,
    *,
    user_id: int,
    property_id: int,
    amount_inr: float,
    amount_paise: int,
    currency: str,
    order_id: str,
    payment_context: str = "buyer",
    site_visit_request_id: int | None = None,
    commit: bool = True,
) -> RazorpayPaymentOrder:
    entity = RazorpayPaymentOrder(
        user_id=user_id,
        property_id=property_id,
        amount=amount_inr,
        amount_paise=amount_paise,
        currency=currency,
        payment_context=payment_context,
        site_visit_request_id=site_visit_request_id,
        order_id=order_id,
        status="CREATED",
    )
    db.add(entity)
    if commit:
        db.commit()
        db.refresh(entity)
    else:
        db.flush()
    return entity


def get_payment_order_by_order_id(
    db: Session,
    order_id: str,
    for_update: bool = False,
) -> RazorpayPaymentOrder | None:
    query = db.query(RazorpayPaymentOrder).filter(RazorpayPaymentOrder.order_id == order_id)
    if for_update:
        query = query.with_for_update()
    return query.first()


def mark_payment_success(
    db: Session,
    order: RazorpayPaymentOrder,
    *,
    payment_id: str,
    signature: str,
    commit: bool = True,
) -> RazorpayPaymentOrder:
    order.payment_id = payment_id
    order.signature = signature
    order.status = "SUCCESS"
    order.paid_at = func.now()
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(order)
    return order


def mark_payment_failed(
    db: Session,
    order: RazorpayPaymentOrder,
    *,
    payment_id: str | None,
    commit: bool = True,
) -> RazorpayPaymentOrder:
    if payment_id:
        order.payment_id = payment_id
    order.status = "FAILED"
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(order)
    return order


def create_webhook_log(
    db: Session,
    *,
    event_id: str | None,
    event: str,
    order_id: str | None,
    payment_id: str | None,
    signature: str | None,
    payload: str,
    status: str,
    payment_context: str = "unknown",
    error: str | None = None,
    event_key: str | None = None,
    commit: bool = True,
) -> RazorpayWebhookLog:
    entity = RazorpayWebhookLog(
        event_id=event_id,
        event_key=event_id if event_key is None else event_key,
        event=event,
        order_id=order_id,
        payment_id=payment_id,
        signature=signature,
        payload=payload,
        status=status,
        payment_context=payment_context,
        error=error,
        attempt_count=1,
    )
    db.add(entity)
    if commit:
        db.commit()
        db.refresh(entity)
    else:
        db.flush()
    return entity


def get_webhook_log_by_event_id(
    db: Session, event_id: str, *, for_update: bool = False
) -> RazorpayWebhookLog | None:
    query = db.query(RazorpayWebhookLog).filter(RazorpayWebhookLog.event_key == event_id)
    if for_update:
        query = query.with_for_update()
    return query.first()


def update_webhook_log_attempt(
    db: Session,
    log: RazorpayWebhookLog,
    *,
    status: str,
    payment_context: str | None = None,
    error: str | None = None,
    payload: str | None = None,
    order_id: str | None = None,
    payment_id: str | None = None,
    signature: str | None = None,
    commit: bool = True,
) -> RazorpayWebhookLog:
    log.attempt_count = (log.attempt_count or 0) + 1
    log.status = status
    if payment_context is not None:
        log.payment_context = payment_context
    log.error = error
    if payload is not None:
        log.payload = payload
    if order_id is not None:
        log.order_id = order_id
    if payment_id is not None:
        log.payment_id = payment_id
    if signature is not None:
        log.signature = signature
    if commit:
        db.commit()
        db.refresh(log)
    else:
        db.flush()
    return log


def get_payment_order_detail(db: Session, order_id: str) -> RazorpayPaymentOrder | None:
    return db.query(RazorpayPaymentOrder).filter(RazorpayPaymentOrder.order_id == order_id).first()


def list_payment_orders(
    db: Session,
    *,
    user_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[int, list[RazorpayPaymentOrder]]:
    query = db.query(RazorpayPaymentOrder)
    if user_id is not None:
        query = query.filter(RazorpayPaymentOrder.user_id == user_id)
    total = query.count()
    items = query.order_by(RazorpayPaymentOrder.created_at.desc()).offset(skip).limit(limit).all()
    return total, items


def list_webhook_logs(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    payment_context: str | None = None,
    status: str | None = None,
    event: str | None = None,
    order_id: str | None = None,
    payment_id: str | None = None,
) -> tuple[int, list[RazorpayWebhookLog]]:
    query = db.query(RazorpayWebhookLog)
    if payment_context:
        query = query.filter(RazorpayWebhookLog.payment_context == payment_context)
    if status:
        query = query.filter(RazorpayWebhookLog.status == status)
    if event:
        query = query.filter(RazorpayWebhookLog.event == event)
    if order_id:
        query = query.filter(RazorpayWebhookLog.order_id == order_id)
    if payment_id:
        query = query.filter(RazorpayWebhookLog.payment_id == payment_id)
    total = query.count()
    items = query.order_by(RazorpayWebhookLog.created_at.desc()).offset(skip).limit(limit).all()
    return total, items
