import base64
import hmac
import struct
import time
import logging
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone, timedelta

import requests
from fyers_apiv3 import fyersModel

from models import Account

logger = logging.getLogger(__name__)


def generate_totp(key: str, time_step: int = 30, digits: int = 6) -> str:
    clean_key = key.rstrip("=").upper()
    key_bytes = base64.b32decode(clean_key + "=" * ((8 - len(clean_key)) % 8))
    counter = struct.pack(">Q", int(time.time() / time_step))
    mac = hmac.new(key_bytes, counter, "sha1").digest()
    offset = mac[-1] & 0x0F
    binary = struct.unpack(">L", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary)[-digits:].zfill(digits)


def generate_access_token(account: Account) -> dict:
    """Generate a fresh access token for a Fyers account using TOTP 2FA.

    Returns dict with keys: success (bool), access_token (str), error (str|None)
    """
    try:
        s = requests.Session()
        s.headers.update({
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

        # Step 1: Send login OTP
        data1 = f'{{"fy_id":"{base64.b64encode(account.fyers_username.encode()).decode()}","app_id":"2"}}'
        r1 = s.post("https://api-t2.fyers.in/vagator/v2/send_login_otp_v2", data=data1)
        logger.info("[%s] Step1 send_login_otp status=%d", account.name, r1.status_code)
        r1.raise_for_status()
        request_key = r1.json()["request_key"]

        # Step 2: Verify TOTP OTP
        totp_code = generate_totp(account.totp_key)
        data2 = f'{{"request_key":"{request_key}","otp":{totp_code}}}'
        r2 = s.post("https://api-t2.fyers.in/vagator/v2/verify_otp", data=data2)
        logger.info("[%s] Step2 verify_otp status=%d", account.name, r2.status_code)
        r2.raise_for_status()
        request_key = r2.json()["request_key"]

        # Step 3: Verify PIN
        encoded_pin = base64.b64encode(account.pin.encode()).decode()
        data3 = f'{{"request_key":"{request_key}","identity_type":"pin","identifier":"{encoded_pin}"}}'
        r3 = s.post("https://api-t2.fyers.in/vagator/v2/verify_pin_v2", data=data3)
        logger.info("[%s] Step3 verify_pin status=%d", account.name, r3.status_code)
        r3.raise_for_status()
        bearer_token = r3.json()["data"]["access_token"]

        # Step 4: Get auth code via token endpoint (V3)
        headers = {
            "authorization": f"Bearer {bearer_token}",
            "content-type": "application/json; charset=UTF-8",
        }
        payload4 = {
            "fyers_id": account.fyers_username,
            "app_id": account.client_id[:-4],
            "redirect_uri": account.redirect_uri,
            "appType": "100",
            "code_challenge": "",
            "state": "abcdefg",
            "scope": "",
            "nonce": "",
            "response_type": "code",
            "create_cookie": True,
        }
        r4 = s.post("https://api-t1.fyers.in/api/v3/token", headers=headers, json=payload4, allow_redirects=False)
        logger.info("[%s] Step4 token endpoint status=%d", account.name, r4.status_code)

        if r4.status_code not in (302, 308):
            return {"success": False, "access_token": None, "error": f"Token endpoint returned {r4.status_code}: {r4.text}"}

        parsed = urlparse(r4.json()["Url"])
        auth_code = parse_qs(parsed.query)["auth_code"][0]

        # Step 5: Exchange auth code for access token
        session = fyersModel.SessionModel(
            client_id=account.client_id,
            secret_key=account.secret_key,
            redirect_uri=account.redirect_uri,
            response_type="code",
            grant_type="authorization_code",
        )
        session.set_token(auth_code)
        response = session.generate_token()
        logger.info("[%s] Step5 generate_token response keys: %s", account.name, list(response.keys()) if isinstance(response, dict) else type(response))

        if "access_token" in response:
            logger.info("[%s] Token generated successfully", account.name)
            return {"success": True, "access_token": response["access_token"], "error": None}
        else:
            logger.warning("[%s] No access_token in response: %s", account.name, response)
            return {"success": False, "access_token": None, "error": str(response)}

    except Exception as e:
        logger.exception("Token generation failed for account %s", account.name)
        return {"success": False, "access_token": None, "error": str(e)}


def create_fyers_client(account: Account):
    """Create a FyersModel instance for an account. Returns None if no token."""
    if not account.access_token:
        return None
    return fyersModel.FyersModel(
        client_id=account.client_id,
        token=account.access_token,
        is_async=False,
        log_path="",
    )


def place_single_order(account: Account, order_data: dict) -> dict:
    """Place an order on a single account. Returns the API response dict."""
    client = create_fyers_client(account)
    if not client:
        return {"s": "error", "message": "No access token available. Generate token first."}

    try:
        response = client.place_order(data=order_data)
        return response
    except Exception as e:
        logger.exception("Order placement failed for %s", account.name)
        return {"s": "error", "message": str(e)}
