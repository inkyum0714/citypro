"""도로별·격자 공간 인덱스 (충돌·추종 검사 비용 절감)."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.vehicle import Vehicle


class VehicleSpatialIndex:
    """Edge ID별 버킷 + 균일 격자(근처 차량 질의)."""

    def __init__(self, cell_size: float = 64.0) -> None:
        self._by_road: dict[int, list[Vehicle]] = defaultdict(list)
        self._grid: dict[tuple[int, int], list[Vehicle]] = defaultdict(list)
        self._cell = float(cell_size)

    def rebuild(self, vehicles: list[Vehicle]) -> None:
        self._by_road.clear()
        self._grid.clear()
        cell = self._cell
        for vehicle in vehicles:
            if vehicle.finished:
                continue
            self._by_road[int(vehicle.road_id)].append(vehicle)
            cx = int(vehicle.x // cell)
            cy = int(vehicle.y // cell)
            self._grid[(cx, cy)].append(vehicle)

    def vehicles_on_road(self, road_id: int) -> list[Vehicle]:
        return self._by_road.get(int(road_id), [])

    def nearby(self, x: float, y: float, radius: float) -> list[Vehicle]:
        """원형 반경 안의 차량. 격자만 순회하므로 O(k)."""
        cell = self._cell
        r = max(0.0, float(radius))
        x0 = int((x - r) // cell)
        x1 = int((x + r) // cell)
        y0 = int((y - r) // cell)
        y1 = int((y + r) // cell)
        r2 = r * r
        out: list[Vehicle] = []
        grid = self._grid
        for cx in range(x0, x1 + 1):
            for cy in range(y0, y1 + 1):
                bucket = grid.get((cx, cy))
                if not bucket:
                    continue
                for vehicle in bucket:
                    dx = vehicle.x - x
                    dy = vehicle.y - y
                    if dx * dx + dy * dy <= r2:
                        out.append(vehicle)
        return out
