"""Phase 6: 시뮬레이션 지표 수집·내보내기."""

from __future__ import annotations

import csv
import io
from collections import deque
from typing import Any

from utils.variables import get_variable


class AnalyticsCollector:
    """통행량·대기·혼잡 시계열 및 도로별 정체 구간."""

    def __init__(self) -> None:
        self._samples: deque[dict[str, Any]] = deque(
            maxlen=int(get_variable("phase6", "analytics_max_samples", 360))
        )
        self._completed_window = 0
        self._wait_accum = 0.0
        self._wait_samples = 0
        self._last_sample_time = 0.0
        self.sample_interval = float(get_variable("phase6", "analytics_sample_interval", 1.0))

    def reset(self) -> None:
        self._samples.clear()
        self._completed_window = 0
        self._wait_accum = 0.0
        self._wait_samples = 0
        self._last_sample_time = 0.0

    def on_trip_completed(self) -> None:
        self._completed_window += 1

    def on_wait_sample(self, wait_dt: float) -> None:
        if wait_dt <= 0:
            return
        self._wait_accum += wait_dt
        self._wait_samples += 1

    def tick(
        self,
        sim_time: float,
        manager: Any,
        *,
        completed_this_frame: int,
    ) -> None:
        """주기적으로 스냅샷 저장."""
        self._completed_window += completed_this_frame
        if sim_time - self._last_sample_time < self.sample_interval:
            return
        self._last_sample_time = sim_time

        per_road: dict[int, int] = {}
        for vehicle in manager.vehicles:
            per_road[vehicle.road_id] = per_road.get(vehicle.road_id, 0) + 1

        congested_roads = [
            {"road_id": road_id, "vehicles": count}
            for road_id, count in per_road.items()
            if count >= int(get_variable("phase6", "congested_road_vehicle_threshold", 5))
        ]
        avg_wait = (self._wait_accum / self._wait_samples) if self._wait_samples else 0.0
        throughput_per_min = self._completed_window * (60.0 / max(self.sample_interval, 0.1))

        self._samples.append(
            {
                "sim_time": round(sim_time, 1),
                "throughput_per_min": round(throughput_per_min, 2),
                "avg_wait_seconds": round(avg_wait, 2),
                "active_vehicles": len(manager.vehicles),
                "congestion_level": round(manager._congestion_level(), 3),
                "congested_roads": congested_roads,
            }
        )
        self._completed_window = 0
        self._wait_accum = 0.0
        self._wait_samples = 0

    def to_dict(self) -> dict[str, Any]:
        samples = list(self._samples)
        latest = samples[-1] if samples else {}
        return {
            "latest": latest,
            "series": samples[-30:],
            "summary": {
                "sample_count": len(samples),
                "peak_throughput_per_min": max((s.get("throughput_per_min", 0) for s in samples), default=0),
                "peak_congestion": max((s.get("congestion_level", 0) for s in samples), default=0),
            },
        }

    def export_csv(self) -> str:
        """CSV 문자열."""
        output = io.StringIO()
        fieldnames = [
            "sim_time",
            "throughput_per_min",
            "avg_wait_seconds",
            "active_vehicles",
            "congestion_level",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in self._samples:
            writer.writerow(row)
        return output.getvalue()
