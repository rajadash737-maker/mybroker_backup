from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.sell_land.dependencies import get_current_user, get_db
from app.transactions.schemas import TransactionItemResponse, TransactionsResponse
from fastapi import HTTPException, status
from app.transactions.service import get_transaction_detail, list_my_transactions
from app.users.model import User

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("/me", response_model=TransactionsResponse)
def get_my_transactions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_my_transactions(db=db, user_id=current_user.id, skip=skip, limit=limit)


@router.get("/{transaction_id}", response_model=TransactionItemResponse)
def get_transaction_by_id(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_transaction_detail(db=db, user_id=current_user.id, transaction_id=transaction_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return item
