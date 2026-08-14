"""결제 주문 저장 (orders.json)."""

from __future__ import annotations

import json
import threading
import uuid
from copy import deepcopy
from typing import Any

from engagement.catalog import get_plan
from utils.i18n import t
from utils.variables import data_dir
from engagement import profile_store

_lock = threading.Lock()
ORDERS_PATH = data_dir() / "orders.json"


def _load() -> dict[str, Any]:
    if not ORDERS_PATH.is_file():
        return {"orders": {}}
    try:
        data = json.loads(ORDERS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"orders": {}}
    if not isinstance(data, dict):
        return {"orders": {}}
    data.setdefault("orders", {})
    return data


def _save(data: dict[str, Any]) -> None:
    ORDERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = ORDERS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(ORDERS_PATH)


def new_order_id() -> str:
    return f"cf{uuid.uuid4().hex[:18]}"


def create_order(login_id: str, plan_id: str) -> tuple[bool, str, dict[str, Any] | None]:
    plan = get_plan(plan_id)
    if plan is None:
        return False, t("billing.unknown_plan"), None
    login_id = login_id.strip().lower()
    order = {
        "order_id": new_order_id(),
        "login_id": login_id,
        "plan_id": plan["id"],
        "amount": int(plan["price_krw"]),
        "price_usd": int(plan["price_usd"]),
        "order_name": t("billing.order_name", name=plan["name"]),
        "status": "pending",
        "created_at": profile_store.iso_now(),
        "payment_key": None,
    }
    with _lock:
        data = _load()
        data["orders"][order["order_id"]] = order
        _save(data)
    return True, t("billing.order_created"), deepcopy(order)


def get_order(order_id: str) -> dict[str, Any] | None:
    with _lock:
        found = _load().get("orders", {}).get(order_id)
        return deepcopy(found) if isinstance(found, dict) else None


def mark_paid(order_id: str, payment_key: str, toss_payload: dict[str, Any]) -> dict[str, Any] | None:
    with _lock:
        data = _load()
        order = data.get("orders", {}).get(order_id)
        if not isinstance(order, dict):
            return None
        order["status"] = "paid"
        order["payment_key"] = payment_key
        order["paid_at"] = profile_store.iso_now()
        order["method"] = toss_payload.get("method")
        data["orders"][order_id] = order
        _save(data)
        return deepcopy(order)


def mark_failed(order_id: str, message: str) -> None:
    with _lock:
        data = _load()
        order = data.get("orders", {}).get(order_id)
        if not isinstance(order, dict):
            return
        if order.get("status") == "paid":
            return
        order["status"] = "failed"
        order["fail_message"] = message
        data["orders"][order_id] = order
        _save(data)
