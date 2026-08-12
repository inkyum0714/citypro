"""Phase 4: 교차로 신호등 상태 머신."""

from __future__ import annotations

from typing import Any

from utils.variables import get_variable


class TrafficLight:
    """단일 교차로 신호: GREEN → YELLOW → RED → GREEN."""

    def __init__(self, node_id: int, x: float, y: float) -> None:
        self.node_id = node_id
        self.x = x
        self.y = y
        self.state = "green"
        self.timer = (node_id * 0.65) % self._durations()["green"]

    def _durations(self) -> dict[str, float]:
        return {
            "green": float(get_variable("phase4", "signal_green_seconds", 14.0)),
            "yellow": float(get_variable("phase4", "signal_yellow_seconds", 3.0)),
            "red": float(get_variable("phase4", "signal_red_seconds", 14.0)),
        }

    def tick(self, dt: float) -> None:
        """상태 타이머 진행 및 전환."""
        durations = self._durations()
        self.timer += dt
        limit = durations.get(self.state, 10.0)
        if self.timer < limit:
            return
        self.timer = 0.0
        if self.state == "green":
            self.state = "yellow"
        elif self.state == "yellow":
            self.state = "red"
        else:
            self.state = "green"

    def allows_passage(self) -> bool:
        """진입·통과 허용(녹색만)."""
        return self.state == "green"

    def must_stop_before_line(self) -> bool:
        """정지선에서 멈춰야 하는 상태."""
        return self.state in ("red", "yellow")

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "state": self.state,
        }


class SignalController:
    """네트워크 교차로에 신호등을 배치·갱신."""

    def __init__(self) -> None:
        self.lights: dict[int, TrafficLight] = {}

    def sync_network(self, nodes: dict[int, dict[str, Any]], edges: list[dict[str, Any]]) -> None:
        """차수≥min인 노드에 신호등 생성."""
        min_edges = int(get_variable("phase4", "signal_min_edges_at_node", 2))
        degree: dict[int, int] = {}
        for edge in edges:
            degree[int(edge["start_node_id"])] = degree.get(int(edge["start_node_id"]), 0) + 1
            degree[int(edge["end_node_id"])] = degree.get(int(edge["end_node_id"]), 0) + 1

        active: set[int] = set()
        for node_id, count in degree.items():
            if count < min_edges:
                continue
            node = nodes.get(node_id)
            if node is None:
                continue
            active.add(node_id)
            if node_id not in self.lights:
                self.lights[node_id] = TrafficLight(node_id, float(node["x"]), float(node["y"]))
            else:
                self.lights[node_id].x = float(node["x"])
                self.lights[node_id].y = float(node["y"])

        for node_id in list(self.lights.keys()):
            if node_id not in active:
                del self.lights[node_id]

    def tick(self, dt: float, *, approach_counts: dict[int, int] | None = None) -> None:
        adaptive = bool(get_variable("phase6", "adaptive_traffic_lights", True))
        for light in self.lights.values():
            if adaptive and approach_counts and light.state == "green":
                queue = approach_counts.get(light.node_id, 0)
                bonus = float(get_variable("phase6", "adaptive_green_bonus_per_vehicle", 0.35))
                max_bonus = float(get_variable("phase6", "adaptive_green_max_bonus", 8.0))
                light.timer += min(max_bonus, queue * bonus * dt)
            light.tick(dt)

    def get_light(self, node_id: int) -> TrafficLight | None:
        return self.lights.get(node_id)

    def to_dict(self) -> list[dict[str, Any]]:
        return [light.to_dict() for light in self.lights.values()]
