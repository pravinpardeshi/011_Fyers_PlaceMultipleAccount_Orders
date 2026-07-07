import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Account, Order
from schemas import PlaceOrderRequest, PlaceOrderResponse, OrderResult, OrderHistoryItem
from fyers_client import place_single_order

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("/place", response_model=PlaceOrderResponse)
async def place_order(payload: PlaceOrderRequest, db: AsyncSession = Depends(get_db)):
    query = select(Account).where(Account.is_active == True, Account.access_token.isnot(None))
    if payload.account_ids:
        query = query.where(Account.id.in_(payload.account_ids))
    result = await db.execute(query)
    accounts = result.scalars().all()

    if not accounts:
        raise HTTPException(status_code=400, detail="No active accounts with valid tokens. Generate tokens first.")

    batch_id = uuid.uuid4()

    order_data = {
        "symbol": payload.symbol,
        "qty": payload.qty,
        "type": payload.order_type,
        "side": payload.side,
        "productType": payload.product_type,
        "limitPrice": payload.limit_price,
        "stopPrice": payload.stop_price,
        "validity": payload.validity,
        "disclosedQty": payload.disclosed_qty,
        "offlineOrder": False,
        "stopLoss": 0,
        "takeProfit": 0,
    }

    loop = asyncio.get_running_loop()
    order_results = []

    def _place_order(acc):
        resp = place_single_order(acc, order_data)
        return acc, resp

    with ThreadPoolExecutor(max_workers=len(accounts)) as pool:
        tasks = [loop.run_in_executor(pool, _place_order, acc) for acc in accounts]
        completed = await asyncio.gather(*tasks)

    for acc, resp in completed:
        status = "SUCCESS" if resp.get("s") == "ok" else "FAILED"

        order = Order(
            batch_id=batch_id,
            account_id=acc.id,
            symbol=payload.symbol,
            qty=payload.qty,
            order_type=payload.order_type,
            side=payload.side,
            product_type=payload.product_type,
            limit_price=payload.limit_price,
            stop_price=payload.stop_price,
            validity=payload.validity,
            disclosed_qty=payload.disclosed_qty,
            status=status,
            response=resp,
        )
        db.add(order)

        order_results.append(OrderResult(
            account_id=acc.id,
            account_name=acc.name,
            status=status,
            response=resp,
        ))

    await db.commit()

    return PlaceOrderResponse(batch_id=batch_id, results=order_results)


@router.get("/history", response_model=list[OrderHistoryItem])
async def order_history(
    batch_id: uuid.UUID | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    query = select(Order, Account.name.label("account_name")).join(Account, Order.account_id == Account.id)

    if batch_id:
        query = query.where(Order.batch_id == batch_id)

    query = query.order_by(desc(Order.created_at)).limit(limit)
    result = await db.execute(query)

    items = []
    for order, account_name in result:
        items.append(OrderHistoryItem(
            id=order.id,
            batch_id=order.batch_id,
            account_name=account_name,
            symbol=order.symbol,
            qty=order.qty,
            order_type=order.order_type,
            side=order.side,
            product_type=order.product_type,
            limit_price=order.limit_price,
            stop_price=order.stop_price,
            status=order.status,
            response=order.response,
            created_at=order.created_at,
        ))

    return items
