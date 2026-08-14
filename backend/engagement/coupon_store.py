"""레딧 등 프로모 쿠폰 저장 (coupons.json)."""

from __future__ import annotations

import json
import re
import threading
from copy import deepcopy
from typing import Any

from utils.variables import data_dir, env_str, get_variable

_lock = threading.Lock()
COUPONS_PATH = data_dir() / "coupons.json"
_CODE_RE = re.compile(r"^[A-Za-z0-9]{8}$")


def normalize_code(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(raw or "")).upper()


def is_valid_code_format(code: str) -> bool:
    return bool(_CODE_RE.match(code or ""))


def _seed_coupons() -> dict[str, Any]:
    code = normalize_code(env_str("REDDIT_COUPON_CODE") or str(get_variable("billing", "reddit_coupon_code", "RDT1WEEK")))
    if not is_valid_code_format(code):
        code = "RDT1WEEK"
    days = int(get_variable("billing", "coupon_trial_days", 7))
    plan = str(get_variable("billing", "coupon_trial_plan", "pro"))
    max_redemptions = int(get_variable("billing", "reddit_coupon_max", 10))
    return {
        "coupons": {
            code: {
                "code": code,
                "plan": plan,
                "days": days,
                "max_redemptions": max_redemptions,
                "redeemed_by": [],
            }
        }
    }


def _load() -> dict[str, Any]:
    if not COUPONS_PATH.is_file():
        data = _seed_coupons()
        _save(data)
        return data
    try:
        raw = json.loads(COUPONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _seed_coupons()
    if not isinstance(raw, dict):
        return _seed_coupons()
    raw.setdefault("coupons", {})
    if not raw["coupons"]:
        seeded = _seed_coupons()
        raw["coupons"].update(seeded["coupons"])
        _save(raw)
        return raw
    seeded = _seed_coupons()
    changed = False
    for code, spec in seeded["coupons"].items():
        existing = raw["coupons"].get(code)
        if existing is None:
            raw["coupons"][code] = spec
            changed = True
            continue
        for key in ("max_redemptions", "days", "plan"):
            if existing.get(key) != spec.get(key):
                existing[key] = spec[key]
                changed = True
    if changed:
        _save(raw)
    return raw


def _save(data: dict[str, Any]) -> None:
    COUPONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = COUPONS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(COUPONS_PATH)


def get_coupon(code: str) -> dict[str, Any] | None:
    code = normalize_code(code)
    with _lock:
        coupons = _load().get("coupons", {})
        found = coupons.get(code)
        return deepcopy(found) if isinstance(found, dict) else None


def redeem(code: str, login_id: str) -> tuple[bool, str, dict[str, Any] | None]:
    """
    쿠폰 1회 사용 기록.

    Returns:
        (성공, 메시지, 쿠폰 dict)
    """
    code = normalize_code(code)
    login_id = login_id.strip().lower()
    if not is_valid_code_format(code):
        return False, "쿠폰은 숫자·영문 8자리여야 합니다.", None
    if not login_id:
        return False, "로그인이 필요합니다.", None

    with _lock:
        data = _load()
        coupons = data.setdefault("coupons", {})
        coupon = coupons.get(code)
        if not isinstance(coupon, dict):
            return False, "유효하지 않은 쿠폰입니다.", None
        used = [str(u).lower() for u in coupon.get("redeemed_by") or []]
        if login_id in used:
            return False, "이미 사용한 쿠폰입니다.", None
        limit = int(coupon.get("max_redemptions", 0) or 0)
        if limit > 0 and len(used) >= limit:
            return False, "쿠폰 사용 한도에 도달했습니다.", None
        used.append(login_id)
        coupon["redeemed_by"] = used
        coupons[code] = coupon
        _save(data)
        return True, "쿠폰이 적용되었습니다.", deepcopy(coupon)
