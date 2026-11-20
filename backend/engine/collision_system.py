"""충돌 검사·작용반작용 처리·사고 구조(경찰/견인)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from engine.vehicle_physics import (
    detect_collision_pair,
    resolve_collision_impulse,
    vehicle_collision_radius,
)
from utils.variables import get_variable

if TYPE_CHECKING:
    from engine.traffic_manager import TrafficManager
    from engine.vehicle import Vehicle


class CollisionSystem:
    """차량 간 충돌 → 사고, 구조 출동으로 해결."""

    def __init__(self, manager: TrafficManager) -> None:
        self.manager = manager
        self._handled_pairs: set[tuple[int, int]] = set()
        self._cooldown = 0.0
        self.active_accidents: list[dict[str, Any]] = []
        self._rescue_queue: list[dict[str, Any]] = []
        self._active_dispatch: dict[str, Any] | None = None

    def tick(self, dt: float) -> list[dict[str, Any]]:
        if self._cooldown > 0:
            self._cooldown -= dt
        accidents: list[dict[str, Any]] = []
        if not getattr(self.manager, "_client_physics", True):
            accidents = self._scan_collisions()
        self._tick_responders(dt)
        self._tick_rescue(dt)
        return accidents

    def _scan_collisions(self) -> list[dict[str, Any]]:
        """서버 폴백 충돌 스캔. 격자 이웃만 검사."""
        accidents: list[dict[str, Any]] = []
        vehicles = [
            v for v in self.manager.vehicles if not v.finished and not getattr(v, "in_accident", False)
        ]
        spatial = getattr(self.manager, "_spatial", None)
        radius = float(get_variable("vehicle", "avoidance_scan_radius", 55.0))
        seen: set[tuple[int, int]] = set()
        for a in vehicles:
            neighbors = (
                spatial.nearby(a.x, a.y, radius) if spatial is not None else vehicles
            )
            if getattr(a, "response_role", None):
                continue
            for b in neighbors:
                if b.id <= a.id or b.finished or getattr(b, "in_accident", False):
                    continue
                if getattr(b, "response_role", None):
                    continue
                pair = (a.id, b.id)
                if pair in seen or pair in self._handled_pairs:
                    continue
                seen.add(pair)
                if not detect_collision_pair(a, b):
                    continue
                record = self._register_collision(a, b)
                if record is not None:
                    accidents.append(record)
        return accidents

    def apply_client_reports(self, pairs: list[dict[str, Any]]) -> int:
        """프론트 물리 엔진이 보낸 충돌 쌍을 검증 후 사고 처리."""
        if not pairs:
            return 0
        by_id = {v.id: v for v in self.manager.vehicles if not v.finished}
        applied = 0
        limit = int(get_variable("physics", "client_report_max_pairs", 12))
        for item in pairs[: max(1, limit)]:
            if not isinstance(item, dict):
                continue
            try:
                id_a = int(item.get("id_a", item.get("a")))
                id_b = int(item.get("id_b", item.get("b")))
            except (TypeError, ValueError):
                continue
            a = by_id.get(id_a)
            b = by_id.get(id_b)
            if a is None or b is None or a.id == b.id:
                continue
            if getattr(a, "in_accident", False) or getattr(b, "in_accident", False):
                continue
            if getattr(a, "response_role", None) or getattr(b, "response_role", None):
                continue
            pair = (min(a.id, b.id), max(a.id, b.id))
            if pair in self._handled_pairs:
                continue
            dist = math.hypot(a.x - b.x, a.y - b.y)
            max_sep = (vehicle_collision_radius(a) + vehicle_collision_radius(b)) * 4.0
            if dist > max_sep:
                continue
            self._register_collision(a, b)
            applied += 1
        return applied

    def _register_collision(self, a: Vehicle, b: Vehicle) -> dict[str, Any] | None:
        physics = self._on_collision(a, b)
        pair = (min(a.id, b.id), max(a.id, b.id))
        self._handled_pairs.add(pair)
        record = {
            "vehicle_ids": [a.id, b.id],
            "road_id": a.road_id,
            "impulse": physics.get("impulse", 0.0),
            "mass_a": physics.get("mass_a"),
            "mass_b": physics.get("mass_b"),
            "status": "open",
            "rescue": None,
        }
        self.active_accidents.append(record)
        self._begin_or_join_dispatch(record["vehicle_ids"], int(a.road_id), self._centroid(record["vehicle_ids"]))
        if self._cooldown <= 0:
            event = self.manager.trigger_event(
                "accident",
                road_id=a.road_id,
                message=(
                    f"차량 #{a.id}({a.mass_kg:.0f}kg)·#{b.id}({b.mass_kg:.0f}kg) "
                    f"충돌 충격량 {physics.get('impulse', 0):.0f}"
                ),
            )
            record["event_id"] = event.id if event else None
            self._cooldown = float(get_variable("vehicle", "accident_event_cooldown", 4.0))
            return record
        return None

    def _on_collision(self, a: Vehicle, b: Vehicle) -> dict[str, Any]:
        physics = resolve_collision_impulse(a, b)
        for v in (a, b):
            v.in_accident = True
            v.state = "accident"
            v.accident_timer = 0.0
            v.rescue_state = None
            v.acceleration = 0.0
        return physics

    def _tick_rescue(self, dt: float) -> None:
        remaining: list[dict[str, Any]] = []
        for job in self._rescue_queue:
            job["eta"] = float(job.get("eta", 0.0)) - dt
            if job["eta"] > 0:
                remaining.append(job)
                continue
            self._finish_rescue(job)
        self._rescue_queue = remaining

    def _finish_rescue(self, job: dict[str, Any]) -> None:
        mode = job.get("mode", "police")
        ids = set(job.get("vehicle_ids") or [])
        for vehicle in list(self.manager.vehicles):
            if ids and vehicle.id not in ids:
                continue
            if not vehicle.in_accident:
                continue
            if mode == "tow":
                vehicle.rescue_state = "towing"
                vehicle.state = "towed"
            else:
                vehicle.rescue_state = "cleared"
                vehicle.state = "cleared"
            vehicle.finished = True
            vehicle.in_accident = False
            vehicle.current_speed = 0.0
            vehicle.vx = 0.0
            vehicle.vy = 0.0

        for acc in self.active_accidents:
            if ids and not set(acc.get("vehicle_ids", [])).intersection(ids):
                continue
            acc["status"] = "resolved"
            acc["rescue"] = mode

        self.active_accidents = [a for a in self.active_accidents if a.get("status") != "resolved"]
        self.manager._mark_segments_dirty()
        cleared = max(1, len(ids) // 2) if ids else 1
        self.manager.accidents_cleared_total = int(getattr(self.manager, "accidents_cleared_total", 0)) + cleared
        label = "견인 완료" if mode == "tow" else "경찰 현장 정리 완료"
        icon = "🚛" if mode == "tow" else "🚓"
        self.manager.event_manager.push_message(f"{label} — 교통사고 해결", icon=icon)

    def dispatch_police(self, road_id: int | None = None) -> dict[str, Any]:
        """경찰 출동 — 사고 차량 정리."""
        targets = self._accident_vehicle_ids(road_id)
        if not targets:
            return {"ok": False, "message": "처리할 교통사고가 없습니다."}
        eta = float(get_variable("vehicle", "police_response_seconds", 3.5))
        for v in self.manager.vehicles:
            if v.id in targets:
                v.rescue_state = "police"
        self._rescue_queue.append({"mode": "police", "vehicle_ids": targets, "eta": eta})
        self.manager.trigger_event(
            "police_response",
            road_id=road_id or self._first_accident_road(),
            message=f"경찰 출동 — 사고 차량 {len(targets)}대 처리 예정",
        )
        return {"ok": True, "message": f"경찰 출동 ({eta:.0f}초 후 현장 정리)", "count": len(targets)}

    def dispatch_tow(self, road_id: int | None = None) -> dict[str, Any]:
        """견인차 출동."""
        targets = self._accident_vehicle_ids(road_id)
        if not targets:
            return {"ok": False, "message": "견인할 사고 차량이 없습니다."}
        eta = float(get_variable("vehicle", "tow_response_seconds", 5.0))
        for v in self.manager.vehicles:
            if v.id in targets:
                v.rescue_state = "towing"
        self._rescue_queue.append({"mode": "tow", "vehicle_ids": targets, "eta": eta})
        self.manager.trigger_event(
            "tow_truck",
            road_id=road_id or self._first_accident_road(),
            message=f"견인차 출동 — {len(targets)}대 견인 예정",
        )
        return {"ok": True, "message": f"견인차 출동 ({eta:.0f}초 후 견인)", "count": len(targets)}

    def clear_accidents_now(self, road_id: int | None = None) -> dict[str, Any]:
        """즉시 사고 현장 정리."""
        targets = self._accident_vehicle_ids(road_id)
        if not targets:
            return {"ok": False, "message": "정리할 사고가 없습니다."}
        self._finish_rescue({"mode": "police", "vehicle_ids": targets, "eta": 0})
        self.manager.trigger_event(
            "clear_accident",
            road_id=road_id or self._first_accident_road(),
            message="사고 현장 즉시 정리",
        )
        return {"ok": True, "message": f"사고 차량 {len(targets)}대 정리 완료", "count": len(targets)}

    def _accident_vehicle_ids(self, road_id: int | None) -> list[int]:
        ids: list[int] = []
        for v in self.manager.vehicles:
            if not v.in_accident or v.finished:
                continue
            if road_id is not None and v.road_id != road_id:
                continue
            ids.append(v.id)
        return ids

    def _first_accident_road(self) -> int | None:
        for v in self.manager.vehicles:
            if v.in_accident:
                return v.road_id
        return None

    def open_accident_count(self) -> int:
        return sum(1 for v in self.manager.vehicles if v.in_accident and not v.finished)

    def clear_stale_pairs(self) -> None:
        active = {v.id for v in self.manager.vehicles}
        self._handled_pairs = {p for p in self._handled_pairs if p[0] in active and p[1] in active}

    def ensure_dispatch_for_road(self, road_id: int | None, progress: float = 0.5) -> None:
        """사고 이벤트에 병원·119·112 출동이 없으면 보냅니다."""
        if self._active_dispatch is not None:
            return
        ids = self._accident_vehicle_ids(int(road_id) if road_id is not None else None)
        road = None
        if road_id is not None:
            road = self.manager.road_network.get_road(int(road_id))
        if road is None and self.manager.road_network.roads:
            road = self.manager.road_network.roads[0]
        if road is None:
            return
        if ids:
            self._begin_or_join_dispatch(ids, int(road["id"]), self._centroid(ids))
            return
        t = max(0.05, min(0.95, float(progress or 0.5)))
        x = float(road["start"][0]) + (float(road["end"][0]) - float(road["start"][0])) * t
        y = float(road["start"][1]) + (float(road["end"][1]) - float(road["start"][1])) * t
        self._begin_or_join_dispatch([], int(road["id"]), (x, y))

    def _centroid(self, vehicle_ids: list[int]) -> tuple[float, float]:
        points = [(v.x, v.y) for v in self.manager.vehicles if v.id in set(vehicle_ids)]
        if not points:
            return 0.0, 0.0
        return sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)

    def _nearest_building(self, building_type: str, x: float, y: float) -> dict[str, Any] | None:
        best: dict[str, Any] | None = None
        best_d = 1e18
        for building in self.manager.buildings.buildings:
            if building.get("type") != building_type:
                continue
            dist = math.hypot(float(building["x"]) - x, float(building["y"]) - y)
            if dist < best_d:
                best = building
                best_d = dist
        return best

    def _begin_or_join_dispatch(
        self,
        vehicle_ids: list[int],
        road_id: int,
        target: tuple[float, float],
    ) -> None:
        tx, ty = target
        if self._active_dispatch is not None:
            job = self._active_dispatch
            for vid in vehicle_ids:
                if vid not in job["vehicle_ids"]:
                    job["vehicle_ids"].append(vid)
            job["tx"], job["ty"] = tx, ty
            for vehicle in self.manager.vehicles:
                if getattr(vehicle, "response_role", None):
                    vehicle.response_tx = tx
                    vehicle.response_ty = ty
            return

        specs = (
            ("112", "police", "#1d4ed8", (-70.0, -36.0), "police_response", "112 출동"),
            ("119", "fire", "#dc2626", (74.0, -28.0), "fire_response", "119 출동"),
            ("hospital", "hospital", "#f8fafc", (8.0, 68.0), "ambulance", "병원 구급차 출동"),
        )
        responder_ids: list[int] = []
        needed: set[str] = set()
        road = self.manager.road_network.get_road(road_id)
        if road is None and self.manager.road_network.roads:
            road = self.manager.road_network.roads[0]
        if road is None:
            return
        for role, building_type, color, offset, event_type, label in specs:
            building = self._nearest_building(building_type, tx, ty)
            if building is not None:
                ox, oy = float(building["x"]), float(building["y"])
                origin = str(building.get("label") or building_type)
                spawn_road = self.manager.road_network.get_road(int(building["road_id"])) or road
            else:
                ox, oy = tx + offset[0], ty + offset[1]
                origin = {"112": "112", "119": "119", "hospital": "병원"}[role]
                spawn_road = road
            vehicle = self.manager.create_vehicle_on_edge(
                spawn_road,
                vehicle_type="emergency",
                progress=0.35,
            )
            vehicle.response_role = role
            vehicle.response_tx = tx
            vehicle.response_ty = ty
            vehicle.x = ox
            vehicle.y = oy
            vehicle.color = color
            vehicle.emergency_flash = True
            vehicle.state = "responding"
            vehicle.progress = 0.35
            vehicle.current_speed = float(get_variable("vehicle", "response_speed", 78.0))
            responder_ids.append(vehicle.id)
            needed.add(role)
            self.manager.event_manager.add_event(
                event_type,
                road_id=road_id,
                progress=0.5,
                message=f"{label} — {origin}에서 현장으로",
            )
        if not responder_ids:
            return
        self._active_dispatch = {
            "vehicle_ids": list(vehicle_ids),
            "responder_ids": responder_ids,
            "needed": needed,
            "arrived": set(),
            "tx": tx,
            "ty": ty,
            "road_id": road_id,
            "elapsed": 0.0,
        }
        self.manager._mark_segments_dirty()

    def _tick_responders(self, dt: float) -> None:
        job = self._active_dispatch
        if job is None:
            return
        job["elapsed"] = float(job.get("elapsed", 0.0)) + dt
        arrived: set[str] = job.setdefault("arrived", set())
        speed = float(get_variable("vehicle", "response_speed", 78.0))
        radius = float(get_variable("vehicle", "response_arrival_radius", 16.0))
        timeout = float(get_variable("vehicle", "response_timeout_seconds", 14.0))
        for vehicle in self.manager.vehicles:
            if not getattr(vehicle, "response_role", None) or vehicle.finished:
                continue
            dx = float(job["tx"]) - vehicle.x
            dy = float(job["ty"]) - vehicle.y
            dist = math.hypot(dx, dy)
            if dist < radius or float(job["elapsed"]) >= timeout:
                arrived.add(str(vehicle.response_role))
                vehicle.current_speed = 0.0
                vehicle.vx = 0.0
                vehicle.vy = 0.0
                vehicle.state = "on_scene"
                continue
            step = min(dist, speed * dt)
            vehicle.x += dx / dist * step
            vehicle.y += dy / dist * step
            vehicle.angle = math.atan2(dy, dx)
            vehicle.vx = dx / dist * speed
            vehicle.vy = dy / dist * speed
            vehicle.current_speed = speed
            vehicle.progress = 0.35
            vehicle.state = "responding"
        needed: set[str] = set(job.get("needed") or [])
        if needed and needed <= arrived:
            self._complete_dispatch()
        elif float(job["elapsed"]) >= timeout and arrived:
            self._complete_dispatch()

    def _complete_dispatch(self) -> None:
        job = self._active_dispatch
        if job is None:
            return
        ids = list(job.get("vehicle_ids") or [])
        self._active_dispatch = None
        if ids:
            self._finish_rescue({"mode": "police", "vehicle_ids": ids, "eta": 0})
            self.manager.event_manager.push_message("112·119·병원 도착 — 현장 정리", icon="🚑")
        else:
            self.manager.event_manager.push_message("112·119·병원 도착", icon="🚑")
        responder_ids = set(job.get("responder_ids") or [])
        for vehicle in self.manager.vehicles:
            if vehicle.id in responder_ids:
                vehicle.finished = True
                vehicle.state = "arrived"
                vehicle.current_speed = 0.0
        self.manager._mark_segments_dirty()

    def to_dict(self) -> dict[str, Any]:
        return {
            "open_accidents": self.open_accident_count(),
            "active": list(self.active_accidents),
            "rescue_queue": [
                {"mode": j["mode"], "eta": round(j["eta"], 1), "vehicle_ids": j["vehicle_ids"]}
                for j in self._rescue_queue
            ],
        }
