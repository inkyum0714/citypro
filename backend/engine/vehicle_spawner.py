"""Phase 2: 도로(Edge) 시작점 차량 생성."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from utils.variables import get_variable

if TYPE_CHECKING:
    from engine.traffic_manager import TrafficManager
    from engine.vehicle import Vehicle


class VehicleSpawner:
    """Edge 시작 노드(progress≈0)에서 차선별 여유가 있을 때만 스폰합니다."""

    def __init__(self, manager: TrafficManager) -> None:
        self.manager = manager

    def _spawn_clearance(self) -> float:
        return float(get_variable("phase2", "spawn_clearance_distance", 28.0))

    def _edge_spawn_weight(self, edge: dict[str, Any]) -> float:
        """길이에 비례한 스폰 가중치."""
        from utils.math_helpers import road_length

        min_weight = float(get_variable("phase2", "spawn_min_edge_weight", 0.1))
        return max(min_weight, road_length(edge))

    def pick_spawn_edge(self) -> dict[str, Any] | None:
        """스폰 후보 Edge 하나를 가중치 랜덤으로 선택."""
        roads = self.manager.road_network.roads
        if not roads:
            return None
        weights = [self._edge_spawn_weight(r) for r in roads]
        return random.choices(roads, weights=weights, k=1)[0]

    def _lane_blocked_at_start(self, road_id: int, lane_index: int, vehicles: list[Vehicle]) -> bool:
        clearance = self._spawn_clearance()
        start_progress_max = float(get_variable("phase2", "spawn_progress_window", 0.08))
        for vehicle in vehicles:
            if vehicle.finished or vehicle.road_id != road_id or vehicle.lane_index != lane_index:
                continue
            if vehicle.progress > start_progress_max:
                continue
            from utils.math_helpers import road_length

            road = vehicle.road
            dist = vehicle.progress * road_length(road)
            # 앞차 길이와 공간 차지를 반영한 여유 거리
            need = clearance + vehicle.length * 0.45 * float(getattr(vehicle, "space_occupancy", 1.0) or 1.0)
            if dist < need:
                return True
        return False

    def pick_spawn_lane(self, edge: dict[str, Any]) -> int | None:
        """시작 구간이 비어 있는 차선 index. 없으면 None."""
        lanes = int(edge.get("lanes", 1))
        free = [
            lane
            for lane in range(lanes)
            if not self._lane_blocked_at_start(edge["id"], lane, self.manager.vehicles)
        ]
        if not free:
            return None
        return random.choice(free)

    def try_spawn(self, vehicle_type: str | None = None) -> Vehicle | None:
        """
        한 틱 스폰 시도.

        Returns:
            생성된 차량 또는 스폰 불가 시 None.
        """
        edge = self.pick_spawn_edge()
        if edge is None:
            return None
        lane = self.pick_spawn_lane(edge)
        if lane is None:
            return None
        return self.manager.create_vehicle_on_edge(edge, lane_index=lane, vehicle_type=vehicle_type)

    def try_spawn_on_edge(
        self,
        road_id: int,
        *,
        lane_index: int | None = None,
        progress: float | None = None,
        vehicle_type: str | None = None,
    ) -> Vehicle | None:
        """지정 Edge·차선·progress에 차량 생성 (유저 조종)."""
        edge = next((r for r in self.manager.road_network.roads if r["id"] == road_id), None)
        if edge is None:
            return None
        prog = 0.0 if progress is None else float(progress)
        prog = max(0.0, min(0.98, prog))
        lane = lane_index
        if lane is None:
            lane = self.pick_spawn_lane(edge)
            if lane is None:
                lane = 0
        lanes = int(edge.get("lanes", 1))
        lane = max(0, min(lanes - 1, int(lane)))
        if self._lane_blocked_at_start(edge["id"], lane, self.manager.vehicles) and prog < 0.12:
            return None
        return self.manager.create_vehicle_on_edge(
            edge, lane_index=lane, progress=prog, vehicle_type=vehicle_type
        )

    def try_spawn_at_world(
        self,
        x: float,
        y: float,
        *,
        vehicle_type: str | None = None,
    ) -> Vehicle | None:
        """클릭 좌표 근처 도로에 차량 생성."""
        from utils.math_helpers import closest_road_at_point

        max_dist = float(get_variable("traffic_manager", "spawn_click_max_distance", 42.0))
        hit = closest_road_at_point(self.manager.road_network.roads, x, y, max_distance=max_dist)
        if hit is None:
            return None
        edge, progress, _ = hit
        lane = self.pick_spawn_lane(edge)
        if lane is None:
            lane = 0
        return self.manager.create_vehicle_on_edge(
            edge, lane_index=lane, progress=progress, vehicle_type=vehicle_type
        )
