"""Phase 5: Pygame 실시간 시뮬레이션 뷰어 (WebSocket)."""

from __future__ import annotations

import json
import math
import sys
import threading
from pathlib import Path
from typing import Any

# backend 패키지 import 경로
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from utils.variables import get_variable
from visualization.camera import ViewCamera

try:
    import pygame
except ImportError as exc:  # pragma: no cover
    raise SystemExit("pygame이 필요합니다: pip install pygame") from exc

try:
    from simple_websocket import Client as WsClient
except ImportError as exc:  # pragma: no cover
    raise SystemExit("simple-websocket이 필요합니다 (requirements.txt 참고).") from exc


def _hex_to_rgb(value: str, fallback: tuple[int, int, int] = (220, 220, 220)) -> tuple[int, int, int]:
    if not value or not str(value).startswith("#"):
        return fallback
    try:
        num = int(str(value)[1:], 16)
        return (num >> 16) & 255, (num >> 8) & 255, num & 255
    except ValueError:
        return fallback


class PygameViewer:
    """Flask WebSocket 상태를 Pygame 창에 렌더."""

    def __init__(self, ws_url: str, width: int, height: int) -> None:
        self.ws_url = ws_url
        self.width = width
        self.height = height
        self.camera = ViewCamera()
        self.state: dict[str, Any] = {"roads": [], "vehicles": [], "nodes": [], "traffic_lights": []}
        self.state_lock = threading.Lock()
        self.connected = False
        self._fit_once = False
        self._panning = False
        self._pan_last: tuple[int, int] | None = None

    def _ws_loop(self) -> None:
        try:
            with WsClient.connect(self.ws_url) as ws:
                self.connected = True
                while True:
                    raw = ws.receive()
                    if raw is None:
                        break
                    payload = json.loads(raw)
                    if payload.get("type") == "state":
                        with self.state_lock:
                            self.state = payload.get("data") or {}
        except Exception:
            self.connected = False

    def run(self) -> None:
        pygame.init()
        pygame.display.set_caption("CityFlow — Pygame Viewer")
        screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        clock = pygame.time.Clock()
        font = pygame.font.SysFont("malgungothic,segoeui,arial", 14)

        thread = threading.Thread(target=self._ws_loop, daemon=True)
        thread.start()

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.width, self.height = event.size
                    screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
                elif event.type == pygame.MOUSEWHEEL:
                    mx, my = pygame.mouse.get_pos()
                    factor = 1.1 if event.y > 0 else 0.9
                    self.camera.zoom_at(mx, my, self.width, self.height, factor)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button in (2, 3):
                        self._panning = True
                        self._pan_last = event.pos
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button in (2, 3):
                        self._panning = False
                        self._pan_last = None
                elif event.type == pygame.MOUSEMOTION and self._panning and self._pan_last:
                    dx = event.pos[0] - self._pan_last[0]
                    dy = event.pos[1] - self._pan_last[1]
                    self.camera.pan(dx, dy)
                    self._pan_last = event.pos
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_f:
                        with self.state_lock:
                            self.camera.fit_state(self.state, self.width, self.height)
                    elif event.key == pygame.K_r:
                        self.camera.x = self.width / 2
                        self.camera.y = self.height / 2
                        self.camera.zoom = 1.0

            with self.state_lock:
                state = dict(self.state)
            if not self._fit_once and state.get("roads"):
                self.camera.fit_state(state, self.width, self.height)
                self._fit_once = True

            screen.fill((11, 16, 32))
            self._draw_scene(screen, state)

            status = "연결됨" if self.connected else "연결 대기…"
            hud = f"{status} | 줌 {int(self.camera.zoom * 100)}% | F:맞춤 R:리셋 | 휠·우클릭 드래그"
            screen.blit(font.render(hud, True, (148, 163, 184)), (12, self.height - 28))

            pygame.display.flip()
            fps = int(get_variable("phase5", "pygame_target_fps", 60))
            clock.tick(fps)

        pygame.quit()

    def _draw_scene(self, screen: pygame.Surface, state: dict[str, Any]) -> None:
        for road in state.get("roads") or []:
            self._draw_road(screen, road)
        for light in state.get("traffic_lights") or []:
            self._draw_light(screen, light)
        for vehicle in state.get("vehicles") or []:
            self._draw_vehicle(screen, vehicle)

    def _w2s(self, x: float, y: float) -> tuple[float, float]:
        return self.camera.world_to_screen(x, y, self.width, self.height)

    def _draw_road(self, screen: pygame.Surface, road: dict[str, Any]) -> None:
        sx, sy = self._w2s(road["start"][0], road["start"][1])
        ex, ey = self._w2s(road["end"][0], road["end"][1])
        width = float(road.get("width", 18)) * self.camera.zoom
        pygame.draw.line(screen, (30, 41, 59), (sx, sy), (ex, ey), max(2, int(width + 6 * self.camera.zoom)))
        pygame.draw.line(screen, (71, 85, 105), (sx, sy), (ex, ey), max(1, int(width)))

    def _draw_light(self, screen: pygame.Surface, light: dict[str, Any]) -> None:
        colors = {"green": (34, 197, 94), "yellow": (234, 179, 8), "red": (239, 68, 68)}
        x, y = self._w2s(light["x"], light["y"] - 16)
        color = colors.get(light.get("state"), (239, 68, 68))
        pygame.draw.circle(screen, (15, 23, 42), (int(x), int(y)), max(4, int(7 * self.camera.zoom)))
        pygame.draw.circle(screen, color, (int(x), int(y)), max(3, int(4.5 * self.camera.zoom)))

    def _draw_vehicle(self, screen: pygame.Surface, vehicle: dict[str, Any]) -> None:
        x, y = self._w2s(vehicle["x"], vehicle["y"])
        length = float(vehicle.get("length", 14)) * self.camera.zoom
        width = float(vehicle.get("width", 8)) * self.camera.zoom
        angle = float(vehicle.get("angle", 0))
        color = _hex_to_rgb(vehicle.get("color", "#ffffff"))

        surf = pygame.Surface((max(4, int(length)), max(3, int(width))), pygame.SRCALPHA)
        surf.fill(color)
        rotated = pygame.transform.rotate(surf, -math.degrees(angle))
        rect = rotated.get_rect(center=(int(x), int(y)))
        screen.blit(rotated, rect)


def main() -> None:
    host = str(get_variable("phase5", "pygame_ws_host", "127.0.0.1"))
    port = int(get_variable("main", "flask_port", 5000))
    ws_url = f"ws://{host}:{port}/ws"
    width = int(get_variable("phase5", "pygame_window_width", 1280))
    height = int(get_variable("phase5", "pygame_window_height", 720))
    PygameViewer(ws_url, width, height).run()


if __name__ == "__main__":
    main()
