"""Phase 1: 1차원 도로 선분 및 차량 목록 관리."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from utils.math_helpers import road_length

if TYPE_CHECKING:
    from engine.vehicle import Vehicle


class RoadSegment:
    """
    1차원 선분 형태의 도로.

    진행 방향을 0(시작) ~ length(끝) 스칼라 좌표로 표현합니다.
    """

    def __init__(self, road_id: int, length: float, road: dict[str, Any] | None = None) -> None:
        """
        Args:
            road_id: 도로 식별자.
            length: 선분 길이(시뮬레이션 단위).
            road: 2D 렌더링용 도로 dict(선택). 없으면 최소 메타만 사용.
        """
        self.road_id = road_id
        self.length = max(0.0, length)
        self.road = road or {"id": road_id, "start": [0, 0], "end": [length, 0]}
        self.vehicles: list[Vehicle] = []

    @classmethod
    def from_road_dict(cls, road: dict[str, Any]) -> RoadSegment:
        """2D 도로 dict로부터 1D 세그먼트를 생성합니다."""
        return cls(road_id=int(road["id"]), length=road_length(road), road=road)

    def add_vehicle(self, vehicle: Vehicle) -> None:
        """세그먼트 위 차량 목록에 추가합니다."""
        if vehicle not in self.vehicles:
            self.vehicles.append(vehicle)

    def remove_vehicle(self, vehicle: Vehicle) -> None:
        """차량을 목록에서 제거합니다."""
        if vehicle in self.vehicles:
            self.vehicles.remove(vehicle)

    def clear_vehicles(self) -> None:
        """모든 차량 참조를 비웁니다."""
        self.vehicles.clear()

    def vehicles_by_progress(self) -> list[Vehicle]:
        """진행률(progress) 기준 정렬된 차량 리스트."""
        return sorted(self.vehicles, key=lambda v: v.progress)

    def lead_gap_for(self, vehicle: Vehicle) -> float:
        """
        동일 도로에서 전방 차량까지의 간격(길이 단위).

        Args:
            vehicle: 기준 차량.

        Returns:
            앞차가 없으면 설정상의 큰 값, 있으면 거리(길이 단위).
        """
        from utils.variables import get_variable

        no_obstacle = float(get_variable("vehicle", "lead_gap_no_obstacle", 999.0))
        ahead = [
            other
            for other in self.vehicles
            if other.id != vehicle.id
            and not other.finished
            and other.lane_index == vehicle.lane_index
            and other.progress > vehicle.progress
        ]
        if not ahead:
            return no_obstacle
        nearest = min(ahead, key=lambda other: other.progress)
        gap_progress = nearest.progress - vehicle.progress
        return gap_progress * self.length
