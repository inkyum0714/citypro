"""차량 목적지·Edge 전환. 기본: 각 도로 끝 = 도착 → 소멸."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from engine.pathfinding import RouteStep, dijkstra_route
from utils.math_helpers import road_length
from utils.variables import get_variable

if TYPE_CHECKING:
    from engine.traffic_manager import TrafficManager
    from engine.vehicle import Vehicle


class RoutingService:
    """차량 목적지·RouteStep 큐 및 Edge 전환."""

    def __init__(self, manager: TrafficManager) -> None:
        self.manager = manager

    def _enabled(self) -> bool:
        """네트워크 다중 Edge 경로 탐색 사용 여부."""
        return bool(get_variable("phase4", "use_routing", False))

    def _edge_end_destination(self) -> bool:
        """독립 도로의 끝 지점을 도착지로 쓸지 (기본 True)."""
        return bool(get_variable("phase4", "edge_end_is_destination", True))

    def pick_destination(self, origin_node_id: int) -> int | None:
        nodes = list(self.manager.road_network.nodes.keys())
        if len(nodes) < 2:
            return None
        candidates = [n for n in nodes if n != origin_node_id]
        if not candidates:
            return None
        return random.choice(candidates)

    def build_route(self, start_node_id: int, goal_node_id: int) -> list[RouteStep]:
        return dijkstra_route(self.manager.road_network.edges, start_node_id, goal_node_id)

    def assign_route(self, vehicle: Vehicle, *, goal_node_id: int | None = None) -> None:
        """스폰·재경로 시 목적지 부여.

        edge_end_is_destination 모드: 현재 도로 끝(exit)이 도착지 → 도착 시 소멸.
        """
        # 기본: 이 도로의 끝 = 도착
        if self._edge_end_destination() or not self._enabled():
            vehicle.destination_node_id = int(vehicle.exit_node_id)
            vehicle.route_steps = [
                RouteStep(
                    edge_id=int(vehicle.road_id),
                    forward=bool(vehicle.travel_forward),
                    from_node_id=int(vehicle.entry_node_id),
                    to_node_id=int(vehicle.exit_node_id),
                )
            ]
            vehicle.route_step_index = 0
            return

        origin = vehicle.entry_node_id
        dest = goal_node_id if goal_node_id is not None else self.pick_destination(origin)
        if dest is None:
            vehicle.destination_node_id = int(vehicle.exit_node_id)
            vehicle.route_steps = []
            vehicle.route_step_index = 0
            return

        steps = self.build_route(origin, dest)
        if not steps:
            steps = [
                RouteStep(
                    edge_id=int(vehicle.road_id),
                    forward=bool(vehicle.travel_forward),
                    from_node_id=int(vehicle.entry_node_id),
                    to_node_id=int(vehicle.exit_node_id),
                )
            ]
            vehicle.destination_node_id = int(vehicle.exit_node_id)
        else:
            vehicle.destination_node_id = dest

        vehicle.route_steps = steps
        vehicle.route_step_index = 0
        self._align_vehicle_to_current_step(vehicle)

    def _align_vehicle_to_current_step(self, vehicle: Vehicle) -> None:
        if not vehicle.route_steps:
            return
        step = vehicle.route_steps[vehicle.route_step_index]
        edge = self.manager.road_network.get_road(step.edge_id)
        if edge is None:
            return
        vehicle.road = edge
        vehicle.road_id = int(edge["id"])
        vehicle.travel_forward = step.forward
        vehicle.entry_node_id = step.from_node_id
        vehicle.exit_node_id = step.to_node_id
        vehicle.refresh_world_position()

    def advance_at_end(self, vehicle: Vehicle) -> None:
        """Edge 끝(progress≥1) 도달 시 도착 소멸 또는 다음 Edge."""
        # 도로 끝 = 도착 → 즉시 소멸
        if self._edge_end_destination() or not self._enabled() or not vehicle.route_steps:
            vehicle.finished = True
            vehicle.state = "arrived"
            return

        vehicle.progress = 1.0
        at_node = vehicle.exit_node_id
        if at_node == vehicle.destination_node_id:
            vehicle.finished = True
            vehicle.state = "arrived"
            return

        vehicle.route_step_index += 1
        if vehicle.route_step_index >= len(vehicle.route_steps):
            vehicle.finished = True
            vehicle.state = "arrived"
            return

        step = vehicle.route_steps[vehicle.route_step_index]
        if step.from_node_id != at_node:
            rerouted = self.try_reroute_from_node(vehicle, at_node)
            if not rerouted:
                vehicle.finished = True
                vehicle.state = "arrived"
            return

        edge = self.manager.road_network.get_road(step.edge_id)
        if edge is None:
            vehicle.finished = True
            vehicle.state = "arrived"
            return

        vehicle.road = edge
        vehicle.road_id = int(edge["id"])
        vehicle.travel_forward = step.forward
        vehicle.entry_node_id = step.from_node_id
        vehicle.exit_node_id = step.to_node_id
        vehicle.progress = 0.0
        vehicle.turn_signal = None
        vehicle.lane_change_active = False
        vehicle.state = "moving"
        vehicle.refresh_world_position()
        self.manager._mark_segments_dirty()

    def try_reroute_from_node(self, vehicle: Vehicle, node_id: int) -> bool:
        """교차로에서 경로 불일치 시 목적지까지 경로 재탐색."""
        if self._edge_end_destination() or not self._enabled() or vehicle.destination_node_id is None:
            return False
        steps = self.build_route(node_id, int(vehicle.destination_node_id))
        if not steps:
            return False
        vehicle.route_steps = steps
        vehicle.route_step_index = 0
        vehicle.progress = 0.0
        self._align_vehicle_to_current_step(vehicle)
        self.manager._mark_segments_dirty()
        return True

    def reroute_network_changed(self) -> None:
        """새 도로 연결 후 진행 중 차량 경로 갱신."""
        if self._edge_end_destination() or not self._enabled():
            # 도로 끝 도착 모드: 현재 Edge 끝만 목적지로 재설정
            for vehicle in self.manager.vehicles:
                if vehicle.finished:
                    continue
                vehicle.destination_node_id = int(vehicle.exit_node_id)
            return
        for vehicle in self.manager.vehicles:
            if vehicle.finished or vehicle.destination_node_id is None:
                continue
            origin = int(vehicle.exit_node_id if vehicle.progress >= 0.95 else vehicle.entry_node_id)
            steps = self.build_route(origin, int(vehicle.destination_node_id))
            if steps:
                vehicle.route_steps = steps
                vehicle.route_step_index = 0
                self._align_vehicle_to_current_step(vehicle)
        self.manager._mark_segments_dirty()

    def distance_to_stop_line(self, vehicle: Vehicle) -> float:
        """현재 위치에서 정지선까지 거리(길이 단위)."""
        length = road_length(vehicle.road)
        offset = float(get_variable("phase4", "stop_line_offset_from_exit", 22.0))
        stop_frac = offset / max(length, 1.0)
        stop_progress = max(0.0, 1.0 - stop_frac)
        if vehicle.progress >= stop_progress:
            return 0.0
        return (stop_progress - vehicle.progress) * length
