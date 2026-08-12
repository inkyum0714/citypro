"""로그인 사용자별 TrafficManager 격리 레지스트리."""

from __future__ import annotations

import threading
import time
from typing import Callable

from engine.traffic_manager import TrafficManager


class SimulationRegistry:
    """세션(login_id)마다 독립 시뮬레이션을 유지합니다."""

    def __init__(self, *, idle_ttl_seconds: float = 1800.0) -> None:
        self._lock = threading.RLock()
        self._sims: dict[str, TrafficManager] = {}
        self._last_touch: dict[str, float] = {}
        self._idle_ttl = idle_ttl_seconds

    def get(self, login_id: str) -> TrafficManager:
        login_id = login_id.strip().lower()
        with self._lock:
            if login_id not in self._sims:
                self._sims[login_id] = TrafficManager()
            self._last_touch[login_id] = time.time()
            return self._sims[login_id]

    def touch(self, login_id: str) -> None:
        login_id = login_id.strip().lower()
        with self._lock:
            if login_id in self._sims:
                self._last_touch[login_id] = time.time()

    def items(self) -> list[tuple[str, TrafficManager]]:
        with self._lock:
            return list(self._sims.items())

    def prune_idle(self, *, keep: set[str] | None = None) -> None:
        keep = keep or set()
        now = time.time()
        with self._lock:
            for login_id in list(self._sims.keys()):
                if login_id in keep:
                    continue
                last = self._last_touch.get(login_id, 0.0)
                if now - last > self._idle_ttl:
                    self._sims.pop(login_id, None)
                    self._last_touch.pop(login_id, None)

    def with_manager(self, login_id: str, fn: Callable[[TrafficManager], object]) -> object:
        manager = self.get(login_id)
        with self._lock:
            return fn(manager)
