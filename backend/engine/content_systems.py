"""버스 정류장·트럭 화물·골든 아워 콘텐츠."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from utils.math_helpers import closest_road_at_point, position_on_road
from utils.variables import get_variable

if TYPE_CHECKING:
    from engine.traffic_manager import TrafficManager
    from engine.vehicle import Vehicle

CARGO_TYPES: list[dict[str, str]] = [
    {"id": "food", "label": "식품", "icon": "🥬"},
    {"id": "construction", "label": "건설자재", "icon": "🧱"},
    {"id": "fuel", "label": "연료", "icon": "⛽"},
    {"id": "general", "label": "일반화물", "icon": "📦"},
]

CARGO_IDS = [c["id"] for c in CARGO_TYPES]


class BusStopSystem:
    """도로 위 버스 정류장 배치·정차."""

    def __init__(self, manager: TrafficManager) -> None:
        self.manager = manager
        self.stops: list[dict[str, Any]] = []
        self._next_id = 1
        self.boardings = 0

    def clear(self) -> None:
        self.stops.clear()
        self._next_id = 1
        self.boardings = 0

    def add_at_world(self, x: float, y: float) -> dict[str, Any] | None:
        max_dist = float(get_variable("traffic_manager", "spawn_click_max_distance", 42.0))
        hit = closest_road_at_point(self.manager.road_network.roads, x, y, max_distance=max_dist)
        if hit is None:
            return None
        road, progress, _ = hit
        # 너무 가까운 정류장 중복 방지
        for stop in self.stops:
            if stop["road_id"] == road["id"] and abs(float(stop["progress"]) - progress) < 0.08:
                return None
        wx, wy = position_on_road(road, progress, 0)
        stop = {
            "id": self._next_id,
            "road_id": int(road["id"]),
            "progress": round(progress, 3),
            "x": round(wx, 1),
            "y": round(wy, 1),
        }
        self._next_id += 1
        self.stops.append(stop)
        return stop

    def tick_vehicle(self, vehicle: Vehicle, dt: float) -> bool:
        """버스가 정류장에 정차 중이면 True (이동 억제)."""
        if vehicle.vehicle_type != "bus" or vehicle.finished or vehicle.in_accident:
            return False
        dwell = float(getattr(vehicle, "bus_dwell_remaining", 0.0) or 0.0)
        if dwell > 0:
            vehicle.bus_dwell_remaining = max(0.0, dwell - dt)
            vehicle.current_speed = 0.0
            vehicle.state = "boarding"
            if vehicle.bus_dwell_remaining <= 0:
                self.boardings += 1
                vehicle.state = "moving"
            return True

        for stop in self.stops:
            if int(stop["road_id"]) != int(vehicle.road_id):
                continue
            if abs(float(vehicle.progress) - float(stop["progress"])) > 0.035:
                continue
            # 이미 이 정류장을 처리했는지
            served = getattr(vehicle, "served_stops", None)
            if served is None:
                vehicle.served_stops = set()
                served = vehicle.served_stops
            if stop["id"] in served:
                continue
            served.add(stop["id"])
            vehicle.bus_dwell_remaining = float(get_variable("content", "bus_dwell_seconds", 2.2))
            vehicle.current_speed = 0.0
            vehicle.state = "boarding"
            return True
        return False

    def to_dict(self) -> list[dict[str, Any]]:
        return list(self.stops)

    def export(self) -> dict[str, Any]:
        return {"stops": self.stops, "_next_id": self._next_id, "boardings": self.boardings}

    def load(self, data: dict[str, Any] | None) -> None:
        data = data or {}
        self.stops = list(data.get("stops") or [])
        self._next_id = int(data.get("_next_id", max((s.get("id", 0) for s in self.stops), default=0) + 1))
        self.boardings = int(data.get("boardings", 0))


class CargoSystem:
    """트럭 운반 물품 분류."""

    def __init__(self, manager: TrafficManager) -> None:
        self.manager = manager
        self.classified_count = 0

    def clear(self) -> None:
        self.classified_count = 0

    @staticmethod
    def assign_spawn_cargo(vehicle: Vehicle) -> None:
        if vehicle.vehicle_type != "truck":
            vehicle.cargo_type = None
            vehicle.cargo_classified = True
            return
        # 미분류로 스폰 — 플레이어가 분류
        vehicle.cargo_type = "unclassified"
        vehicle.cargo_classified = False

    def classify(self, vehicle_id: int, cargo_type: str) -> dict[str, Any]:
        if cargo_type not in CARGO_IDS:
            return {"ok": False, "message": "알 수 없는 화물 종류입니다."}
        vehicle = next((v for v in self.manager.vehicles if v.id == vehicle_id), None)
        if vehicle is None:
            return {"ok": False, "message": "차량을 찾을 수 없습니다."}
        if vehicle.vehicle_type != "truck":
            return {"ok": False, "message": "트럭만 화물 분류가 가능합니다."}
        if getattr(vehicle, "cargo_classified", False) and vehicle.cargo_type in CARGO_IDS:
            return {"ok": False, "message": "이미 분류된 화물입니다.", "vehicle": vehicle.to_dict()}
        vehicle.cargo_type = cargo_type
        vehicle.cargo_classified = True
        self.classified_count += 1
        label = next(c["label"] for c in CARGO_TYPES if c["id"] == cargo_type)
        return {
            "ok": True,
            "message": f"트럭 #{vehicle_id} 화물을 '{label}'(으)로 분류했습니다.",
            "vehicle": vehicle.to_dict(),
            "classified_count": self.classified_count,
        }

    def catalog(self) -> list[dict[str, str]]:
        return list(CARGO_TYPES)


class GoldenHourTracker:
    """평균 속도가 임계값 이상인 구간을 누적 (골든 아워)."""

    def __init__(self) -> None:
        self.streak_seconds = 0.0
        self.total_golden_seconds = 0.0
        self._avg_speed = 0.0
        self.active = False

    def clear(self) -> None:
        self.streak_seconds = 0.0
        self.total_golden_seconds = 0.0
        self._avg_speed = 0.0
        self.active = False

    def tick(self, vehicles: list[Vehicle], dt: float) -> float:
        """이번 틱에서 새로 쌓인 골든 초를 반환 (퀘스트 진행용)."""
        active = [
            v
            for v in vehicles
            if not v.finished and not v.in_accident and not getattr(v, "response_role", None)
        ]
        if len(active) < 2:
            self.streak_seconds = 0.0
            self.active = False
            self._avg_speed = 0.0
            return 0.0
        avg = sum(v.current_speed for v in active) / len(active)
        self._avg_speed = avg
        threshold = float(get_variable("content", "golden_hour_min_avg_speed", 22.0))
        if avg >= threshold:
            self.streak_seconds += dt
            self.total_golden_seconds += dt
            self.active = True
            return dt
        self.streak_seconds = 0.0
        self.active = False
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "streak_seconds": round(self.streak_seconds, 1),
            "total_golden_seconds": round(self.total_golden_seconds, 1),
            "avg_speed": round(self._avg_speed, 1),
            "threshold": float(get_variable("content", "golden_hour_min_avg_speed", 22.0)),
        }
