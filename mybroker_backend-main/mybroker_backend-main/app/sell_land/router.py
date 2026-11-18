import logging
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile, status
from app.core.dependencies import require_roles
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.services.notification_service import NotificationService
from app.sell_land.constants import DocumentType, OwnershipType, PaymentMethod
from app.sell_land.dependencies import get_current_user, get_db
from app.core.dependencies import get_current_active_user
from app.sell_land.schemas import (
    BuyerExploreLandDetailResponse,
    BuyerExploreLandListResponse,
    BuyerExploreLikeResponse,
    BuyerOfferActionResponse,
    BuyerOfferCreateRequest,
    BuyerOfferCreateResponse,
    BuyerOfferListResponse,
    BuyerPropertyBookingRefundResponse,
    BuyerPropertyBookingRefundUpiRequest,
    IncomingOfferCountResponse,
    BuyerBookingCreateRequest,
    BuyerBookingCreateResponse,
    BuyerBookingPreviewResponse,
    BuyerBookingPaymentResponse,
    BuyerBookingPaymentRequest,
    ExploreSortType,
    SellerOfferActionResponse,
    SellerOfferCounterRequest,
    SellerOfferListResponse,
    SellLandCancelRequest,
    SellLandCancelResponse,
    SellLandBoundaryRequest,
    SellLandCreateRequest,
    SellLandDeleteResponse,
    SellLandDocumentRequirementsResponse,
    SellLandDraftUpsertRequest,
    SellLandMediaDeleteResponse,
    SellLandMediaUploadResponse,
    SellLandPaymentInitRequest,
    SellLandPaymentMarkPaidRequest,
    SellLandPaymentResponse,
    SellLandRazorpayOrderRequest,
    SellLandRazorpayOrderResponse,
    SellLandRazorpayVerifyRequest,
    SellLandRazorpayVerifyResponse,
    SellLandResponse,
    SellLandSubmitResponse,
    SellLandTrackingCardResponse,
    SellLandUpdateRequest,
)
from app.sell_land.service import (
    accept_counter_offer_for_buyer,
    accept_offer_for_my_listing,
    cancel_my_request,
    create_booking_for_buyer,
    reject_counter_offer_for_buyer,
    counter_offer_for_my_listing,
    create_request,
    get_buyer_land_detail_for_buyer,
    get_booking_preview_for_buyer,
    delete_my_media,
    delete_my_request,
    get_my_request,
    get_explore_land_detail,
    get_document_requirements,
    initiate_payment,
    like_explore_land,
    list_explore_lands,
    list_my_buyer_offers,
    get_my_incoming_offer_count,
    list_my_media,
    list_my_request_tracking,
    list_my_requests,
    mark_payment_paid,
    create_seller_razorpay_order,
    verify_seller_razorpay_payment,
    mark_booking_paid_for_buyer,
    make_offer_on_explore_land,
    list_my_listing_offers,
    reject_offer_for_my_listing,
    submit_my_request,
    update_my_boundary,
    update_my_request,
    upload_document,
    upload_photo,
    upsert_my_draft,
    unlike_explore_land,
)
from app.sell_land.property_booking_refunds import (
    get_buyer_booking_refund,
    submit_buyer_refund_upi,
)
from app.users.model import User
from app.users.roles import UserRole

router = APIRouter(prefix="/sell-land", tags=["Sell Land"])
logger = logging.getLogger(__name__)
customer_dependency = require_roles(UserRole.CUSTOMER)


@router.get("/document-requirements", response_model=list[SellLandDocumentRequirementsResponse])
def get_document_requirements_by_seller_type(
    ownership_type: OwnershipType | None = Query(default=None),
):
    return get_document_requirements(ownership_type)


