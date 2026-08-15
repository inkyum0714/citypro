"""무료 사용자 광고 설정. 성인·선정성 카테고리는 코드에서 항상 제외합니다."""

from __future__ import annotations

from typing import Any

from billing.toss import toss_configured
from utils.variables import env_str, get_variable

# 하우스 광고·네트워크 요청에서 절대 허용하지 않는 카테고리
BLOCKED_AD_CATEGORIES = ("adult", "sexual", "dating", "pornography")
MAX_AD_CONTENT_RATING = "PG"
ADSENSE_PLACEHOLDER_CLIENT = "ca-pub-YOUR_CLIENT_ID"
ADSENSE_PLACEHOLDER_SLOT = "YOUR_AD_SLOT_ID"

HOUSE_ADS: tuple[dict[str, Any], ...] = (
    {
        "id": "pro_upgrade",
        "categories": ("productivity", "games"),
        "title_key": "ad.house_title",
        "body_key": "ad.house_body",
        "cta_key": "ad.card_open",
        "image": "city",
    },
)


def _is_configured_adsense_value(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    upper = text.upper()
    if "YOUR_CLIENT_ID" in upper or "YOUR_AD_SLOT_ID" in upper or "XXXXXXXX" in upper:
        return False
    return True


def _adsense_client() -> str:
    return env_str("ADSENSE_CLIENT_ID") or str(get_variable("ads", "adsense_client", "") or "")


def _adsense_slot() -> str:
    return env_str("ADSENSE_SLOT_ID") or str(get_variable("ads", "adsense_slot", "") or "")


def _adsense_slots() -> list[str]:
    raw = get_variable("ads", "adsense_slots", []) or []
    values: list[str] = []
    if isinstance(raw, list):
        values.extend(str(item).strip() for item in raw if str(item).strip())
    single = _adsense_slot()
    if single:
        values.append(single)
    seen: set[str] = set()
    slots: list[str] = []
    for item in values:
        if item in seen or not _is_configured_adsense_value(item):
            continue
        seen.add(item)
        slots.append(item)
    return slots


def _adfit_unit() -> str:
    return env_str("ADFIT_UNIT_ID") or str(get_variable("ads", "adfit_unit", "") or "")


def _blocked_set() -> set[str]:
    return {str(item).strip().lower() for item in BLOCKED_AD_CATEGORIES if str(item).strip()}


def is_adult_category(category: str) -> bool:
    return str(category or "").strip().lower() in _blocked_set()


def filter_house_ads(ads: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    """성인·데이팅 등 차단 카테고리가 하나라도 있으면 인벤토리에서 제거합니다."""
    blocked = _blocked_set()
    safe: list[dict[str, Any]] = []
    for ad in ads:
        cats = {str(c).strip().lower() for c in (ad.get("categories") or ())}
        if cats & blocked:
            continue
        safe.append(ad)
    return safe


def adsense_loader_src(client: str) -> str:
    """Display Ads 공식 로더 URL."""
    return f"https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={client}"


def adsense_display_unit_html(client: str, slot: str) -> str:
    """Google AdSense Display Ads 공식 스니펫과 동일한 유닛 마크업."""
    return (
        '<!-- Display Ads -->\n'
        '<ins class="adsbygoogle"\n'
        '     style="display:block"\n'
        f'     data-ad-client="{client}"\n'
        f'     data-ad-slot="{slot}"\n'
        '     data-ad-format="auto"\n'
        '     data-full-width-responsive="true"></ins>'
    )


def public_ads_config() -> dict[str, Any]:
    """프론트에 내려줄 광고 설정. 퍼블리셔 키가 없으면 가족 안심 하우스 광고."""
    enabled = bool(get_variable("ads", "enabled", True))
    client_raw = _adsense_client()
    slots = _adsense_slots()
    client = client_raw if _is_configured_adsense_value(client_raw) else ""
    slot = slots[0] if slots else ""
    adfit = _adfit_unit()
    if client and slots:
        provider = "adsense"
    elif adfit:
        provider = "adfit"
    else:
        provider = "house"
    rating = str(get_variable("ads", "max_ad_content_rating", MAX_AD_CONTENT_RATING) or MAX_AD_CONTENT_RATING)
    if rating.upper() not in ("G", "PG"):
        rating = MAX_AD_CONTENT_RATING
    return {
        "enabled": enabled,
        "provider": provider,
        "format": "card",
        "exclude_adult": True,
        "blocked_categories": list(BLOCKED_AD_CATEGORIES),
        "max_ad_content_rating": rating.upper(),
        "tag_for_child_directed_treatment": bool(
            get_variable("ads", "tag_for_child_directed_treatment", False)
        ),
        "tag_for_under_age_of_consent": bool(
            get_variable("ads", "tag_for_under_age_of_consent", False)
        ),
        "adsense_client": client,
        "adsense_slot": slot,
        "adsense_slots": slots,
        "placeholder_client": ADSENSE_PLACEHOLDER_CLIENT,
        "placeholder_slot": ADSENSE_PLACEHOLDER_SLOT,
        "adfit_unit": adfit,
        "house_ads": filter_house_ads(HOUSE_ADS),
        "billing_enabled": toss_configured(),
        "checkout_plan": "pro",
    }
