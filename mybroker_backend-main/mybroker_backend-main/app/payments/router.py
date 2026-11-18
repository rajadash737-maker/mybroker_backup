import hmac
import json
import logging
import os
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_active_user, get_current_user, get_db, require_roles
from app.payments.schemas import (
    CreateOrderRequest,
    CreateOrderResponse,
    PaymentItemResponse,
    PaymentListResponse,
    WebhookLogListResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from app.payments.service import (
    create_order,
    get_payment_detail,
    handle_webhook_event,
    list_payments,
    list_webhook_logs_service,
    verify_payment,
)
from app.users.model import User
from app.users.roles import UserRole

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Payments"])


@router.post("/create-order", response_model=CreateOrderResponse, status_code=status.HTTP_201_CREATED)
def create_payment_order(
    payload: CreateOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    response, error = create_order(db, payload, user_id=current_user.id)
    if error == "User not found" or error == "Property not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        if error == "User mismatch":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error)
        logger.warning("create-order failed: %s", error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/verify-payment", response_model=VerifyPaymentResponse)
def verify_payment_order(
    payload: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    response, error = verify_payment(db, payload, user_id=current_user.id)
    if error == "Order not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        if error == "Not authorized":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error)
        logger.warning("verify-payment failed: %s", error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/razorpay-webhook")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not secret:
        logger.error("RAZORPAY_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Webhook not configured")

    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    if not signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signature")

    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload")
    event = payload.get("event", "")
    # Razorpay identifies a webhook delivery with this header; payload-level
    # id fields are entity IDs and are not reliable event deduplication keys.
    event_id = request.headers.get("x-razorpay-event-id")
    if not event_id or len(event_id) > 80:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing or invalid event ID")
    payment_block = (payload.get("payload") or {}).get("payment", {})
    payment_entity = payment_block.get("entity", {}) if isinstance(payment_block, dict) else {}
    if not isinstance(payment_entity, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payment entity")
    order_id = payment_entity.get("order_id")
    payment_id = payment_entity.get("id")
    payment_status = payment_entity.get("status")

    ok, error = handle_webhook_event(
        db,
        event=event,
        event_id=event_id,
        payload_json=json.dumps(payload),
        signature=signature,
        order_id=order_id,
        payment_id=payment_id,
        payment_status=payment_status,
        amount_paise=payment_entity.get("amount"),
        currency=payment_entity.get("currency"),
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error or "Webhook processing failed")
    return {"status": "ok"}


@router.get("/payments/me", response_model=PaymentListResponse)
def get_my_payments(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total, items = list_payments(db, user_id=current_user.id, skip=skip, limit=limit)
    return {"total": total, "items": items}


@router.get("/payments/admin", response_model=PaymentListResponse)
def get_all_payments(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.ACCOUNTING)),
):
    total, items = list_payments(db, user_id=None, skip=skip, limit=limit)
    return {"total": total, "items": items}


@router.get("/payments/webhook-logs", response_model=WebhookLogListResponse)
def get_webhook_logs(
    skip: int = 0,
    limit: int = 50,
    payment_context: str | None = None,
    status: str | None = None,
    event: str | None = None,
    order_id: str | None = None,
    payment_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.ACCOUNTING)),
):
    total, items = list_webhook_logs_service(
        db,
        skip=skip,
        limit=limit,
        payment_context=payment_context,
        status=status,
        event=event,
        order_id=order_id,
        payment_id=payment_id,
    )
    return {"total": total, "items": items}


@router.get("/payments/{order_id}", response_model=PaymentItemResponse)
def get_payment_by_order_id(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_payment_detail(db, order_id=order_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    is_admin = current_user.role in {
        UserRole.ADMIN.value,
        UserRole.SUPER_ADMIN.value,
        UserRole.ACCOUNTING.value,
    }
    if not is_admin and item["user_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return item
