from contextlib import asynccontextmanager
from pathlib import Path
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text

from database import init_db, async_session
from routers import accounts_router, tokens_router, orders_router
from token_scheduler import scheduler_loop, get_scheduler_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(scheduler_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="OrderForge - Multi-Account Trading Terminal",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts_router)
app.include_router(tokens_router)
app.include_router(orders_router)

STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(str(TEMPLATES_DIR / "index.html"))


@app.get("/health")
async def health_check():
    checks = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": app.version,
        "checks": {}
    }

    # Database check
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        checks["checks"]["database"] = {"status": "ok"}
    except Exception as e:
        checks["status"] = "unhealthy"
        checks["checks"]["database"] = {"status": "error", "detail": str(e)}

    # Scheduler check
    try:
        scheduler = await get_scheduler_status()
        accounts = scheduler.get("accounts", [])
        valid_tokens = sum(1 for a in accounts if a.get("is_valid"))
        checks["checks"]["scheduler"] = {
            "status": "ok",
            "check_interval_minutes": scheduler.get("check_interval_minutes"),
            "total_accounts": len(accounts),
            "valid_tokens": valid_tokens,
        }
    except Exception as e:
        checks["checks"]["scheduler"] = {"status": "error", "detail": str(e)}

    # Account check
    try:
        from sqlalchemy import select, func
        from models import Account
        async with async_session() as db:
            result = await db.execute(select(func.count(Account.id)))
            total = result.scalar()
            result = await db.execute(select(func.count(Account.id)).where(Account.is_active == True))
            active = result.scalar()
        checks["checks"]["accounts"] = {"status": "ok", "total": total, "active": active}
    except Exception as e:
        checks["checks"]["accounts"] = {"status": "error", "detail": str(e)}

    # Determine overall status
    for check in checks["checks"].values():
        if check.get("status") == "error":
            if checks["status"] == "healthy":
                checks["status"] = "degraded"
            break

    return checks
