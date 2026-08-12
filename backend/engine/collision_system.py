"""충돌 검사·작용반작용 처리·사고 구조(경찰/견인)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from engine.vehicle_physics import detect_collision_pair, resolve_collision_impulse
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

    def tick(self, dt: float) -> list[dict[str, Any]]:
        if self._cooldown > 0:
            self._cooldown -= dt
        accidents: list[dict[str, Any]] = []
        vehicles = [
            v for v in self.manager.vehicles if not v.finished and not getattr(v, "in_accident", False)
        ]
        n = len(vehicles)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = vehicles[i], vehicles[j]
                pair = (min(a.id, b.id), max(a.id, b.id))
                if pair in self._handled_pairs:
                    continue
                if not detect_collision_pair(a, b):
                    continue
                physics = self._on_collision(a, b)
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
                    accidents.append(record)

        self._tick_rescue(dt)
        return accidents

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "open_accidents": self.open_accident_count(),
            "active": list(self.active_accidents),
            "rescue_queue": [
                {"mode": j["mode"], "eta": round(j["eta"], 1), "vehicle_ids": j["vehicle_ids"]}
                for j in self._rescue_queue
            ],
        }