@router.get("/explore", response_model=BuyerExploreLandListResponse)
def explore_live_lands(
    search: str | None = Query(default=None, min_length=1, max_length=120),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    min_area: float | None = Query(default=None, ge=0),
    max_area: float | None = Query(default=None, ge=0),
    sort: ExploreSortType = Query(default=ExploreSortType.LATEST),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_explore_lands(
        db=db,
        user_id=current_user.id,
        search=search,
        min_price=min_price,
        max_price=max_price,
        min_area=min_area,
        max_area=max_area,
        sort_by=sort,
        skip=skip,
        limit=limit,
    )


@router.post("/explore/{request_id}/like", response_model=BuyerExploreLikeResponse)
def like_land_for_buyer(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response, error = like_explore_land(db, current_user.id, request_id)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.get("/explore/{request_id}", response_model=BuyerExploreLandDetailResponse)
def get_explore_land_detail_for_buyer(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    entity = get_explore_land_detail(db, request_id)
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sell land request not found")
    return entity


@router.get("/buyer/land/{request_id}", response_model=BuyerExploreLandDetailResponse)
def get_buyer_land_detail(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response, error = get_buyer_land_detail_for_buyer(
        db=db,
        request_id=request_id,
        buyer_id=current_user.id,
    )
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "Not authorized":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/explore/{request_id}/offer", response_model=BuyerOfferCreateResponse, status_code=status.HTTP_201_CREATED)
def offer_land_for_buyer(
    request_id: int,
    payload: BuyerOfferCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response, error = make_offer_on_explore_land(
        db=db,
        user_id=current_user.id,
        request_id=request_id,
        payload=payload,
    )
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {"You cannot make an offer on your own listing", "Listing is temporarily locked for another buyer"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.get("/buyer/offers", response_model=BuyerOfferListResponse)
def get_my_buyer_offers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_my_buyer_offers(db=db, user_id=current_user.id)


@router.get("/buyer/bookings/{booking_id}/refund", response_model=BuyerPropertyBookingRefundResponse)
def buyer_property_booking_refund(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(customer_dependency),
):
    return get_buyer_booking_refund(db, booking_id=booking_id, buyer=current_user)


@router.post("/buyer/bookings/{booking_id}/refund/upi", response_model=BuyerPropertyBookingRefundResponse)
def submit_buyer_property_booking_refund_upi(
    booking_id: int,
    payload: BuyerPropertyBookingRefundUpiRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(customer_dependency),
):
    return submit_buyer_refund_upi(db, booking_id=booking_id, buyer=current_user, payload=payload)


@router.get("/offers/incoming-count", response_model=IncomingOfferCountResponse)
def get_incoming_offer_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(customer_dependency),
):
    return get_my_incoming_offer_count(db=db, user_id=current_user.id)


@router.get("/buyer/bookings/preview", response_model=BuyerBookingPreviewResponse)
def get_buyer_booking_preview(
    request_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response, error = get_booking_preview_for_buyer(db=db, user_id=current_user.id, request_id=request_id)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "Accepted offer not found":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/buyer/offers/{offer_id}/accept-counter", response_model=BuyerOfferActionResponse)
def accept_counter_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response, error = accept_counter_offer_for_buyer(db=db, user_id=current_user.id, offer_id=offer_id)
    if error in {"Offer not found", "Sell land request not found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {"Only counter offers can be accepted", "Listing is temporarily locked for another buyer"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/buyer/offers/{offer_id}/reject-counter", response_model=BuyerOfferActionResponse)
def reject_counter_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response, error = reject_counter_offer_for_buyer(db=db, user_id=current_user.id, offer_id=offer_id)
    if error == "Offer not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "Only counter offers can be rejected":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/buyer/bookings", response_model=BuyerBookingCreateResponse, status_code=status.HTTP_201_CREATED)
def create_buyer_booking(
    request_id: int = Form(...),
    buyer_name: str = Form(...),
    buyer_mobile: str = Form(...),
    aadhaar_doc: UploadFile = File(...),
    pan_doc: UploadFile = File(...),
    bank_doc: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        payload = BuyerBookingCreateRequest(
            request_id=request_id,
            buyer_name=buyer_name,
            buyer_mobile=buyer_mobile,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    booking, error = create_booking_for_buyer(
        db=db,
        user_id=current_user.id,
        payload=payload,
        aadhaar_doc=aadhaar_doc,
        pan_doc=pan_doc,
        bank_doc=bank_doc,
    )
    if error:
        logger.warning(
            "create_buyer_booking failed: user_id=%s request_id=%s error=%s",
            current_user.id,
            request_id,
            error,
        )
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {
        "Only live listings can be booked",
        "Listing is not locked for this buyer",
        "Accepted offer not found",
        "Booking already completed",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return BuyerBookingCreateResponse(
        status="Booking initiated",
        booking_id=booking.id,
        payment_status=booking.payment_status,
        deal_amount=booking.deal_amount,
        booking_fee_amount=booking.booking_fee_amount,
    )


@router.post("/buyer/bookings/{booking_id}/pay", response_model=BuyerBookingPaymentResponse)
def pay_buyer_booking(
    booking_id: int,
    payload: BuyerBookingPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking, error = mark_booking_paid_for_buyer(
        db=db,
        user_id=current_user.id,
        booking_id=booking_id,
        payload=payload,
    )
    if error == "Booking not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "Booking already paid":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return BuyerBookingPaymentResponse(
        status="Payment successful",
        booking_id=booking.id,
        payment_status=booking.payment_status,
        payment_method=(
            PaymentMethod(booking.payment_method)
            if booking.payment_method
            else None
        ),
        transaction_id=booking.payment_transaction_id,
        paid_at=booking.paid_at,
    )


@router.get("/{request_id}/offers", response_model=SellerOfferListResponse)
def get_listing_offers_for_seller(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response, error = list_my_listing_offers(db=db, user_id=current_user.id, request_id=request_id)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/{request_id}/offers/{offer_id}/accept", response_model=SellerOfferActionResponse)
def accept_listing_offer(
    request_id: int,
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response, error = accept_offer_for_my_listing(
        db=db,
        user_id=current_user.id,
        request_id=request_id,
        offer_id=offer_id,
    )
    if error in {"Sell land request not found", "Offer not found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {"Offer is already finalized", "Listing is already locked by an accepted offer"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/{request_id}/offers/{offer_id}/reject", response_model=SellerOfferActionResponse)
def reject_listing_offer(
    request_id: int,
    offer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response, error = reject_offer_for_my_listing(
        db=db,
        user_id=current_user.id,
        request_id=request_id,
        offer_id=offer_id,
    )
    if error in {"Sell land request not found", "Offer not found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "Offer is already finalized":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/{request_id}/offers/{offer_id}/counter", response_model=SellerOfferActionResponse)
def counter_listing_offer(
    request_id: int,
    offer_id: int,
    payload: SellerOfferCounterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response, error = counter_offer_for_my_listing(
        db=db,
        user_id=current_user.id,
        request_id=request_id,
        offer_id=offer_id,
        payload=payload,
    )
    if error in {"Sell land request not found", "Offer not found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error == "Offer is already finalized":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.delete("/explore/{request_id}/like", response_model=BuyerExploreLikeResponse)
def unlike_land_for_buyer(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response, error = unlike_explore_land(db, current_user.id, request_id)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/", response_model=SellLandResponse, status_code=status.HTTP_201_CREATED)
def create_sell_land(
    payload: SellLandCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_request(db, current_user.id, payload)


@router.post("/draft", response_model=SellLandResponse)
def save_sell_land_draft(
    payload: SellLandDraftUpsertRequest = Body(default_factory=SellLandDraftUpsertRequest),
    request_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entity, error = upsert_my_draft(db, current_user.id, payload, request_id=request_id)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return entity


@router.put("/{request_id}/boundary", response_model=SellLandResponse)
def update_boundary_points(
    request_id: int,
    payload: SellLandBoundaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entity, error = update_my_boundary(db, current_user.id, request_id, payload)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return entity


@router.post("/{request_id}/photos", response_model=SellLandMediaUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_land_photo(
    request_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    media, error = upload_photo(db, current_user.id, request_id, file)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return media


@router.post(
    "/{request_id}/documents",
    response_model=SellLandMediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_land_document(
    request_id: int,
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    media, error = upload_document(db, current_user.id, request_id, document_type, file)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return media


@router.get("/{request_id}/media", response_model=list[SellLandMediaUploadResponse])
def get_listing_media(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, error = list_my_media(db, current_user.id, request_id)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    return items


@router.delete(
    "/{request_id}/media/{media_id}",
    response_model=SellLandMediaDeleteResponse,
)
def delete_listing_media(
    request_id: int,
    media_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    error = delete_my_media(db, current_user.id, request_id, media_id)
    if error in {"Sell land request not found", "Media not found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return {"status": "Media deleted", "media_id": media_id}


@router.post(
    "/payments/initiate",
    response_model=SellLandPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def initiate_listing_payment(
    payload: SellLandPaymentInitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Legacy seller payment API disabled. Use /sell-land/payments/razorpay-order instead.",
    )


@router.post(
    "/payments/mark-paid",
    response_model=SellLandPaymentResponse,
    include_in_schema=False,
)
def mark_listing_payment_paid(
    payload: SellLandPaymentMarkPaidRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Legacy seller payment API disabled. Use /sell-land/payments/razorpay-verify instead.",
    )


@router.post("/payments/razorpay-order", response_model=SellLandRazorpayOrderResponse)
def create_seller_payment_order(
    payload: SellLandRazorpayOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    response, error = create_seller_razorpay_order(db, current_user.id, payload)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/payments/razorpay-verify", response_model=SellLandRazorpayVerifyResponse)
def verify_seller_payment(
    payload: SellLandRazorpayVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    response, error = verify_seller_razorpay_payment(db, current_user.id, payload)
    if error == "Payment not found" or error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response


@router.post("/{request_id}/submit", response_model=SellLandSubmitResponse)
def submit_sell_land_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entity, error = submit_my_request(db, current_user.id, request_id)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)

    try:
        NotificationService(db=db).notify_property_uploaded(entity.id)
    except Exception as exc:  # noqa: BLE001 - avoid blocking submit on notification failure
        logger.warning("FCM notification failed for listing %s: %s", entity.id, exc)

    return {"status": "Listing submitted", "request_id": entity.id, "listing_code": entity.listing_code}


@router.post("/{request_id}/cancel", response_model=SellLandCancelResponse)
def cancel_sell_land_request(
    request_id: int,
    payload: SellLandCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entity, error = cancel_my_request(db, current_user.id, request_id, payload)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error in {"Sold request cannot be cancelled", "Listing is already cancelled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return SellLandCancelResponse(
        status=(
            "Cancellation accepted. Sent to admin for refund review."
            if entity.cancellation_requires_admin_review
            else "Cancellation accepted. Sent directly to accounting for refund."
        ),
        request_id=entity.id,
        listing_status=entity.status,
        cancellation_reason=entity.cancellation_reason or payload.reason.value,
        refund_upi_id=entity.refund_upi_id or payload.upi_id,
        refund_due_at=entity.refund_due_at,
        cancellation_requires_admin_review=entity.cancellation_requires_admin_review,
    )


@router.get("/me", response_model=list[SellLandResponse])
def get_my_sell_land_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_my_requests(db, current_user.id)


@router.get("/me/tracking", response_model=list[SellLandTrackingCardResponse])
def get_my_sell_land_request_tracking(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_my_request_tracking(db, current_user.id)


@router.get("/{request_id}", response_model=SellLandResponse)
def get_my_sell_land_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entity = get_my_request(db, current_user.id, request_id)
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sell land request not found")
    return entity


@router.put("/{request_id}", response_model=SellLandResponse)
def update_my_sell_land_request(
    request_id: int,
    payload: SellLandUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entity, error = update_my_request(db, current_user.id, request_id, payload)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return entity


@router.delete("/{request_id}", response_model=SellLandDeleteResponse)
def delete_my_sell_land_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    error = delete_my_request(db, current_user.id, request_id)
    if error == "Sell land request not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return {"status": "Sell land request deleted"}
