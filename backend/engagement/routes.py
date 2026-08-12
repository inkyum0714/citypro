"""참여·수익화 REST API."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request, session

from auth.routes import login_required
from engagement.service import EngagementService
from engine.sim_registry import SimulationRegistry
from engine.traffic_manager import TrafficManager

engagement_bp = Blueprint("engagement", __name__)

# main에서 주입
engagement_service: EngagementService | None = None
sim_registry: SimulationRegistry | None = None


def init_engagement_routes(service: EngagementService, registry: SimulationRegistry) -> None:
    global engagement_service, sim_registry
    engagement_service = service
    sim_registry = registry


def _svc() -> EngagementService:
    assert engagement_service is not None
    return engagement_service


def _mgr() -> TrafficManager:
    assert sim_registry is not None
    return sim_registry.get(_login_id())


def _login_id() -> str:
    return str(session.get("login_id", "")).strip().lower()


@engagement_bp.route("/api/engagement/me")
@login_required
def engagement_me() -> Response:
    login_id = _login_id()
    _svc().touch(login_id)
    return jsonify({"ok": True, "player": _svc().get_public(login_id)})


@engagement_bp.route("/api/engagement/leaderboard")
@login_required
def engagement_leaderboard() -> Response:
    return jsonify({"ok": True, "leaderboard": _svc().leaderboard()})


@engagement_bp.route("/api/engagement/claim-quest", methods=["POST"])
@login_required
def claim_quest() -> Response:
    payload = request.get_json(silent=True) or {}
    quest_id = str(payload.get("quest_id", ""))
    ok, message, player = _svc().claim_quest(_login_id(), quest_id)
    return jsonify({"ok": ok, "message": message, "player": player})


@engagement_bp.route("/api/engagement/claim-daily-bonus", methods=["POST"])
@login_required
def claim_daily_bonus() -> Response:
    ok, message, player = _svc().claim_daily_bonus(_login_id())
    return jsonify({"ok": ok, "message": message, "player": player})


@engagement_bp.route("/api/engagement/shop/buy", methods=["POST"])
@login_required
def shop_buy() -> Response:
    payload = request.get_json(silent=True) or {}
    item_id = str(payload.get("item_id", ""))
    ok, message, player = _svc().purchase_shop(_login_id(), item_id)
    return jsonify({"ok": ok, "message": message, "player": player})


@engagement_bp.route("/api/engagement/pro/activate-demo", methods=["POST"])
@login_required
def pro_demo() -> Response:
    ok, message, player = _svc().activate_pro_demo(_login_id())
    return jsonify({"ok": ok, "message": message, "player": player})


@engagement_bp.route("/api/engagement/cosmetic", methods=["POST"])
@login_required
def set_cosmetic() -> Response:
    payload = request.get_json(silent=True) or {}
    cosmetic_id = str(payload.get("cosmetic_id", "default"))
    player = _svc().set_cosmetic(_login_id(), cosmetic_id)
    return jsonify({"ok": True, "player": player})


@engagement_bp.route("/api/engagement/saves")
@login_required
def list_saves() -> Response:
    return jsonify({"ok": True, **_svc().list_saves(_login_id())})


@engagement_bp.route("/api/engagement/saves", methods=["POST"])
@login_required
def save_city() -> Response:
    payload = request.get_json(silent=True) or {}
    slot = int(payload.get("slot", 0))
    name = str(payload.get("name", ""))
    snapshot = _mgr().export_city_snapshot()
    ok, message, player = _svc().save_city(_login_id(), slot, name, snapshot)
    return jsonify({"ok": ok, "message": message, "player": player})


@engagement_bp.route("/api/engagement/saves/load", methods=["POST"])
@login_required
def load_city() -> Response:
    payload = request.get_json(silent=True) or {}
    slot = int(payload.get("slot", 0))
    snapshot = _svc().get_save_snapshot(_login_id(), slot)
    if snapshot is None:
        return jsonify({"ok": False, "message": "저장된 도시가 없습니다."}), 404
    _mgr().load_city_snapshot(snapshot)
    return jsonify({"ok": True, "message": "도시를 불러왔습니다."})


@engagement_bp.route("/api/engagement/stages")
@login_required
def list_stages() -> Response:
    return jsonify({"ok": True, "stages": _svc().list_stages(_login_id())})


@engagement_bp.route("/api/engagement/stages/start", methods=["POST"])
@login_required
def start_stage() -> Response:
    payload = request.get_json(silent=True) or {}
    stage_id = str(payload.get("stage_id", ""))
    from engagement.stages import get_stage

    stage = get_stage(stage_id)
    if stage is None:
        return jsonify({"ok": False, "message": "스테이지를 찾을 수 없습니다."}), 404
    ok, message, player = _svc().start_stage(_login_id(), stage_id)
    if ok:
        _mgr().start_stage(stage)
    return jsonify({"ok": ok, "message": message, "player": player, "stage": _svc().sync_stage_progress(_login_id(), stage_id, {})})


@engagement_bp.route("/api/engagement/stages/claim", methods=["POST"])
@login_required
def claim_stage() -> Response:
    payload = request.get_json(silent=True) or {}
    stage_id = str(payload.get("stage_id", "") or _mgr().stage_id or "")
    progress = dict(_mgr().stage_progress or {})
    ok, message, player = _svc().claim_stage(_login_id(), stage_id, progress)
    if ok:
        _mgr().stage_id = None
        _mgr().stage_progress = {}
    return jsonify({"ok": ok, "message": message, "player": player})


@engagement_bp.route("/api/engagement/stages/status")
@login_required
def stage_status() -> Response:
    mgr = _mgr()
    info = _svc().sync_stage_progress(_login_id(), mgr.stage_id, dict(mgr.stage_progress or {}))
    return jsonify({"ok": True, "stage": info})
