"""Phase 2/3: 차선 변경 FSM + MOBIL 의사결정."""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.mobil import MobilLaneAdvisor
from utils.math_helpers import road_length
from utils.variables import get_variable

if TYPE_CHECKING:
    from engine.traffic_manager import TrafficManager
    from engine.vehicle import Vehicle


class LaneController:
    """MOBIL로 차선 변경 필요성 판단 후 방향지시·통행 방해 검사·이동."""

    def __init__(self, manager: TrafficManager) -> None:
        self.manager = manager
        self.mobil = MobilLaneAdvisor(manager)

    def _min_signal_time(self) -> float:
        return float(get_variable("phase2", "turn_signal_min_seconds", 0.45))

    def _lane_change_duration(self) -> float:
        return float(get_variable("phase2", "lane_change_duration_seconds", 0.55))

    def _min_target_lane_gap_front(self) -> float:
        return float(get_variable("phase2", "min_target_lane_gap_front", 22.0))

    def _min_target_lane_gap_rear(self) -> float:
        return float(get_variable("phase2", "min_target_lane_gap_rear", 18.0))

    def _use_mobil(self) -> bool:
        return bool(get_variable("phase3", "use_mobil", True))

    def _lead_vehicle(self, vehicle: Vehicle, lane_index: int) -> Vehicle | None:
        segment = self.manager._segments.get(vehicle.road_id)
        if segment is None:
            return None
        ahead = [
            other
            for other in segment.vehicles
            if other.id != vehicle.id
            and not other.finished
            and other.lane_index == lane_index
            and other.progress > vehicle.progress
        ]
        if not ahead:
            return None
        return min(ahead, key=lambda o: o.progress)

    def _gap_to_vehicle(self, vehicle: Vehicle, other: Vehicle, *, front: bool) -> float:
        length = road_length(vehicle.road)
        if front:
            return max(0.0, (other.progress - vehicle.progress) * length)
        return max(0.0, (vehicle.progress - other.progress) * length)

    def _target_lane_safe(self, vehicle: Vehicle, target_lane: int) -> bool:
        """Phase 2: 기하학적 전·후방 간격(통행 방해 금지)."""
        segment = self.manager._segments.get(vehicle.road_id)
        if segment is None:
            return False

        min_front = self._min_target_lane_gap_front()
        min_rear = self._min_target_lane_gap_rear()
        vehicle_len = vehicle.length

        for other in segment.vehicles:
            if other.id == vehicle.id or other.finished or other.lane_index != target_lane:
                continue
            if other.progress >= vehicle.progress:
                gap = self._gap_to_vehicle(vehicle, other, front=True)
                if gap < min_front + vehicle_len * 0.3:
                    return False
            else:
                gap = self._gap_to_vehicle(vehicle, other, front=False)
                if gap < min_rear + other.length * 0.3:
                    return False
        return True

    def _desired_speed(self, vehicle: Vehicle, speed_factor: float) -> float:
        road_limit = float(vehicle.road.get("speed_limit", 50))
        return min(vehicle.base_speed, road_limit) * speed_factor

    def _pick_target_lane(self, vehicle: Vehicle, speed_factor: float) -> int | None:
        if self._use_mobil():
            return self.mobil.best_adjacent_lane(vehicle, self._desired_speed(vehicle, speed_factor))

        lanes = int(vehicle.road.get("lanes", 1))
        if lanes < 2 or vehicle.lane_index >= lanes - 1:
            return None
        trigger = float(get_variable("phase2", "lane_change_headway_trigger", 42.0))
        lead = self._lead_vehicle(vehicle, vehicle.lane_index)
        if lead is None:
            return None
        gap = self.manager._lead_gap_in_lane(vehicle)
        if gap >= trigger or lead.current_speed >= vehicle.max_speed * 0.92:
            return None
        return vehicle.lane_index + 1

    def tick(self, vehicle: Vehicle, dt: float, *, speed_factor: float = 1.0) -> None:
        """
        차량별 차선 변경 상태 머신을 한 틱 진행합니다.

        Args:
            vehicle: 대상 차량.
            dt: 시뮬레이션 dt.
            speed_factor: MOBIL 목표 속도용 이벤트 배율.
        """
        if vehicle.lane_change_active:
            vehicle.lane_change_elapsed += dt
            duration = self._lane_change_duration()
            vehicle.lane_change_progress = min(1.0, vehicle.lane_change_elapsed / max(duration, 1e-6))
            if vehicle.lane_change_progress >= 1.0:
                vehicle.lane_index = vehicle.lane_change_target_lane
                vehicle.lane_change_active = False
                vehicle.lane_change_progress = 0.0
                vehicle.lane_change_elapsed = 0.0
                vehicle.turn_signal = None
                vehicle.lane_change_target_lane = None
                vehicle.state = "moving"
            vehicle.refresh_world_position()
            return

        if vehicle.turn_signal is not None:
            vehicle.signal_elapsed += dt
            if vehicle.signal_elapsed >= self._min_signal_time():
                target = vehicle.lane_change_target_lane
                if target is not None and self._target_lane_safe(vehicle, target):
                    vehicle.lane_change_active = True
                    vehicle.lane_change_from_lane = vehicle.lane_index
                    vehicle.lane_change_elapsed = 0.0
                    vehicle.lane_change_progress = 0.0
                    vehicle.state = "lane_change"
                else:
                    vehicle.turn_signal = None
                    vehicle.signal_elapsed = 0.0
                    vehicle.lane_change_target_lane = None
                    vehicle.state = "moving"
            vehicle.refresh_world_position()
            return

        if vehicle.finished or vehicle.lane_change_active:
            return

        target_lane = self._pick_target_lane(vehicle, speed_factor)
        if target_lane is None:
            return
        if not self._target_lane_safe(vehicle, target_lane):
            return

        direction = "left" if target_lane > vehicle.lane_index else "right"
        vehicle.turn_signal = direction
        vehicle.signal_elapsed = 0.0
        vehicle.lane_change_target_lane = target_lane
        vehicle.state = "signaling"
