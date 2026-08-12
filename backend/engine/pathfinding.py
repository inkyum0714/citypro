"""Phase 4: Node–Edge 그래프 경로 탐색 (Dijkstra)."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Any

from utils.math_helpers import road_length


@dataclass(frozen=True)
class RouteStep:
    """한 Edge 구간 주행 (방향 포함)."""

    edge_id: int
    forward: bool
    from_node_id: int
    to_node_id: int


def _build_adjacency(edges: list[dict[str, Any]]) -> dict[int, list[tuple[int, int, bool, float]]]:
    """노드별 (이웃, edge_id, forward, cost) 인접 리스트."""
    adj: dict[int, list[tuple[int, int, bool, float]]] = {}
    for edge in edges:
        start = int(edge["start_node_id"])
        end = int(edge["end_node_id"])
        cost = road_length(edge)
        adj.setdefault(start, []).append((end, int(edge["id"]), True, cost))
        adj.setdefault(end, []).append((start, int(edge["id"]), False, cost))
    return adj


def dijkstra_route(
    edges: list[dict[str, Any]],
    start_node_id: int,
    goal_node_id: int,
) -> list[RouteStep]:
    """
    start→goal 최단 경로 (양방향 Edge).

    Returns:
        RouteStep 리스트. 경로 없으면 빈 리스트.
    """
    if start_node_id == goal_node_id:
        return []

    adj = _build_adjacency(edges)
    dist: dict[int, float] = {start_node_id: 0.0}
    prev: dict[int, tuple[int, int, bool] | None] = {start_node_id: None}
    heap: list[tuple[float, int]] = [(0.0, start_node_id)]

    while heap:
        d, node = heapq.heappop(heap)
        if d > dist.get(node, float("inf")):
            continue
        if node == goal_node_id:
            break
        for neighbor, edge_id, forward, cost in adj.get(node, []):
            nd = d + cost
            if nd < dist.get(neighbor, float("inf")):
                dist[neighbor] = nd
                prev[neighbor] = (node, edge_id, forward)
                heapq.heappush(heap, (nd, neighbor))

    if goal_node_id not in prev:
        return []

    steps: list[RouteStep] = []
    cur = goal_node_id
    while cur != start_node_id:
        parent_info = prev.get(cur)
        if parent_info is None:
            return []
        from_node, edge_id, forward = parent_info
        steps.append(
            RouteStep(
                edge_id=edge_id,
                forward=forward,
                from_node_id=from_node,
                to_node_id=cur,
            )
        )
        cur = from_node
    steps.reverse()
    return steps
