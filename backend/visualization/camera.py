"""Phase 5: Pygame 뷰어용 2D 카메라."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from utils.variables import get_variable


@dataclass
class ViewCamera:
    """월드 중심(x, y) + zoom 기반 뷰."""

    x: float = 480.0
    y: float = 320.0
    zoom: float = 1.0

    def clamp_zoom(self, value: float) -> float:
        zmin = float(get_variable("phase5", "camera_min_zoom", 0.15))
        zmax = float(get_variable("phase5", "camera_max_zoom", 4.0))
        return max(zmin, min(zmax, value))

    def screen_to_world(self, sx: float, sy: float, width: int, height: int) -> tuple[float, float]:
        wx = (sx - width / 2) / self.zoom + self.x
        wy = (sy - height / 2) / self.zoom + self.y
        return wx, wy

    def world_to_screen(self, wx: float, wy: float, width: int, height: int) -> tuple[float, float]:
        sx = (wx - self.x) * self.zoom + width / 2
        sy = (wy - self.y) * self.zoom + height / 2
        return sx, sy

    def zoom_at(self, sx: float, sy: float, width: int, height: int, factor: float) -> None:
        bx, by = self.screen_to_world(sx, sy, width, height)
        self.zoom = self.clamp_zoom(self.zoom * factor)
        ax, ay = self.screen_to_world(sx, sy, width, height)
        self.x += bx - ax
        self.y += by - ay

    def pan(self, dx_screen: float, dy_screen: float) -> None:
        self.x -= dx_screen / self.zoom
        self.y -= dy_screen / self.zoom

    def fit_state(self, state: dict[str, Any], width: int, height: int) -> None:
        roads = state.get("roads") or []
        nodes = state.get("nodes") or []
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")

        def include(x: float, y: float) -> None:
            nonlocal min_x, min_y, max_x, max_y
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

        for road in roads:
            include(float(road["start"][0]), float(road["start"][1]))
            include(float(road["end"][0]), float(road["end"][1]))
        for node in nodes:
            include(float(node["x"]), float(node["y"]))

        if not roads and not nodes:
            self.x = width / 2
            self.y = height / 2
            self.zoom = 1.0
            return

        pad = float(get_variable("phase5", "camera_fit_padding", 80.0))
        min_x -= pad
        min_y -= pad
        max_x += pad
        max_y += pad
        world_w = max(max_x - min_x, 120.0)
        world_h = max(max_y - min_y, 120.0)
        self.x = (min_x + max_x) / 2
        self.y = (min_y + max_y) / 2
        self.zoom = self.clamp_zoom(min(width / world_w, height / world_h) * 0.92)
