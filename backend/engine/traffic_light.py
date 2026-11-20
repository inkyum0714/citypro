"""교차로 신호. 접근로는 축(맞은편 동시 녹색)마다 위상이 다릅니다."""

from __future__ import annotations

import math
from typing import Any

from utils.variables import get_variable


def signal_should_stop(state: str, stop_dist: float, speed: float) -> bool:
    """도로교통법: 적색·보행은 정지, 황색은 안전하게 멈출 수 있으면 정지."""
    if state in ("red", "walk"):
        return True
    if state != "yellow" or stop_dist <= 0.5:
        return False
    from engine.vehicle import stopping_distance

    return stop_dist >= max(4.0, stopping_distance(speed) * 0.85)


def _approach_angle(edge: dict[str, Any], node_id: int) -> float:
    """노드로 들어오는 진행 방향."""
    if int(edge["end_node_id"]) == node_id:
        dx = float(edge["end"][0]) - float(edge["start"][0])
        dy = float(edge["end"][1]) - float(edge["start"][1])
    else:
        dx = float(edge["start"][0]) - float(edge["end"][0])
        dy = float(edge["start"][1]) - float(edge["end"][1])
    return math.atan2(dy, dx)


def _same_axis(angle: float, reference: float) -> bool:
    """맞은편(180°)은 같은 축. 직교에 가까우면 다른 축."""
    diff = (angle - reference) % math.pi
    if diff < 0:
        diff += math.pi
    if diff > math.pi / 2:
        diff = math.pi - diff
    return diff < math.pi / 4


class TrafficLight:
    """단일 상태 신호. 유닛 테스트와 정지 판정에 사용합니다."""

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
            "red": float(get_variable("phase4", "signal_red_seconds", 10.0)),
            "walk": float(get_variable("phase4", "signal_walk_seconds", 8.0)),
        }

    def tick(self, dt: float) -> None:
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
        elif self.state == "red":
            self.state = "walk"
        else:
            self.state = "green"

    def allows_passage(self) -> bool:
        return self.state == "green"

    def must_stop_before_line(self) -> bool:
        return self.state in ("red", "walk")

    def should_stop(self, stop_dist: float, speed: float) -> bool:
        return signal_should_stop(self.state, stop_dist, speed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "state": self.state,
            "pedestrian": self.state == "walk",
            "approaches": [],
        }


