# OrderForge

A multi-account Fyers trading terminal that places the same order across multiple Fyers brokerage accounts simultaneously, with fully automated TOTP-based 2FA token generation.

Built with **FastAPI**, **Fyers API V3**, **SQLAlchemy** (SQLite / PostgreSQL), and a vanilla **HTML/CSS/JS** frontend.

![Python](https://img.shields.io/badge/Python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)
![Fyers API](https://img.shields.io/badge/Fyers_API-V3-orange)

---

## Features

- **Multi-account order placement** — fire one order to 3+ accounts simultaneously via parallel threads
- **Automated 2FA / TOTP token generation** — no manual browser login needed each morning
- **Background token scheduler** — auto-refreshes tokens every 30 minutes before expiry
- **Derivatives support** — F&O orders with lot size validation
- **SQLite or PostgreSQL** — swap one line in `config.py` to switch
- **Light / Dark theme** — toggle from the status bar, persists in localStorage
- **Collapsible sidebar** — hover tooltips in collapsed state, persists in localStorage
- **Account selection checkboxes** — choose which accounts receive each order
- **Health check endpoint** — `/health` for monitoring DB, scheduler, and account status
- **Full order history** — every order tracked with batch grouping and API responses
- **Montserrat font** — clean, modern UI typography

---

## Project Structure

```
├── main.py                 # FastAPI app entry point, lifespan, /health endpoint
├── config.py               # All configuration (edit directly, no .env)
├── database.py             # SQLAlchemy async engine (SQLite + PostgreSQL)
├── models.py               # Account & Order database models (UUID PKs)
├── schemas.py              # Pydantic request / response schemas
├── fyers_client.py         # Fyers API V3 wrapper (TOTP auth + order placement)
├── token_scheduler.py      # Background token refresh scheduler
├── routers/
│   ├── __init__.py         # Router exports
│   ├── accounts.py         # Account CRUD endpoints
│   ├── tokens.py           # Token generation & scheduler endpoints
│   └── orders.py           # Order placement & history endpoints
├── templates/
│   └── index.html          # Trading terminal UI
├── static/
│   ├── style.css           # Light & dark theme styles
│   ├── app.js              # Frontend JavaScript
│   └── favicon.svg         # SVG favicon
├── pyproject.toml          # Dependencies
├── uv.lock                 # Lock file
└── .gitignore
```

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A running **PostgreSQL** server (only if using PostgreSQL)
- Fyers API app credentials for each account:
  - `client_id` (App ID, e.g. `L9NY305RTW-100`)
  - `secret_key` (App Secret)
  - `fyers_username` (Fyers Client ID, e.g. `TK01248`)
  - `totp_key` (from [MyAccount > ManageAccount](https://myaccount.fyers.in/ManageAccount))
  - `pin` (4-digit login PIN)
  - `redirect_uri` (your app's redirect URI)

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/011_place_multiple_orders_Fyers.git
cd 011_place_multiple_orders_Fyers

uv sync
```

Or with pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] aiosqlite asyncpg fyers-apiv3 requests
```

### 2. Configure

Edit `config.py`:

```python
# SQLite (default — zero config)
DATABASE_URL = "sqlite+aiosqlite:///fyers_orders.db"

# PostgreSQL (uncomment to use)
# DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/fyers_orders"
```

### 3. Run

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** in your browser.

---

## Usage

### Step 1 — Add Accounts

Go to the **Accounts** tab and click **+ Add Account**. Fill in credentials for each of your Fyers accounts:

| Field | Example |
|-------|---------|
| Account Name | Primary Account |
| Fyers Username | `TK01248` |
| Client ID | `L9NY305RTW-100` |
| Secret Key | `your_secret_key` |
| TOTP Key | `OMKRABCDCDVDFGECLWXK6OVB7T4DTKU5` |
| PIN | `1234` |
| Redirect URI | `https://trade.fyers.in/api-login/redirect-uri/index.html` |

Repeat for multiple accounts.

**Note: 2FA should be enabled for the accounts.**

### Step 2 — Generate Tokens

Go to the **Token Management** tab and click **Generate All Tokens**.

The system automatically:
1. Sends a login OTP using your TOTP key
2. Verifies the OTP and PIN
3. Obtains an auth code via the V3 token endpoint
4. Exchanges it for a 24-hour access token

Tokens are stored in the database and reused until they expire. The **background scheduler** auto-refreshes tokens every 30 minutes.

### Step 3 — Place Orders

In the **Trading Terminal** tab:

1. Enter the symbol (e.g. `NSE:SBIN-EQ`)
2. Set quantity, product type, and order type
3. For SL-Limit / SL-Market orders, enter the stop price
4. Select which accounts to send the order to via checkboxes
5. Click **BUY** or **SELL**

For derivatives (F&O), the quantity is validated against the instrument's lot size.

### Step 4 — Review History

The **Order History** tab shows all past orders grouped by batch, with per-account status and raw API responses.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/accounts` | List all accounts |
| `POST` | `/api/v1/accounts` | Add account |
| `GET` | `/api/v1/accounts/{id}` | Get account details |
| `PUT` | `/api/v1/accounts/{id}` | Update account |
| `DELETE` | `/api/v1/accounts/{id}` | Delete account |
| `POST` | `/api/v1/tokens/generate` | Generate tokens for all or specific accounts |
| `GET` | `/api/v1/tokens/status` | Token validity status for all accounts |
| `GET` | `/api/v1/tokens/scheduler` | Scheduler status |
| `POST` | `/api/v1/tokens/refresh` | Manual token refresh |
| `POST` | `/api/v1/orders/place` | Place order across selected accounts |
| `GET` | `/api/v1/orders/history` | Order history with optional `batch_id` filter |
| `GET` | `/health` | Health check (DB, scheduler, accounts) |

Interactive API docs available at **http://localhost:8000/docs**.

---

## Database

### SQLite (default)

No setup required. The database file `fyers_orders.db` is created automatically on first run.

### PostgreSQL

1. Create the database:

```sql
CREATE DATABASE fyers_orders;
```

2. Update `config.py`:

```python
DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/fyers_orders"
```

Tables are created automatically on startup.

---

## Configuration Reference

All settings live in `config.py`:

```python
# Database URL
DATABASE_URL = "sqlite+aiosqlite:///fyers_orders.db"

# Fyers API redirect URI
DEFAULT_REDIRECT_URI = "https://trade.fyers.in/api-login/redirect-uri/index.html"

# Server bind
HOST = "0.0.0.0"
PORT = 8000
```

---

## How It Works

```
┌─────────────────┐     ┌──────────────────────────────┐
│   Browser UI    │────▶│       FastAPI Backend         │
│  (index.html)   │◀────│  /api/v1/orders/place        │
└─────────────────┘     │  /api/v1/tokens/generate     │
                        │  /api/v1/accounts            │
                        │  /health                     │
                        └──────────┬───────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │ Account 1│  │ Account 2│  │ Account 3│
              │ Fyers V3 │  │ Fyers V3 │  │ Fyers V3 │
              └──────────┘  └──────────┘  └──────────┘
```

- **Token Generation**: Fully automated 5-step TOTP flow (OTP → verify TOTP → verify PIN → get auth code → exchange for access token)
- **Token Scheduler**: Background task checks every 30 minutes, refreshes tokens expiring within 1 hour
- **Order Placement**: Dispatched in parallel using `ThreadPoolExecutor` for near-simultaneous execution

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, SQLAlchemy (async), Pydantic |
| Database | SQLite (aiosqlite) / PostgreSQL (asyncpg) |
| API | Fyers API V3 |
| Frontend | Vanilla HTML/CSS/JS, Montserrat font |
| Auth | TOTP-based 2FA (automated) |
| Concurrency | ThreadPoolExecutor (parallel order placement) |

---

## License

MIT
