import uuid
from datetime import datetime
from pydantic import BaseModel, Field


# --- Account Schemas ---
class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    fyers_username: str = Field(..., min_length=1, max_length=50)
    client_id: str = Field(..., min_length=1, max_length=50)
    secret_key: str = Field(..., min_length=1)
    totp_key: str = Field(..., min_length=1)
    pin: str = Field(..., min_length=4, max_length=10)
    redirect_uri: str = Field(default="https://trade.fyers.in/api-login/redirect-uri/index.html")


class AccountUpdate(BaseModel):
    name: str | None = None
    fyers_username: str | None = None
    client_id: str | None = None
    secret_key: str | None = None
    totp_key: str | None = None
    pin: str | None = None
    redirect_uri: str | None = None
    is_active: bool | None = None


class AccountResponse(BaseModel):
    id: uuid.UUID
    name: str
    fyers_username: str
    client_id: str
    is_active: bool
    has_token: bool
    token_expiry: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Token Schemas ---
class TokenGenerateRequest(BaseModel):
    account_ids: list[uuid.UUID] | None = None  # None = generate for all active accounts


class TokenStatus(BaseModel):
    account_id: uuid.UUID
    account_name: str
    has_token: bool
    token_expiry: datetime | None
    is_valid: bool


# --- Order Schemas ---
class PlaceOrderRequest(BaseModel):
    symbol: str = Field(..., description="e.g., NSE:SBIN-EQ")
    qty: int = Field(..., gt=0)
    order_type: int = Field(..., description="1=Limit, 2=Market")
    side: int = Field(..., description="1=Buy, -1=Sell")
    product_type: str = Field(..., description="INTRADAY, CNC, or MARGIN")
    limit_price: float = Field(default=0)
    stop_price: float = Field(default=0)
    validity: str = Field(default="DAY")
    disclosed_qty: int = Field(default=0)
    account_ids: list[uuid.UUID] | None = None  # None = all active accounts with tokens


class OrderResult(BaseModel):
    account_id: uuid.UUID
    account_name: str
    status: str
    response: dict | None = None


class PlaceOrderResponse(BaseModel):
    batch_id: uuid.UUID
    results: list[OrderResult]


class OrderHistoryItem(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID
    account_name: str
    symbol: str
    qty: int
    order_type: int
    side: int
    product_type: str
    limit_price: float
    stop_price: float
    status: str
    response: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
