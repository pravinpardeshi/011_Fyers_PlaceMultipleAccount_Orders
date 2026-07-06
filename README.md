# Fyers Multi-Account Trading Terminal

Place the same order across multiple Fyers brokerage accounts simultaneously from a single web UI.

Built with **FastAPI**, **Fyers API V3**, **SQLAlchemy** (SQLite / PostgreSQL), and a vanilla **HTML/CSS/JS** frontend.

![Python](https://img.shields.io/badge/Python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)
![Fyers API](https://img.shields.io/badge/Fyers_API-V3-orange)

---

## Features

- **Multi-account order placement** — fire one order to 3+ accounts at the same time using parallel threads
- **Automated 2FA / TOTP token generation** — no manual browser login needed each morning
- **SQLite or PostgreSQL** — swap one line in `config.py` to switch
<<<<<<< HEAD
- **Light / Dark theme** — toggle from the status bar, persists in localStorage
=======
- **Dark trading terminal UI** — order form, account management, token status, order history
>>>>>>> aaf78d9aa6d8719a0083ca0879538388fc136963
- **Full order history** — every order tracked with batch grouping and API responses

---

## Project Structure

```
├── main.py                 # FastAPI app entry point
├── config.py               # All configuration (edit directly, no .env)
├── database.py             # SQLAlchemy async engine (SQLite + PostgreSQL)
├── models.py               # Account & Order database models
├── schemas.py              # Pydantic request / response schemas
├── fyers_client.py         # Fyers API V3 wrapper (TOTP auth + order placement)
├── routers/
│   ├── accounts.py         # Account CRUD endpoints
│   ├── tokens.py           # Token generation endpoints
│   └── orders.py           # Order placement & history endpoints
├── templates/
│   └── index.html          # Trading terminal UI
├── static/
<<<<<<< HEAD
│   ├── style.css           # Light & dark theme styles
=======
│   ├── style.css           # Dark theme styles
>>>>>>> aaf78d9aa6d8719a0083ca0879538388fc136963
│   └── app.js              # Frontend JavaScript
└── pyproject.toml          # Dependencies
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
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] aiosqlite fyers-apiv3 requests
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

Repeat for Multiple accounts.

# 2FA should be enabled for the accounts.

### Step 2 — Generate Tokens

Go to the **Token Management** tab and click **Generate All Tokens**.

The system automatically:
1. Sends a login OTP using your TOTP key
2. Verifies the OTP and PIN
3. Obtains an auth code
4. Exchanges it for a 24-hour access token

Tokens are stored in the database and reused until they expire.

### Step 3 — Place Orders

In the **Trading Terminal** tab:

1. Enter the symbol (e.g. `NSE:SBIN-EQ`)
2. Set quantity, product type, and order type
3. Click **BUY** or **SELL**

The order fires to **all active accounts with valid tokens simultaneously** using parallel threads.

### Step 4 — Review History

The **Order History** tab shows all past orders grouped by batch, with per-account status and raw API responses.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/accounts` | List all accounts |
| `POST` | `/api/v1/accounts` | Add account |
| `PUT` | `/api/v1/accounts/{id}` | Update account |
| `DELETE` | `/api/v1/accounts/{id}` | Delete account |
| `POST` | `/api/v1/tokens/generate` | Generate tokens (all or specific accounts) |
| `GET` | `/api/v1/tokens/status` | Token validity status |
| `POST` | `/api/v1/orders/place` | Place order across all accounts |
| `GET` | `/api/v1/orders/history` | Order history with optional `batch_id` filter |

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
┌─────────────────┐     ┌──────────────────────────┐
│   Browser UI    │────▶│      FastAPI Backend      │
│  (index.html)   │◀────│  /api/v1/orders/place     │
└─────────────────┘     │  /api/v1/tokens/generate  │
                        │  /api/v1/accounts         │
                        └──────────┬───────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │ Account 1│  │ Account 2│  │ Account 3│
              │ Fyers V3 │  │ Fyers V3 │  │ Fyers V3 │
              └──────────┘  └──────────┘  └──────────┘
```

Orders are dispatched in parallel using Python's `concurrent.futures.ThreadPoolExecutor`, achieving near-simultaneous execution across all accounts.

---

## License

MIT
