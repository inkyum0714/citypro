"""기하 유틸(거리, 보간, 차선 오프셋)."""

from __future__ import annotations

import math
from typing import Any, Sequence

from utils.variables import get_variable


def distance(a: Sequence[float], b: Sequence[float]) -> float:
    """두 점 사이 유클리드 거리."""
    return math.hypot(b[0] - a[0], b[1] - a[1])


def road_length(road: dict[str, Any]) -> float:
    """도로 Edge 길이."""
    return distance(road["start"], road["end"])


def lerp_point(start: Sequence[float], end: Sequence[float], t: float) -> list[float]:
    """선분 위 보간점."""
    return [
        start[0] + (end[0] - start[0]) * t,
        start[1] + (end[1] - start[1]) * t,
    ]


def road_angle(road: dict[str, Any]) -> float:
    """진행 방향 각도(라디안)."""
    dx = road["end"][0] - road["start"][0]
    dy = road["end"][1] - road["start"][1]
    return math.atan2(dy, dx)


def road_normal(road: dict[str, Any]) -> tuple[float, float]:
    """진행 방향 기준 좌측 단위 법선 (우-hand 통행에서 추월 차선 쪽)."""
    length = road_length(road)
    if length < 1e-6:
        return (0.0, 1.0)
    dx = road["end"][0] - road["start"][0]
    dy = road["end"][1] - road["start"][1]
    return (-dy / length, dx / length)


def lane_lateral_offset(road: dict[str, Any], lane_index: int) -> float:
    """
    차선 index에 따른 중심선 수직 오프셋.

    lane 0 = 우측(느린 차선), 큰 index = 좌측(추월 차선).
    """
    lanes = max(1, int(road.get("lanes", 1)))
    width = float(road.get("width", 18))
    lane_width = width / lanes
    center_index = (lanes - 1) / 2.0
    scale = float(get_variable("phase2", "lane_offset_scale", 0.88))
    return (lane_index - center_index) * lane_width * scale


def travel_geom_progress(progress: float, travel_forward: bool) -> float:
    """주행 progress → 기하 보간 t (start→end)."""
    return progress if travel_forward else (1.0 - progress)


def travel_angle(road: dict[str, Any], travel_forward: bool) -> float:
    """주행 방향 각도."""
    base = road_angle(road)
    return base if travel_forward else base + math.pi


def travel_left_normal(road: dict[str, Any], travel_forward: bool) -> tuple[float, float]:
    """주행 방향 기준 좌측 단위 법선."""
    ang = travel_angle(road, travel_forward)
    return (-math.sin(ang), math.cos(ang))


def position_on_road(
    road: dict[str, Any],
    progress: float,
    lane_index: int,
    *,
    lane_blend: float = 1.0,
    from_lane_index: int | None = None,
    travel_forward: bool = True,
) -> tuple[float, float]:
    """
    progress·차선(및 차선 변경 보간)에 따른 월드 좌표.

    Args:
        lane_blend: 0=from_lane, 1=target lane (lane_change 중).
        from_lane_index: 보간 시작 차선. None이면 lane_index.
        travel_forward: False면 end→start 주행.
    """
    t = travel_geom_progress(progress, travel_forward)
    base = lerp_point(road["start"], road["end"], t)
    nx, ny = travel_left_normal(road, travel_forward)
    from_lane = lane_index if from_lane_index is None else from_lane_index
    to_lane = lane_index
    if lane_blend < 1.0 and from_lane_index is not None:
        off_from = lane_lateral_offset(road, from_lane_index)
        off_to = lane_lateral_offset(road, to_lane)
        offset = off_from + (off_to - off_from) * lane_blend
    else:
        offset = lane_lateral_offset(road, lane_index)
    return base[0] + nx * offset, base[1] + ny * offset


def clamp(value: float, minimum: float, maximum: float) -> float:
    """값을 [minimum, maximum] 구간으로 제한."""
    return max(minimum, min(maximum, value))


def project_point_to_segment(
    px: float,
    py: float,
    start: Sequence[float],
    end: Sequence[float],
) -> tuple[float, float]:
    """
    점을 선분에 투영.

    Returns:
        (t along segment 0..1, perpendicular distance to segment)
    """
    x1, y1 = start[0], start[1]
    x2, y2 = end[0], end[1]
    dx, dy = x2 - x1, y2 - y1
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-9:
        return 0.0, math.hypot(px - x1, py - y1)
    t = clamp(((px - x1) * dx + (py - y1) * dy) / len_sq, 0.0, 1.0)
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return t, math.hypot(px - proj_x, py - proj_y)


def segment_intersection(
    a_start: Sequence[float],
    a_end: Sequence[float],
    b_start: Sequence[float],
    b_end: Sequence[float],
    *,
    endpoint_eps: float = 0.02,
) -> tuple[float, float] | None:
    """
    두 선분의 고유 교점이 있으면 (t_a, t_b) 반환 (각 선분 파라미터 0..1).

    끝점 근처 교점은 None (노드 병합으로 처리).
    """
    ax, ay = a_start[0], a_start[1]
    bx, by = a_end[0], a_end[1]
    cx, cy = b_start[0], b_start[1]
    dx, dy = b_end[0], b_end[1]
    abx, aby = bx - ax, by - ay
    cdx, cdy = dx - cx, dy - cy
    den = abx * cdy - aby * cdx
    if abs(den) < 1e-9:
        return None
    acx, acy = cx - ax, cy - ay
    t = (acx * cdy - acy * cdx) / den
    u = (acx * aby - acy * abx) / den
    if t <= endpoint_eps or t >= 1.0 - endpoint_eps:
        return None
    if u <= endpoint_eps or u >= 1.0 - endpoint_eps:
        return None
    return t, u


def closest_road_at_point(
    roads: list[dict[str, Any]],
    px: float,
    py: float,
    *,
    max_distance: float = 40.0,
) -> tuple[dict[str, Any], float, float] | None:
    """
    월드 좌표에 가장 가까운 Edge.

    Returns:
        (road, progress 0..1, distance) 또는 None
    """
    best: tuple[dict[str, Any], float, float] | None = None
    best_dist = max_distance
    for road in roads:
        t, dist = project_point_to_segment(px, py, road["start"], road["end"])
        if dist < best_dist:
            best_dist = dist
            length = road_length(road)
            progress = (t * length) / length if length > 1e-6 else 0.0
            progress = clamp(progress, 0.02, 0.98)
            best = (road, progress, dist)
    return best
