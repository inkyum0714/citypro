"""토스페이먼츠 API 클라이언트. 시크릿 키는 환경 변수만 사용합니다."""

from __future__ import annotations

import base64
import hashlib
import logging
from typing import Any

import requests

from utils.variables import env_str

logger = logging.getLogger("cityflow.billing")

TOSS_CONFIRM_URL = "https://api.tosspayments.com/v1/payments/confirm"


def toss_client_key() -> str:
    return env_str("TOSS_CLIENT_KEY", "TOSSPAYMENTS_CLIENT_KEY")


def toss_secret_key() -> str:
    return env_str("TOSS_SECRET_KEY", "TOSSPAYMENTS_SECRET_KEY")


def toss_configured() -> bool:
    return bool(toss_client_key() and toss_secret_key())


def customer_key_for(login_id: str) -> str:
    digest = hashlib.sha256(login_id.strip().lower().encode("utf-8")).hexdigest()[:24]
    return f"cf_{digest}"


def _auth_header() -> str:
    token = base64.b64encode(f"{toss_secret_key()}:".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def confirm_payment(payment_key: str, order_id: str, amount: int) -> tuple[bool, dict[str, Any]]:
    """결제 승인. 성공 시 Toss Payment 객체를 반환합니다."""
    if not toss_configured():
        return False, {"message": "토스페이먼츠 키가 설정되지 않았습니다."}
    try:
        response = requests.post(
            TOSS_CONFIRM_URL,
            headers={
                "Authorization": _auth_header(),
                "Content-Type": "application/json",
                "Idempotency-Key": order_id[:100],
            },
            json={
                "paymentKey": payment_key,
                "orderId": order_id,
                "amount": int(amount),
            },
            timeout=15,
        )
    except requests.RequestException:
        logger.exception("toss confirm request failed")
        return False, {"message": "결제 승인 요청에 실패했습니다."}
    try:
        payload = response.json()
    except ValueError:
        return False, {"message": "결제 응답을 해석할 수 없습니다."}
    if response.status_code != 200:
        return False, {
            "message": payload.get("message") or "결제 승인에 실패했습니다.",
            "code": payload.get("code"),
        }
    return True, payload
