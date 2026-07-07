import asyncio
import logging
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session
from models import Account
from fyers_client import generate_access_token

logger = logging.getLogger(__name__)

CHECK_INTERVAL_MINUTES = 30
REFRESH_BEFORE_EXPIRY_HOURS = 1


async def check_and_refresh_tokens():
    """Check token expiry and refresh if expiring soon."""
    async with async_session() as db:
        result = await db.execute(
            select(Account).where(Account.is_active == True)
        )
        accounts = result.scalars().all()

    now = datetime.now(timezone.utc)
    accounts_needing_refresh = []

    for acc in accounts:
        needs_refresh = False
        if not acc.access_token:
            needs_refresh = True
            reason = "no token"
        elif acc.token_expiry:
            expiry = acc.token_expiry
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry <= now + timedelta(hours=REFRESH_BEFORE_EXPIRY_HOURS):
                needs_refresh = True
                reason = f"expiring at {expiry.isoformat()}"
        else:
            needs_refresh = True
            reason = "no expiry set"

        if needs_refresh:
            accounts_needing_refresh.append((acc, reason))

    if not accounts_needing_refresh:
        logger.debug("[Scheduler] All tokens valid, no refresh needed")
        return []

    logger.info("[Scheduler] %d accounts need token refresh", len(accounts_needing_refresh))
    for acc, reason in accounts_needing_refresh:
        logger.info("[Scheduler]   - %s: %s", acc.name, reason)

    loop = asyncio.get_running_loop()
    results = []

    def _gen(acc):
        return acc.id, acc.name, generate_access_token(acc)

    with ThreadPoolExecutor(max_workers=len(accounts_needing_refresh)) as pool:
        tasks = [loop.run_in_executor(pool, _gen, acc) for acc, _ in accounts_needing_refresh]
        completed = await asyncio.gather(*tasks)

    async with async_session() as db:
        for account_id, account_name, token_result in completed:
            if token_result["success"]:
                try:
                    account = await db.get(Account, account_id)
                    if account:
                        account.access_token = token_result["access_token"]
                        account.token_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
                        await db.commit()
                        logger.info("[Scheduler] Token refreshed for %s", account_name)
                    results.append({"account": account_name, "success": True})
                except Exception as e:
                    logger.exception("[Scheduler] Failed to save token for %s", account_name)
                    await db.rollback()
                    results.append({"account": account_name, "success": False, "error": str(e)})
            else:
                logger.warning("[Scheduler] Token refresh failed for %s: %s", account_name, token_result["error"])
                results.append({"account": account_name, "success": False, "error": token_result["error"]})

    return results


async def scheduler_loop():
    """Background loop that checks and refreshes tokens periodically."""
    logger.info("[Scheduler] Starting token scheduler (check every %d min, refresh %dh before expiry)",
                CHECK_INTERVAL_MINUTES, REFRESH_BEFORE_EXPIRY_HOURS)

    # Initial refresh on startup
    await asyncio.sleep(2)
    logger.info("[Scheduler] Running initial token refresh on startup...")
    await check_and_refresh_tokens()

    while True:
        await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)
        try:
            await check_and_refresh_tokens()
        except Exception as e:
            logger.exception("[Scheduler] Error in scheduler loop: %s", e)


async def get_scheduler_status():
    """Get current token status for all accounts."""
    async with async_session() as db:
        result = await db.execute(
            select(Account).where(Account.is_active == True).order_by(Account.name)
        )
        accounts = result.scalars().all()

    now = datetime.now(timezone.utc)
    statuses = []

    for acc in accounts:
        has_token = acc.access_token is not None
        is_valid = False
        expiry = None
        if has_token and acc.token_expiry:
            expiry = acc.token_expiry
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            is_valid = expiry > now

        statuses.append({
            "account_id": str(acc.id),
            "account_name": acc.name,
            "has_token": has_token,
            "token_expiry": acc.token_expiry.isoformat() if acc.token_expiry else None,
            "is_valid": is_valid,
            "needs_refresh": has_token and expiry and expiry <= now + timedelta(hours=REFRESH_BEFORE_EXPIRY_HOURS),
        })

    return {
        "check_interval_minutes": CHECK_INTERVAL_MINUTES,
        "refresh_before_expiry_hours": REFRESH_BEFORE_EXPIRY_HOURS,
        "accounts": statuses,
    }
