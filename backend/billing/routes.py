"""토스페이먼츠 결제·성공/실패 라우트."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, render_template, request, session

from auth.routes import login_required
from billing import orders as order_store
from billing.toss import confirm_payment, customer_key_for, toss_client_key, toss_configured
from engagement.catalog import get_plan
from engagement.service import EngagementService

billing_bp = Blueprint("billing", __name__)
engagement_service: EngagementService | None = None


def init_billing_routes(service: EngagementService) -> None:
    global engagement_service
    engagement_service = service


def _svc() -> EngagementService:
    assert engagement_service is not None
    return engagement_service


def _login_id() -> str:
    return str(session.get("login_id", "")).strip().lower()


@billing_bp.route("/api/billing/config")
@login_required
def billing_config() -> Response:
    return jsonify(
        {
            "ok": True,
            "billing_enabled": toss_configured(),
            "plans": _svc().get_public(_login_id()).get("plans", []),
        }
    )


@billing_bp.route("/pro/checkout")
@login_required
def checkout_page() -> Any:
    if not toss_configured():
        return render_template(
            "checkout.html",
            error="토스페이먼츠 키가 없습니다. Render에 TOSS_CLIENT_KEY / TOSS_SECRET_KEY를 설정하세요.",
            order=None,
            client_key="",
            customer_key="",
        )
    plan_id = str(request.args.get("plan") or "pro")
    ok, message, order = order_store.create_order(_login_id(), plan_id)
    if not ok or order is None:
        return render_template(
            "checkout.html",
            error=message,
            order=None,
            client_key="",
            customer_key="",
        )
    return render_template(
        "checkout.html",
        error="",
        order=order,
        client_key=toss_client_key(),
        customer_key=customer_key_for(_login_id()),
        user_name=session.get("name", ""),
    )


@billing_bp.route("/pro/success")
@login_required
def payment_success() -> Any:
    payment_key = str(request.args.get("paymentKey") or "")
    order_id = str(request.args.get("orderId") or "")
    amount_raw = request.args.get("amount") or "0"
    try:
        amount = int(amount_raw)
    except (TypeError, ValueError):
        amount = 0
    order = order_store.get_order(order_id)
    if order is None:
        return render_template("pay_result.html", ok=False, message="주문을 찾을 수 없습니다.")
    if order.get("login_id") != _login_id():
        return render_template("pay_result.html", ok=False, message="주문 소유자가 일치하지 않습니다.")
    if order.get("status") == "paid":
        player = _svc().get_public(_login_id())
        return render_template("pay_result.html", ok=True, message="이미 처리된 결제입니다.", player=player)
    if int(order.get("amount") or 0) != amount:
        order_store.mark_failed(order_id, "amount_mismatch")
        return render_template("pay_result.html", ok=False, message="결제 금액이 주문과 다릅니다.")

    ok, payload = confirm_payment(payment_key, order_id, amount)
    if not ok:
        order_store.mark_failed(order_id, str(payload.get("message") or "confirm_failed"))
        return render_template(
            "pay_result.html",
            ok=False,
            message=str(payload.get("message") or "결제 승인에 실패했습니다."),
        )

    paid = order_store.mark_paid(order_id, payment_key, payload)
    plan_id = str((paid or order).get("plan_id") or "pro")
    plan = get_plan(plan_id)
    days = int(plan.get("days", 30)) if plan else 30
    granted, message, player = _svc().grant_plan(_login_id(), plan_id, days=days, source="toss")
    if not granted:
        return render_template("pay_result.html", ok=False, message=message, player=player)
    return render_template("pay_result.html", ok=True, message=message, player=player)


@billing_bp.route("/pro/fail")
@login_required
def payment_fail() -> Any:
    order_id = str(request.args.get("orderId") or "")
    message = str(request.args.get("message") or "결제가 취소되었거나 실패했습니다.")
    if order_id:
        order_store.mark_failed(order_id, message)
    return render_template("pay_result.html", ok=False, message=message)
