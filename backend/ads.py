"""무료 사용자 상단 광고 설정. 성인·선정성 카테고리는 코드에서 항상 제외합니다."""

from __future__ import annotations

from typing import Any

from billing.toss import toss_configured
from utils.variables import env_str, get_variable

# 하우스 광고·네트워크 요청에서 절대 허용하지 않는 카테고리
BLOCKED_AD_CATEGORIES = ("adult", "sexual", "dating", "pornography")


def _adsense_client() -> str:
    return env_str("ADSENSE_CLIENT_ID") or str(get_variable("ads", "adsense_client", "") or "")


def _adsense_slot() -> str:
    return env_str("ADSENSE_SLOT_ID") or str(get_variable("ads", "adsense_slot", "") or "")


def _adfit_unit() -> str:
    return env_str("ADFIT_UNIT_ID") or str(get_variable("ads", "adfit_unit", "") or "")


def public_ads_config() -> dict[str, Any]:
    """프론트에 내려줄 광고 설정. 퍼블리셔 키가 없으면 가족 안심 하우스 광고."""
    enabled = bool(get_variable("ads", "enabled", True))
    client = _adsense_client()
    slot = _adsense_slot()
    adfit = _adfit_unit()
    if client and slot:
        provider = "adsense"
    elif adfit:
        provider = "adfit"
    else:
        provider = "house"
    return {
        "enabled": enabled,
        "provider": provider,
        "exclude_adult": True,
        "blocked_categories": list(BLOCKED_AD_CATEGORIES),
        "adsense_client": client,
        "adsense_slot": slot,
        "adfit_unit": adfit,
        "billing_enabled": toss_configured(),
        "checkout_plan": "pro",
    }
