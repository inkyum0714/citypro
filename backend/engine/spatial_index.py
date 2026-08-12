"""Phase 6: 도로별 차량 인덱스 (충돌·추종 검사 비용 절감)."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.vehicle import Vehicle


class VehicleSpatialIndex:
    """Edge ID별 active 차량 버킷."""

    def __init__(self) -> None:
        self._by_road: dict[int, list[Vehicle]] = defaultdict(list)

    def rebuild(self, vehicles: list[Vehicle]) -> None:
        self._by_road.clear()
        for vehicle in vehicles:
            if vehicle.finished:
                continue
            self._by_road[int(vehicle.road_id)].append(vehicle)

    def vehicles_on_road(self, road_id: int) -> list[Vehicle]:
        return self._by_road.get(int(road_id), [])
