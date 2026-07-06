import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Account
from schemas import TokenGenerateRequest, TokenStatus
from fyers_client import generate_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tokens", tags=["tokens"])


@router.post("/generate")
async def generate_tokens(payload: TokenGenerateRequest, db: AsyncSession = Depends(get_db)):
    if payload.account_ids:
        result = await db.execute(select(Account).where(Account.id.in_(payload.account_ids), Account.is_active == True))
    else:
        result = await db.execute(select(Account).where(Account.is_active == True))

    accounts = result.scalars().all()
    if not accounts:
        return {"message": "No active accounts found", "results": []}

    loop = asyncio.get_event_loop()
    results = []

    def _gen_token(acc):
        return acc.id, acc.name, generate_access_token(acc)

    with ThreadPoolExecutor(max_workers=len(accounts)) as pool:
        tasks = [loop.run_in_executor(pool, _gen_token, acc) for acc in accounts]
        completed = await asyncio.gather(*tasks)

    for account_id, account_name, token_result in completed:
        results.append({
            "account_id": str(account_id),
            "account_name": account_name,
            "success": token_result["success"],
            "error": token_result["error"],
        })

        if token_result["success"]:
            try:
                await db.execute(
                    update(Account)
                    .where(Account.id == account_id)
                    .values(
                        access_token=token_result["access_token"],
                        token_expiry=datetime.now(timezone.utc) + timedelta(hours=24),
                    )
                )
                await db.commit()
                logger.info("Token saved for %s", account_name)
            except Exception as e:
                logger.exception("Failed to save token for %s", account_name)
                await db.rollback()
        else:
            logger.warning("Token generation failed for %s: %s", account_name, token_result["error"])

    return {"message": f"Processed {len(results)} accounts", "results": results}


@router.get("/status", response_model=list[TokenStatus])
async def token_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).order_by(Account.name))
    accounts = result.scalars().all()

    statuses = []
    for acc in accounts:
        has_token = acc.access_token is not None
        is_valid = False
        if has_token and acc.token_expiry:
            expiry = acc.token_expiry
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            is_valid = expiry > datetime.now(timezone.utc)

        statuses.append(TokenStatus(
            account_id=acc.id,
            account_name=acc.name,
            has_token=has_token,
            token_expiry=acc.token_expiry,
            is_valid=is_valid,
        ))

    return statuses
