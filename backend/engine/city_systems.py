"""도시 시설(주택·공공·상업)과 횡단보도."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from utils.math_helpers import closest_road_at_point, position_on_road, road_length, road_normal
from utils.variables import get_variable

if TYPE_CHECKING:
    from engine.traffic_manager import TrafficManager
    from engine.vehicle import Vehicle

BUILDING_CATALOG: dict[str, dict[str, Any]] = {
    "house_detached": {
        "group": "housing",
        "label": "단독주택",
        "w": 22,
        "d": 18,
        "fill": "#fbbf24",
        "stroke": "#92400e",
        "demand": 1.0,
        "lot": 28,
    },
    "house_town": {
        "group": "housing",
        "label": "연립주택",
        "w": 28,
        "d": 16,
        "fill": "#fb923c",
        "stroke": "#9a3412",
        "demand": 2.2,
        "lot": 30,
    },
    "house_apt": {
        "group": "housing",
        "label": "아파트",
        "w": 36,
        "d": 24,
        "fill": "#64748b",
        "stroke": "#1e293b",
        "demand": 6.0,
        "lot": 38,
    },
    "city_hall": {
        "group": "civic",
        "label": "시청",
        "w": 42,
        "d": 28,
        "fill": "#1d4ed8",
        "stroke": "#1e3a8a",
        "demand": 0.4,
        "lot": 44,
        "unique": True,
    },
    "police": {
        "group": "civic",
        "label": "경찰서",
        "w": 30,
        "d": 22,
        "fill": "#1e40af",
        "stroke": "#172554",
        "demand": 0.3,
        "lot": 34,
    },
    "fire": {
        "group": "civic",
        "label": "소방서",
        "w": 30,
        "d": 22,
        "fill": "#b91c1c",
        "stroke": "#7f1d1d",
        "demand": 0.3,
        "lot": 34,
    },
    "school": {
        "group": "civic",
        "label": "학교",
        "w": 38,
        "d": 26,
        "fill": "#0d9488",
        "stroke": "#115e59",
        "demand": 0.5,
        "lot": 40,
    },
    "hospital": {
        "group": "civic",
        "label": "병원",
        "w": 38,
        "d": 26,
        "fill": "#e11d48",
        "stroke": "#9f1239",
        "demand": 0.6,
        "lot": 40,
    },
    "market": {
        "group": "commerce",
        "label": "마트",
        "w": 40,
        "d": 28,
        "fill": "#16a34a",
        "stroke": "#14532d",
        "demand": 0.8,
        "lot": 42,
    },
    "convenience": {
        "group": "commerce",
        "label": "편의점",
        "w": 20,
        "d": 16,
        "fill": "#22c55e",
        "stroke": "#166534",
        "demand": 0.35,
        "lot": 26,
    },
    "villa": {
        "group": "housing",
        "label": "빌라",
        "w": 26,
        "d": 20,
        "fill": "#f59e0b",
        "stroke": "#92400e",
        "demand": 1.6,
        "lot": 30,
    },
    "officetel": {
        "group": "housing",
        "label": "오피스텔",
        "w": 30,
        "d": 22,
        "fill": "#94a3b8",
        "stroke": "#334155",
        "demand": 3.4,
        "lot": 34,
    },
    "office": {
        "group": "commerce",
        "label": "사무실",
        "w": 34,
        "d": 24,
        "fill": "#0284c7",
        "stroke": "#0c4a6e",
        "demand": 0.7,
        "lot": 36,
    },
    "hotel": {
        "group": "commerce",
        "label": "호텔",
        "w": 36,
        "d": 26,
        "fill": "#7c3aed",
        "stroke": "#4c1d95",
        "demand": 0.9,
        "lot": 38,
    },
    "park": {
        "group": "civic",
        "label": "공원",
        "w": 44,
        "d": 32,
        "fill": "#4ade80",
        "stroke": "#166534",
        "demand": 0.15,
        "lot": 48,
    },
    "library": {
        "group": "civic",
        "label": "도서관",
        "w": 36,
        "d": 24,
        "fill": "#0f766e",
        "stroke": "#134e4a",
        "demand": 0.4,
        "lot": 38,
    },
    "pharmacy": {
        "group": "commerce",
        "label": "약국",
        "w": 20,
        "d": 16,
        "fill": "#2dd4bf",
        "stroke": "#115e59",
        "demand": 0.3,
        "lot": 26,
    },
    "restaurant": {
        "group": "commerce",
        "label": "식당",
        "w": 24,
        "d": 18,
        "fill": "#fb7185",
        "stroke": "#9f1239",
        "demand": 0.45,
        "lot": 28,
    },
    "gas_station": {
        "group": "commerce",
        "label": "주유소",
        "w": 32,
        "d": 22,
        "fill": "#facc15",
        "stroke": "#854d0e",
        "demand": 0.5,
        "lot": 36,
    },
    "factory": {
        "group": "industry",
        "label": "공장",
        "w": 46,
        "d": 30,
        "fill": "#78716c",
        "stroke": "#44403c",
        "demand": 0.25,
        "lot": 50,
    },
}


def building_catalog() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for building_id, spec in BUILDING_CATALOG.items():
        rows.append({"id": building_id, **spec})
    return rows


class BuildingSystem:
    """도로 옆 필지에 도시 시설을 둡니다. 주택이 통행 수요를 만듭니다."""

    def __init__(self, manager: TrafficManager) -> None:
        self.manager = manager
        self.buildings: list[dict[str, Any]] = []
        self._next_id = 1

    def clear(self) -> None:
        self.buildings.clear()
        self._next_id = 1

    def count(self) -> int:
        return len(self.buildings)

    def add_at_world(self, x: float, y: float, building_type: str) -> dict[str, Any] | None:
        spec = BUILDING_CATALOG.get(str(building_type or "").strip())
        if spec is None:
            return None
        if spec.get("unique") and any(b.get("type") == building_type for b in self.buildings):
            return None
        max_dist = float(get_variable("traffic_manager", "spawn_click_max_distance", 42.0))
        hit = closest_road_at_point(self.manager.road_network.roads, x, y, max_distance=max_dist * 1.6)
        if hit is None:
            return None
        road, progress, _ = hit
        nx, ny = road_normal(road)
        lot = float(spec.get("lot", 30))
        cx, cy = position_on_road(road, progress, 0)
        side = 1.0 if ((x - cx) * nx + (y - cy) * ny) >= 0 else -1.0
        px = cx + nx * lot * side
        py = cy + ny * lot * side
        for existing in self.buildings:
            if abs(float(existing["x"]) - px) < 18 and abs(float(existing["y"]) - py) < 18:
                return None
        building = {
            "id": self._next_id,
            "type": building_type,
            "group": spec["group"],
            "label": spec["label"],
            "x": round(px, 1),
            "y": round(py, 1),
            "angle": round(math.atan2(road["end"][1] - road["start"][1], road["end"][0] - road["start"][0]), 4),
            "w": spec["w"],
            "d": spec["d"],
            "fill": spec["fill"],
            "stroke": spec["stroke"],
            "road_id": int(road["id"]),
            "progress": round(progress, 3),
            "demand": float(spec.get("demand", 0.0)),
        }
        self._next_id += 1
        self.buildings.append(building)
        return building

    def spawn_weight_bonus(self, edge: dict[str, Any]) -> float:
        road_id = int(edge.get("id", -1))
        bonus = 0.0
        for building in self.buildings:
            if int(building["road_id"]) != road_id:
                continue
            bonus += float(building.get("demand", 0.0))
        return bonus

    def trip_demand(self) -> float:
        """주택 수요 합 → 자동 스폰 가산."""
        return sum(float(b.get("demand", 0.0)) for b in self.buildings if b.get("group") == "housing")

    def to_dict(self) -> list[dict[str, Any]]:
        return list(self.buildings)

    def export(self) -> dict[str, Any]:
        return {"buildings": self.buildings, "_next_id": self._next_id}

    def load(self, data: dict[str, Any] | None) -> None:
        data = data or {}
        self.buildings = list(data.get("buildings") or [])
        self._next_id = int(data.get("_next_id", max((b.get("id", 0) for b in self.buildings), default=0) + 1))


class CrosswalkSystem:
    """도로교통법 제27조: 횡단보도 보행자가 있으면 차량이 양보합니다."""

    def __init__(self, manager: TrafficManager) -> None:
        self.manager = manager
        self.crosswalks: list[dict[str, Any]] = []
        self._next_id = 1

    def clear(self) -> None:
        self.crosswalks.clear()
        self._next_id = 1

    def add_at_world(self, x: float, y: float) -> dict[str, Any] | None:
        max_dist = float(get_variable("traffic_manager", "spawn_click_max_distance", 42.0))
        hit = closest_road_at_point(self.manager.road_network.roads, x, y, max_distance=max_dist)
        if hit is None:
            return None
        road, progress, _ = hit
        for walk in self.crosswalks:
            if walk["road_id"] == road["id"] and abs(float(walk["progress"]) - progress) < 0.06:
                return None
        wx, wy = position_on_road(road, progress, 0)
        walk = {
            "id": self._next_id,
            "road_id": int(road["id"]),
            "progress": round(progress, 3),
            "x": round(wx, 1),
            "y": round(wy, 1),
            "width": round(float(road.get("width", 18)), 1),
            "angle": round(math.atan2(road["end"][1] - road["start"][1], road["end"][0] - road["start"][0]), 4),
            "pedestrian": False,
            "timer": 0.0,
        }
        self._next_id += 1
        self.crosswalks.append(walk)
        return walk

    def tick(self, dt: float) -> None:
        walk_s = float(get_variable("phase4", "crosswalk_walk_seconds", 6.0))
        idle_s = float(get_variable("phase4", "crosswalk_idle_seconds", 11.0))
        for walk in self.crosswalks:
            walk["timer"] = float(walk.get("timer", 0.0)) + dt
            limit = walk_s if walk.get("pedestrian") else idle_s
            if walk["timer"] < limit:
                continue
            walk["timer"] = 0.0
            walk["pedestrian"] = not bool(walk.get("pedestrian"))

    def yield_distance(self, vehicle: Vehicle) -> float | None:
        """보행자가 있는 전방 횡단보도까지 거리. 없으면 None."""
        if vehicle.vehicle_type == "emergency" and bool(
            get_variable("phase4", "emergency_ignore_signal", True)
        ):
            return None
        best: float | None = None
        road_len = road_length(vehicle.road) if getattr(vehicle, "road", None) else 0.0
        if road_len < 1.0:
            return None
        for walk in self.crosswalks:
            if int(walk["road_id"]) != int(vehicle.road_id):
                continue
            if not walk.get("pedestrian"):
                continue
            delta = float(walk["progress"]) - float(vehicle.progress)
            if not getattr(vehicle, "travel_forward", True):
                delta = -delta
            if delta < 0.01 or delta > 0.45:
                continue
            dist = delta * road_len
            if best is None or dist < best:
                best = dist
        return best

    def to_dict(self) -> list[dict[str, Any]]:
        return [
            {
                "id": w["id"],
                "road_id": w["road_id"],
                "progress": w["progress"],
                "x": w["x"],
                "y": w["y"],
                "width": w["width"],
                "angle": w["angle"],
                "pedestrian": bool(w.get("pedestrian")),
            }
            for w in self.crosswalks
        ]

    def export(self) -> dict[str, Any]:
        return {"crosswalks": self.crosswalks, "_next_id": self._next_id}

    def load(self, data: dict[str, Any] | None) -> None:
        data = data or {}
        self.crosswalks = list(data.get("crosswalks") or [])
        self._next_id = int(
            data.get("_next_id", max((w.get("id", 0) for w in self.crosswalks), default=0) + 1)
        )
