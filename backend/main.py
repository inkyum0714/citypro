"""Flask HTTP/WebSocket 진입점 — 교통 시뮬레이션 API."""
from __future__ import annotations
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any
from flask import Flask, Response, jsonify, render_template, request, session
from flask_sock import Sock
from werkzeug.middleware.proxy_fix import ProxyFix
from auth.routes import auth_bp, init_oauth, login_required
from engagement.hooks import bind_engagement, on_user_login
from engagement.routes import engagement_bp, init_engagement_routes
from engagement.service import EngagementService
from engine.sim_registry import SimulationRegistry
from engine.traffic_manager import TrafficManager
from utils.variables import get_variable
BASE_DIR: Path = Path(__file__).resolve().parent.parent
FRONTEND_DIR: Path = BASE_DIR / "frontend"
logger = logging.getLogger("cityflow")
sim_registry: SimulationRegistry = SimulationRegistry()
engagement: EngagementService = EngagementService()
clients: dict[Any, str] = {}
clients_lock: threading.Lock = threading.Lock()
_simulation_thread_started: bool = False
def _broadcast(message: str) -> None:
    with clients_lock:
        dead: list[Any] = []
        for ws in list(clients.keys()):
            try:
                ws.send(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            clients.pop(ws, None)
def _broadcast_state() -> None:
    with clients_lock:
        snapshot = list(clients.items())
    for ws, login_id in snapshot:
        try:
            manager = sim_registry.get(login_id)
            state = manager.get_state()
            player = engagement.get_public(login_id)
            payload = {
                "type": "state",
                "data": {**state, "player": player},
            }
            ws.send(json.dumps(payload, ensure_ascii=False))
        except Exception:
            with clients_lock:
                clients.pop(ws, None)
def _simulation_loop() -> None:
    sleep_s = float(get_variable("main", "simulation_step_sleep_seconds", 0.033))
    prune_every = 0.0
    while True:
        try:
            with clients_lock:
                connected = {login_id for login_id in clients.values()}
            for login_id, manager in sim_registry.items():
                if login_id not in connected and login_id not in engagement.active_user_ids():
                    continue
                try:
                    manager.step()
                    metrics = dict(getattr(manager, "frame_metrics", {}) or {})
                    if metrics:
                        engagement.apply_sim_metrics(login_id, metrics)
                except Exception:
                    logger.exception("simulation step failed for %s", login_id)
            engagement.tick_playtime(sleep_s)
            _broadcast_state()
            prune_every += sleep_s
            if prune_every >= 60.0:
                prune_every = 0.0
                sim_registry.prune_idle(keep=connected)
        except Exception:
            logger.exception("simulation loop error")
        time.sleep(sleep_s)
def _start_simulation_thread() -> None:
    global _simulation_thread_started
    if not _simulation_thread_started:
        _simulation_thread_started = True
        thread = threading.Thread(target=_simulation_loop, daemon=True)
        thread.start()
def _manager_for(login_id: str | None) -> TrafficManager:
    if not login_id:
        # 비로그인 폴백(테스트/내부용) — 공유하지 않는 임시 인스턴스
        return TrafficManager()
    return sim_registry.get(login_id)
def _handle_action(payload: dict[str, Any], login_id: str | None = None) -> dict[str, Any]:
    action = payload.get("action")
    player_update: dict[str, Any] | None = None
    traffic_manager = _manager_for(login_id)
    if action == "add_road":
        road_data = payload.get("data", {})
        lanes = road_data.get("lanes")
        try:
            lanes_i = int(lanes) if lanes is not None else None
        except (TypeError, ValueError):
            lanes_i = None
        bidirectional = bool(road_data.get("bidirectional", False))
        edge = traffic_manager.add_road(
            road_data["start"],
            road_data["end"],
            road_type=road_data.get("road_type") or road_data.get("type"),
            lanes=lanes_i,
            bidirectional=bidirectional,
        )
        if edge is None:
            return {"ok": False, "message": "도로가 너무 짧거나 연결할 수 없습니다."}
        traffic_manager.note_road_built()
        if login_id:
            player_update = engagement.record_action(login_id, "add_road")
        return {"ok": True, "message": "도로가 추가·연결되었습니다.", "player": player_update}
    if action == "trigger_event":
        event_type = payload.get("event_type")
        road_id = payload.get("road_id")
        message = payload.get("message")
        if event_type == "police_response":
            return traffic_manager.collisions.dispatch_police(
                int(road_id) if road_id is not None else None
            )
        if event_type == "tow_truck":
            return traffic_manager.collisions.dispatch_tow(
                int(road_id) if road_id is not None else None
            )
        if event_type == "clear_accident":
            return traffic_manager.collisions.clear_accidents_now(
                int(road_id) if road_id is not None else None
            )
        if login_id and event_type:
            ok, err = engagement.try_pay_premium_event(login_id, str(event_type))
            if not ok:
                return {
                    "ok": False,
                    "message": err or "VIP 호송은 PRO 가입 또는 코인 60으로 이용할 수 있습니다.",
                    "player": engagement.get_public(login_id),
                }
        event = traffic_manager.trigger_event(event_type, road_id=road_id, message=message)
        if event is None:
            return {"ok": False, "message": "알 수 없는 이벤트입니다."}
        if login_id:
            player_update = engagement.record_action(login_id, "trigger_event")
        return {"ok": True, "message": event.message, "event": event.to_dict(), "player": player_update}
    if action == "toggle_pause":
        traffic_manager.is_paused = not traffic_manager.is_paused
        state = "일시정지" if traffic_manager.is_paused else "재개"
        return {"ok": True, "message": f"시뮬레이션이 {state}되었습니다."}
    if action == "clear_events":
        traffic_manager.event_manager.clear()
        return {"ok": True, "message": "모든 이벤트가 해제되었습니다."}
    if action == "reset_simulation":
        traffic_manager.reset()
        return {"ok": True, "message": "시뮬레이션이 초기화되었습니다."}
    if action == "set_spawn_rate":
        rate = payload.get("rate")
        if rate is not None:
            rate_min = float(get_variable("main", "spawn_rate_min", 0.02))
            rate_max = float(get_variable("main", "spawn_rate_max", 0.5))
            traffic_manager.spawn_rate = max(rate_min, min(rate_max, float(rate)))
        return {"ok": True, "message": "차량 생성 빈도가 변경되었습니다."}
    if action == "set_auto_spawn":
        enabled = payload.get("enabled")
        if enabled is not None:
            traffic_manager.auto_spawn_enabled = bool(enabled)
        state = "켜짐" if traffic_manager.auto_spawn_enabled else "꺼짐"
        return {"ok": True, "message": f"자동 차량 생성: {state}"}
    if action == "spawn_vehicle":
        vtype = payload.get("vehicle_type")
        if vtype is not None and vtype not in ("", "random"):
            vehicle_type: str | None = str(vtype)
        else:
            vehicle_type = None
        world = payload.get("world") or {}
        wx = world.get("x") if isinstance(world, dict) else payload.get("world_x")
        wy = world.get("y") if isinstance(world, dict) else payload.get("world_y")
        road_id = payload.get("road_id")
        vehicle = traffic_manager.spawn_vehicle_user(
            road_id=int(road_id) if road_id is not None else None,
            lane_index=payload.get("lane_index"),
            progress=payload.get("progress"),
            world_x=float(wx) if wx is not None else None,
            world_y=float(wy) if wy is not None else None,
            vehicle_type=vehicle_type,
        )
        if vehicle is None:
            return {"ok": False, "message": "차량을 생성할 수 없습니다. 도로·차선 여유를 확인하세요."}
        if login_id:
            player_update = engagement.record_action(login_id, "spawn_vehicle")
        return {
            "ok": True,
            "message": f"차량 #{vehicle.id} 생성됨 ({vehicle.mass_kg:.0f}kg)",
            "vehicle": vehicle.to_dict(),
            "player": player_update,
        }
    if action == "dispatch_police":
        road_id = payload.get("road_id")
        return traffic_manager.collisions.dispatch_police(
            int(road_id) if road_id is not None else None
        )
    if action == "dispatch_tow":
        road_id = payload.get("road_id")
        return traffic_manager.collisions.dispatch_tow(
            int(road_id) if road_id is not None else None
        )
    if action == "clear_accidents":
        road_id = payload.get("road_id")
        return traffic_manager.collisions.clear_accidents_now(
            int(road_id) if road_id is not None else None
        )
    if action == "add_bus_stop":
        world = payload.get("world") or {}
        wx = world.get("x", payload.get("world_x"))
        wy = world.get("y", payload.get("world_y"))
        if wx is None or wy is None:
            return {"ok": False, "message": "정류장 위치가 필요합니다."}
        stop = traffic_manager.add_bus_stop_at(float(wx), float(wy))
        if stop is None:
            return {"ok": False, "message": "도로 위에 정류장을 배치할 수 없습니다."}
        if login_id:
            player_update = engagement.record_action(login_id, "add_bus_stop")
        return {"ok": True, "message": f"정류장 #{stop['id']} 개설", "bus_stop": stop, "player": player_update}

    if action == "classify_cargo":
        vehicle_id = payload.get("vehicle_id")
        cargo_type = str(payload.get("cargo_type", ""))
        if vehicle_id is None:
            return {"ok": False, "message": "차량 ID가 필요합니다."}
        result = traffic_manager.classify_cargo(int(vehicle_id), cargo_type)
        if result.get("ok") and login_id:
            player_update = engagement.record_action(login_id, "classify_cargo")
            result["player"] = player_update
        return result

    return {"ok": False, "message": "지원하지 않는 액션입니다."}

def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(FRONTEND_DIR / "templates"),
        static_folder=str(FRONTEND_DIR),
        static_url_path="",
    )
    app.secret_key = str(get_variable("auth", "session_secret", "cityflow-dev-secret-change-me"))
    public_base = str(get_variable("main", "public_base_url", "") or "").strip().rstrip("/")
    if public_base:
        from urllib.parse import urlparse
        parsed = urlparse(public_base)
        if parsed.netloc:
            app.config["SERVER_NAME"] = parsed.netloc
            app.config["PREFERRED_URL_SCHEME"] = parsed.scheme or "https"
    trust_proxy = bool(get_variable("main", "trust_proxy_headers", False))
    if trust_proxy:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    init_oauth(app)
    bind_engagement(engagement)
    init_engagement_routes(engagement, sim_registry)
    app.register_blueprint(auth_bp)
    app.register_blueprint(engagement_bp)
    sock = Sock(app)
    _start_simulation_thread()
    @app.route("/")
    @login_required
    def index() -> str:
        login_id = str(session.get("login_id", ""))
        engagement.touch(login_id)
        sim_registry.get(login_id)
        engagement.get_public(login_id)
        return render_template(
            "index.html",
            user_name=session.get("name", ""),
            login_id=login_id,
        )
    @app.route("/api/state")
    @login_required
    def get_state() -> Response:
        login_id = str(session.get("login_id", ""))
        engagement.touch(login_id)
        state = sim_registry.get(login_id).get_state()
        state["player"] = engagement.get_public(login_id)
        return jsonify(state)
    @app.route("/api/analytics/export")
    @login_required
    def export_analytics() -> Response:
        login_id = str(session.get("login_id", ""))
        profile = engagement.get_public(login_id)
        if not profile.get("is_pro") and bool(get_variable("engagement", "pro_required_for_csv_export", True)):
            return jsonify({"ok": False, "message": "CSV 내보내기는 PRO 기능입니다."}), 403
        csv_data = sim_registry.get(login_id).export_analytics_csv()
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=cityflow_analytics.csv"},
        )
    @app.route("/api/action", methods=["POST"])
    @login_required
    def api_action() -> Response:
        """WebSocket 대체 REST 액션 (연결 실패 시)."""
        login_id = str(session.get("login_id", ""))
        payload: dict[str, Any] = request.get_json(silent=True) or {}
        result = _handle_action(payload, login_id=login_id)
        return jsonify(result)
    @app.route("/api/events", methods=["POST"])
    @login_required
    def trigger_event_api() -> Response:
        payload: dict[str, Any] = {"action": "trigger_event", **(request.get_json(silent=True) or {})}
        login_id = str(session.get("login_id", ""))
        return jsonify(_handle_action(payload, login_id=login_id))
    @sock.route("/ws")
    def simulation(ws: Any) -> None:
        login_id = str(session.get("login_id", "") or "")
        if not login_id:
            ws.send(json.dumps({"type": "error", "data": {"message": "로그인이 필요합니다."}}))
            return
        _start_simulation_thread()
        with clients_lock:
            clients[ws] = login_id
        engagement.touch(login_id)
        manager = sim_registry.get(login_id)
        state = manager.get_state()
        state["player"] = engagement.get_public(login_id)
        ws.send(json.dumps({"type": "state", "data": state}, ensure_ascii=False))
        try:
            while True:
                data = ws.receive()
                if data is None:
                    break
                try:
                    payload = json.loads(data)
                except (TypeError, json.JSONDecodeError):
                    ws.send(
                        json.dumps(
                            {"type": "action_result", "data": {"ok": False, "message": "잘못된 JSON입니다."}},
                            ensure_ascii=False,
                        )
                    )
                    continue
                if not isinstance(payload, dict):
                    ws.send(
                        json.dumps(
                            {"type": "action_result", "data": {"ok": False, "message": "잘못된 요청입니다."}},
                            ensure_ascii=False,
                        )
                    )
                    continue
                engagement.touch(login_id)
                result = _handle_action(payload, login_id=login_id)
                ws.send(json.dumps({"type": "action_result", "data": result}, ensure_ascii=False))
        finally:
            with clients_lock:
                clients.pop(ws, None)
    return app
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    debug = bool(get_variable("main", "flask_debug", True))
    port = int(get_variable("main", "flask_port", 5000))
    app.run(debug=debug, port=port)
