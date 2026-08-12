"""Phase 3: MOBIL 차선 변경 의사결정."""

from __future__ import annotations

from typing import TYPE_CHECKING

from engine.idm import compute_idm_acceleration, net_bumper_gap
from utils.math_helpers import road_length
from utils.variables import get_variable

if TYPE_CHECKING:
    from engine.traffic_manager import TrafficManager
    from engine.vehicle import Vehicle


class MobilLaneAdvisor:
    """
    MOBIL (Minimizing Overall Braking Induced by Lane changes).

    Δa = (a_n - a_c) + p · (a_o' - a_o) > a_thr, 새 후방차 a_t > -b_safe.
    """

    def __init__(self, manager: TrafficManager) -> None:
        self.manager = manager

    def _cfg(self) -> dict[str, float]:
        return {
            "politeness": float(get_variable("phase3", "mobil_politeness", 0.25)),
            "threshold": float(get_variable("phase3", "mobil_accel_threshold", 0.2)),
            "b_safe": float(get_variable("phase3", "mobil_b_safe", 14.0)),
        }

    def _in_lane(self, vehicle: Vehicle, lane_index: int) -> list[Vehicle]:
        segment = self.manager._segments.get(vehicle.road_id)
        if segment is None:
            return []
        return [
            o
            for o in segment.vehicles
            if o.id != vehicle.id and not o.finished and o.lane_index == lane_index
        ]

    def _lead_ahead(self, vehicle: Vehicle, lane_index: int, *, after_progress: float | None = None) -> Vehicle | None:
        ref = vehicle.progress if after_progress is None else after_progress
        ahead = [o for o in self._in_lane(vehicle, lane_index) if o.progress > ref]
        if not ahead:
            return None
        return min(ahead, key=lambda o: o.progress)

    def _follower_behind(self, vehicle: Vehicle, lane_index: int) -> Vehicle | None:
        behind = [o for o in self._in_lane(vehicle, lane_index) if o.progress < vehicle.progress]
        if not behind:
            return None
        return max(behind, key=lambda o: o.progress)

    def _road_gap(self, rear: Vehicle, front: Vehicle) -> float:
        return max(0.0, (front.progress - rear.progress) * road_length(rear.road))

    def _idm_follow(
        self,
        ego_speed: float,
        desired: float,
        lead: Vehicle | None,
        follower: Vehicle,
    ) -> float:
        if lead is None:
            return compute_idm_acceleration(follower.current_speed, desired)
        gap = self._road_gap(follower, lead)
        net_s = net_bumper_gap(gap, follower.length, lead.length)
        return compute_idm_acceleration(
            follower.current_speed,
            desired,
            net_gap=net_s,
            lead_speed=lead.current_speed,
        )

    def _ego_idm(self, ego: Vehicle, lane_index: int, desired: float) -> float:
        lead = self._lead_ahead(ego, lane_index)
        if lead is None:
            return compute_idm_acceleration(ego.current_speed, desired)
        gap = self._road_gap(ego, lead)
        net_s = net_bumper_gap(gap, ego.length, lead.length)
        return compute_idm_acceleration(
            ego.current_speed,
            desired,
            net_gap=net_s,
            lead_speed=lead.current_speed,
        )

    def evaluate_change_to(
        self,
        ego: Vehicle,
        target_lane: int,
        desired_speed: float,
    ) -> tuple[bool, float]:
        """
        MOBIL 기준 target_lane 변경 타당성.

        Returns:
            (허용 여부, incentive Δa)
        """
        current_lane = ego.lane_index
        if target_lane == current_lane:
            return False, 0.0

        cfg = self._cfg()
        a_c = self._ego_idm(ego, current_lane, desired_speed)
        a_n = self._ego_idm(ego, target_lane, desired_speed)

        old_follower = self._follower_behind(ego, current_lane)
        if old_follower is not None:
            a_o = self._idm_follow(ego.current_speed, desired_speed, ego, old_follower)
            lead_after = self._lead_ahead(ego, current_lane)
            a_o_after = self._idm_follow(
                lead_after.current_speed if lead_after else 0.0,
                desired_speed,
                lead_after,
                old_follower,
            )
        else:
            a_o = 0.0
            a_o_after = 0.0

        new_follower = self._follower_behind(ego, target_lane)
        if new_follower is not None:
            a_t = self._idm_follow(ego.current_speed, desired_speed, ego, new_follower)
            if a_t < -cfg["b_safe"]:
                return False, 0.0
        else:
            a_t = 0.0

        incentive = (a_n - a_c) + cfg["politeness"] * (a_o_after - a_o)
        return incentive > cfg["threshold"], incentive

    def best_adjacent_lane(self, ego: Vehicle, desired_speed: float) -> int | None:
        """인접 차선 중 MOBIL incentive가 가장 큰 차선."""
        lanes = int(ego.road.get("lanes", 1))
        best_lane: int | None = None
        best_score = float("-inf")

        for delta in (1, -1):
            target = ego.lane_index + delta
            if target < 0 or target >= lanes:
                continue
            ok, score = self.evaluate_change_to(ego, target, desired_speed)
            if ok and score > best_score:
                best_score = score
                best_lane = target
        return best_lane
