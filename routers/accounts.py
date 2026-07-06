from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from database import get_db
from models import Account
from schemas import AccountCreate, AccountUpdate, AccountResponse

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


def account_to_response(account: Account) -> AccountResponse:
    return AccountResponse(
        id=account.id,
        name=account.name,
        fyers_username=account.fyers_username,
        client_id=account.client_id,
        redirect_uri=account.redirect_uri,
        is_active=account.is_active,
        has_token=account.access_token is not None,
        token_expiry=account.token_expiry,
        created_at=account.created_at,
    )


@router.get("", response_model=list[AccountResponse])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).order_by(Account.created_at))
    accounts = result.scalars().all()
    return [account_to_response(a) for a in accounts]


@router.post("", response_model=AccountResponse, status_code=201)
async def create_account(payload: AccountCreate, db: AsyncSession = Depends(get_db)):
    account = Account(**payload.model_dump())
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account_to_response(account)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account_to_response(account)


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(account_id: uuid.UUID, payload: AccountUpdate, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)

    await db.commit()
    await db.refresh(account)
    return account_to_response(account)


@router.delete("/{account_id}", status_code=204)
async def delete_account(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    await db.commit()
