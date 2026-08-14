"""요청 언어(쿠키 / Accept-Language)에 따른 서버 메시지 번역."""

from __future__ import annotations

from typing import Any

COOKIE_NAME = "cityflow_lang"
SUPPORTED = ("ko", "en")

STRINGS: dict[str, dict[str, str]] = {
    "ko": {
        "auth.id_min": "로그인 ID는 3자 이상이어야 합니다.",
        "auth.name_required": "이름을 입력하세요.",
        "auth.password_min": "비밀번호는 8자 이상이어야 합니다.",
        "auth.id_taken": "이미 사용 중인 로그인 ID입니다.",
        "auth.register_ok": "회원가입이 완료되었습니다.",
        "auth.login_required": "로그인이 필요합니다.",
        "auth.bad_credentials": "아이디 또는 비밀번호가 올바르지 않습니다.",
        "auth.login_ok": "로그인되었습니다.",
        "auth.logout_ok": "로그아웃되었습니다.",
        "auth.google_not_configured": "Google 로그인이 설정되지 않았습니다.",
        "coupon.invalid_format": "쿠폰은 숫자·영문 8자리여야 합니다.",
        "coupon.login_required": "로그인이 필요합니다.",
        "coupon.invalid": "유효하지 않은 쿠폰입니다.",
        "coupon.already_used": "이미 사용한 쿠폰입니다.",
        "coupon.expired": "쿠폰이 만료되었습니다.",
        "coupon.applied": "쿠폰이 적용되었습니다.",
        "coupon.trial_started": "쿠폰 적용! PRO {days}일 체험이 시작되었습니다.",
        "coupon.trial_expired": "무료 체험이 만료되었습니다.",
        "quest.unknown": "퀘스트를 찾을 수 없습니다.",
        "quest.not_complete": "아직 완료되지 않았습니다.",
        "quest.already_claimed": "이미 보상을 받았습니다.",
        "quest.claimed": "보상을 받았습니다!",
        "quest.fail": "실패",
        "daily.not_all_complete": "모든 일일 퀘스트를 완료하세요.",
        "daily.already_claimed": "오늘 보너스는 이미 받았습니다.",
        "daily.bonus": "일일 완료 보너스!",
        "shop.not_found": "상품을 찾을 수 없습니다.",
        "shop.already_owned": "이미 보유한 스킨입니다.",
        "shop.insufficient": "코인이 부족합니다.",
        "shop.buy_failed": "구매 실패",
        "shop.purchased": "{name} 구매 완료!",
        "plan.unknown": "알 수 없는 요금제입니다.",
        "plan.applied": "{label} {days}일이 적용되었습니다.",
        "plan.demo_disabled": "PRO 체험을 사용할 수 없습니다.",
        "premium.event": "PRO 전용 이벤트입니다. PRO 가입 또는 코인 60 필요.",
        "save.no_slot": "저장 슬롯이 없습니다.",
        "save.saved": "도시가 저장되었습니다.",
        "save.missing": "저장된 도시가 없습니다.",
        "save.loaded": "도시를 불러왔습니다.",
        "stage.not_found": "스테이지를 찾을 수 없습니다.",
        "stage.goals_unmet": "아직 목표를 모두 달성하지 않았습니다.",
        "stage.already_cleared": "이미 클리어한 스테이지입니다.",
        "stage.started": "{name} 시작!",
        "stage.cleared": "{name} 클리어! 보상 지급",
        "csv.pro_only": "CSV 내보내기는 PRO 기능입니다.",
        "billing.unknown_plan": "알 수 없는 요금제입니다.",
        "billing.order_created": "주문이 생성되었습니다.",
        "billing.order_name": "CityFlow {name} 1개월",
        "billing.no_keys": "토스페이먼츠 키가 설정되지 않았습니다.",
        "billing.no_keys_hint": "토스페이먼츠 키가 없습니다. Render에 TOSS_CLIENT_KEY / TOSS_SECRET_KEY를 설정하세요.",
        "billing.confirm_failed": "결제 승인에 실패했습니다.",
        "billing.confirm_request_failed": "결제 승인 요청에 실패했습니다.",
        "billing.parse_failed": "결제 응답을 해석할 수 없습니다.",
        "billing.order_missing": "주문을 찾을 수 없습니다.",
        "billing.order_owner": "주문 소유자가 일치하지 않습니다.",
        "billing.already_paid": "이미 처리된 결제입니다.",
        "billing.amount_mismatch": "결제 금액이 주문과 다릅니다.",
        "billing.cancelled": "결제가 취소되었거나 실패했습니다.",
        "pay.ok": "결제 완료",
        "pay.fail": "결제 실패",
        "pay.until": "{plan} · {date}까지",
        "stage.stage_01_first_flow.name": "스테이지 1 · 첫 흐름",
        "stage.stage_02_junction.name": "스테이지 2 · 교차로 구축",
        "stage.stage_03_cargo_line.name": "스테이지 3 · 화물 노선",
        "stage.stage_04_rescue.name": "스테이지 4 · 구조 작전",
        "shop.booster_xp_1h.name": "XP 부스터 (1시간)",
        "shop.cosmetic_neon.name": "네온 도로 스킨",
        "shop.cosmetic_sunset.name": "선셋 스킨",
        "shop.save_slot_extra.name": "도시 저장 슬롯 +1",
    },
    "en": {
        "auth.id_min": "Login ID must be at least 3 characters.",
        "auth.name_required": "Please enter your name.",
        "auth.password_min": "Password must be at least 8 characters.",
        "auth.id_taken": "That login ID is already taken.",
        "auth.register_ok": "Account created.",
        "auth.login_required": "Please sign in.",
        "auth.bad_credentials": "Incorrect ID or password.",
        "auth.login_ok": "Signed in.",
        "auth.logout_ok": "Signed out.",
        "auth.google_not_configured": "Google sign-in is not configured.",
        "coupon.invalid_format": "Coupon must be 8 letters or numbers.",
        "coupon.login_required": "Please sign in.",
        "coupon.invalid": "This coupon is not valid.",
        "coupon.already_used": "You have already used this coupon.",
        "coupon.expired": "This coupon has expired.",
        "coupon.applied": "Coupon applied.",
        "coupon.trial_started": "Coupon applied! Your {days}-day PRO trial has started.",
        "coupon.trial_expired": "Your free trial has expired.",
        "quest.unknown": "Quest not found.",
        "quest.not_complete": "This quest is not complete yet.",
        "quest.already_claimed": "Reward already claimed.",
        "quest.claimed": "Reward claimed!",
        "quest.fail": "Failed",
        "daily.not_all_complete": "Complete all daily quests first.",
        "daily.already_claimed": "Today's bonus was already claimed.",
        "daily.bonus": "Daily completion bonus!",
        "shop.not_found": "Item not found.",
        "shop.already_owned": "You already own this skin.",
        "shop.insufficient": "Not enough coins.",
        "shop.buy_failed": "Purchase failed",
        "shop.purchased": "Purchased {name}!",
        "plan.unknown": "Unknown plan.",
        "plan.applied": "{label} applied for {days} days.",
        "plan.demo_disabled": "PRO trial is not available.",
        "premium.event": "PRO-only event. Subscribe to PRO or spend 60 coins.",
        "save.no_slot": "No save slot available.",
        "save.saved": "City saved.",
        "save.missing": "No saved city in this slot.",
        "save.loaded": "City loaded.",
        "stage.not_found": "Stage not found.",
        "stage.goals_unmet": "You have not met all goals yet.",
        "stage.already_cleared": "This stage is already cleared.",
        "stage.started": "{name} started!",
        "stage.cleared": "{name} cleared! Rewards granted",
        "csv.pro_only": "CSV export is a PRO feature.",
        "billing.unknown_plan": "Unknown plan.",
        "billing.order_created": "Order created.",
        "billing.order_name": "CityFlow {name} 1 month",
        "billing.no_keys": "Toss Payments keys are not configured.",
        "billing.no_keys_hint": "Toss Payments keys are missing. Set TOSS_CLIENT_KEY / TOSS_SECRET_KEY on Render.",
        "billing.confirm_failed": "Payment confirmation failed.",
        "billing.confirm_request_failed": "Payment confirmation request failed.",
        "billing.parse_failed": "Could not parse the payment response.",
        "billing.order_missing": "Order not found.",
        "billing.order_owner": "This order belongs to another account.",
        "billing.already_paid": "This payment was already processed.",
        "billing.amount_mismatch": "Payment amount does not match the order.",
        "billing.cancelled": "Payment was cancelled or failed.",
        "pay.ok": "Payment complete",
        "pay.fail": "Payment failed",
        "pay.until": "{plan} · until {date}",
        "stage.stage_01_first_flow.name": "Stage 1 · First flow",
        "stage.stage_02_junction.name": "Stage 2 · Build a junction",
        "stage.stage_03_cargo_line.name": "Stage 3 · Cargo line",
        "stage.stage_04_rescue.name": "Stage 4 · Rescue ops",
        "shop.booster_xp_1h.name": "XP booster (1 hour)",
        "shop.cosmetic_neon.name": "Neon road skin",
        "shop.cosmetic_sunset.name": "Sunset skin",
        "shop.save_slot_extra.name": "City save slot +1",
    },
}


def current_lang() -> str:
    """요청 컨텍스트가 없으면 한국어(테스트 호환)."""
    try:
        from flask import has_request_context, request

        if not has_request_context():
            return "ko"
        cookie = (request.cookies.get(COOKIE_NAME) or "").strip().lower()
        if cookie in SUPPORTED:
            return cookie
        header = (request.headers.get("Accept-Language") or "").strip().lower()
        primary = header.split(",")[0].split(";")[0].strip()
        if primary.startswith("en"):
            return "en"
        if primary.startswith("ko"):
            return "ko"
    except Exception:
        pass
    return "ko"


def t(key: str, *, lang: str | None = None, default: str | None = None, **kwargs: Any) -> str:
    chosen = lang if lang in SUPPORTED else current_lang()
    table = STRINGS.get(chosen) or STRINGS["ko"]
    text = table.get(key) or STRINGS["ko"].get(key) or default or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            pass
    return text