class JunctionSignal:
    """노드의 접근로별 위상. 같은 축은 함께 녹색입니다."""

    PHASES_TWO = ("a_green", "a_yellow", "b_green", "b_yellow", "walk")
    PHASES_ONE = ("a_green", "a_yellow", "walk")

    def __init__(self, node_id: int, x: float, y: float) -> None:
        self.node_id = node_id
        self.x = x
        self.y = y
        self.phase = "a_green"
        self.timer = (node_id * 0.37) % self._durations()["green"]
        self.approaches: list[dict[str, Any]] = []

    def _durations(self) -> dict[str, float]:
        return {
            "green": float(get_variable("phase4", "signal_green_seconds", 14.0)),
            "yellow": float(get_variable("phase4", "signal_yellow_seconds", 3.0)),
            "walk": float(get_variable("phase4", "signal_walk_seconds", 8.0)),
        }

    def sync_approaches(self, edges: list[dict[str, Any]]) -> None:
        incoming = [
            edge
            for edge in edges
            if int(edge["start_node_id"]) == self.node_id or int(edge["end_node_id"]) == self.node_id
        ]
        if not incoming:
            self.approaches = []
            return
        reference = _approach_angle(incoming[0], self.node_id)
        approaches: list[dict[str, Any]] = []
        for edge in incoming:
            angle = _approach_angle(edge, self.node_id)
            approaches.append(
                {
                    "edge_id": int(edge["id"]),
                    "angle": angle,
                    "axis": 0 if _same_axis(angle, reference) else 1,
                }
            )
        self.approaches = approaches
        if self._phases()[0] and self.phase not in self._phases():
            self.phase = self._phases()[0]

    def _phases(self) -> tuple[str, ...]:
        if any(ap["axis"] == 1 for ap in self.approaches):
            return self.PHASES_TWO
        return self.PHASES_ONE

    def state_for(self, edge_id: int) -> str | None:
        approach = next((ap for ap in self.approaches if int(ap["edge_id"]) == int(edge_id)), None)
        if approach is None:
            return None
        axis = int(approach["axis"])
        if self.phase == "walk":
            return "walk"
        if self.phase == "a_green":
            return "green" if axis == 0 else "red"
        if self.phase == "a_yellow":
            return "yellow" if axis == 0 else "red"
        if self.phase == "b_green":
            return "green" if axis == 1 else "red"
        if self.phase == "b_yellow":
            return "yellow" if axis == 1 else "red"
        return "red"

    def summary_state(self) -> str:
        states = [self.state_for(int(ap["edge_id"])) for ap in self.approaches]
        states = [s for s in states if s]
        if not states:
            return "red"
        if "green" in states and "red" in states:
            return "green"
        if all(s == "walk" for s in states):
            return "walk"
        if "yellow" in states:
            return "yellow"
        return states[0]

    def tick(self, dt: float, *, queue: int = 0, adaptive: bool = False) -> None:
        if adaptive and queue > 0 and self.phase in ("a_green", "b_green"):
            bonus = float(get_variable("phase6", "adaptive_green_bonus_per_vehicle", 0.35))
            max_bonus = float(get_variable("phase6", "adaptive_green_max_bonus", 8.0))
            self.timer += min(max_bonus, queue * bonus * dt)
        durations = self._durations()
        if self.phase in ("a_green", "b_green"):
            limit = durations["green"]
        elif self.phase in ("a_yellow", "b_yellow"):
            limit = durations["yellow"]
        else:
            limit = durations["walk"]
        self.timer += dt
        if self.timer < limit:
            return
        self.timer = 0.0
        phases = self._phases()
        if self.phase not in phases:
            self.phase = phases[0]
            return
        index = phases.index(self.phase)
        self.phase = phases[(index + 1) % len(phases)]

    def to_dict(self) -> dict[str, Any]:
        approaches = []
        for ap in self.approaches:
            state = self.state_for(int(ap["edge_id"])) or "red"
            approaches.append(
                {
                    "edge_id": int(ap["edge_id"]),
                    "axis": int(ap["axis"]),
                    "state": state,
                    "angle": round(float(ap["angle"]), 4),
                }
            )
        summary = self.summary_state()
        return {
            "node_id": self.node_id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "state": summary,
            "phase": self.phase,
            "pedestrian": summary == "walk",
            "approaches": approaches,
        }


class SignalController:
    """네트워크 교차로에 접근로별 신호를 배치·갱신."""

    def __init__(self) -> None:
        self.lights: dict[int, JunctionSignal] = {}

    def sync_network(self, nodes: dict[int, dict[str, Any]], edges: list[dict[str, Any]]) -> None:
        """차수≥min인 노드에 신호를 두고 접근로를 갱신합니다."""
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
                self.lights[node_id] = JunctionSignal(node_id, float(node["x"]), float(node["y"]))
            else:
                self.lights[node_id].x = float(node["x"])
                self.lights[node_id].y = float(node["y"])
            self.lights[node_id].sync_approaches(edges)

        for node_id in list(self.lights.keys()):
            if node_id not in active:
                del self.lights[node_id]

    def tick(self, dt: float, *, approach_counts: dict[tuple[int, int], int] | None = None) -> None:
        adaptive = bool(get_variable("phase6", "adaptive_traffic_lights", True))
        counts = approach_counts or {}
        for light in self.lights.values():
            queue = 0
            if light.phase == "a_green":
                active_axis = 0
            elif light.phase == "b_green":
                active_axis = 1
            else:
                active_axis = None
            if active_axis is not None:
                for ap in light.approaches:
                    if int(ap["axis"]) != active_axis:
                        continue
                    queue += int(counts.get((light.node_id, int(ap["edge_id"])), 0))
            light.tick(dt, queue=queue, adaptive=adaptive)

    def get_light(self, node_id: int) -> JunctionSignal | None:
        return self.lights.get(int(node_id))

    def state_for(self, node_id: int, edge_id: int) -> str | None:
        light = self.get_light(node_id)
        if light is None:
            return None
        return light.state_for(edge_id)

    def to_dict(self) -> list[dict[str, Any]]:
        return [light.to_dict() for light in self.lights.values()]
