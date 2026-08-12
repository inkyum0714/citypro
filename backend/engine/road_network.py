"""Phase 2: Node–Edge 도로 네트워크."""

from __future__ import annotations

from typing import Any

from engine.network_node import node_dict
from utils.math_helpers import (
    clamp,
    distance,
    lerp_point,
    project_point_to_segment,
    segment_intersection,
)
from utils.variables import get_variable

ROAD_TYPES: dict[str, dict[str, Any]] = {
    "city": {"lanes": 2, "speed_limit": 50, "width": 18},
    "highway": {"lanes": 3, "speed_limit": 90, "width": 26},
    "residential": {"lanes": 1, "speed_limit": 30, "width": 14},
}

# add_road가 반환하는 분할 이벤트: 기존 Edge 위 차량 progress 재매핑용
SplitRemap = dict[str, Any]


class RoadNetwork:
    """
    교통 네트워크: Node(교차로)와 Edge(도로).

    Edge는 ``start_node_id``·``end_node_id``를 가지며, 좌표는 노드에서 파생됩니다.
    끝점이 다른 도로에 닿거나 교차하면 자동으로 연결·분할합니다.
    """

    def __init__(self) -> None:
        self.nodes: dict[int, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self._next_node_id = 1
        self._next_road_id = 1
        self.last_remaps: list[SplitRemap] = []

    @property
    def roads(self) -> list[dict[str, Any]]:
        """하위 호환: Edge 목록 alias."""
        return self.edges

    def _merge_tolerance(self) -> float:
        return float(get_variable("phase2", "node_merge_distance", 14.0))

    def _touch_distance(self) -> float:
        return float(
            get_variable(
                "phase2",
                "road_touch_distance",
                get_variable("phase2", "node_merge_distance", 14.0),
            )
        )

    def _min_split_t(self) -> float:
        return float(get_variable("phase2", "min_split_progress", 0.05))

    def get_node(self, node_id: int) -> dict[str, Any] | None:
        return self.nodes.get(node_id)

    def find_node_near(self, x: float, y: float) -> int | None:
        """좌표에 가장 가까운 기존 노드 ID(허용 거리 이내). 없으면 None."""
        tol = self._merge_tolerance()
        best_id: int | None = None
        best_d = tol
        for node in self.nodes.values():
            d = distance([x, y], [node["x"], node["y"]])
            if d <= best_d:
                best_d = d
                best_id = int(node["id"])
        return best_id

    def create_node(self, x: float, y: float) -> int:
        """새 교차로 노드를 등록합니다."""
        node_id = self._next_node_id
        self._next_node_id += 1
        self.nodes[node_id] = node_dict(node_id, x, y)
        return node_id

    def resolve_node(self, x: float, y: float) -> int:
        """근처 노드 병합 또는 신규 생성."""
        existing = self.find_node_near(x, y)
        if existing is not None:
            return existing
        return self.create_node(x, y)

    def _make_edge(
        self,
        start_node_id: int,
        end_node_id: int,
        *,
        road_type: str,
        lanes: int,
        speed_limit: float,
        width: float,
        edge_id: int | None = None,
        bidirectional: bool = False,
        pair_id: int | None = None,
    ) -> dict[str, Any]:
        start_node = self.nodes[start_node_id]
        end_node = self.nodes[end_node_id]
        if edge_id is None:
            edge_id = self._next_road_id
            self._next_road_id += 1
        return {
            "id": edge_id,
            "start_node_id": start_node_id,
            "end_node_id": end_node_id,
            "start": [start_node["x"], start_node["y"]],
            "end": [end_node["x"], end_node["y"]],
            "type": road_type,
            "lanes": lanes,
            "speed_limit": speed_limit,
            "width": width,
            "bidirectional": bool(bidirectional),
            "pair_id": pair_id,
        }

    def split_edge_at_progress(self, edge_id: int, t: float) -> tuple[int, SplitRemap | None]:
        """
        Edge를 진행률 t에서 분할하고 중간 노드 ID를 반환합니다.

        Returns:
            (node_id, remap_event or None)
        """
        edge = self.get_road(edge_id)
        if edge is None:
            raise ValueError(f"unknown edge {edge_id}")

        min_t = self._min_split_t()
        t = clamp(t, 0.0, 1.0)
        if t <= min_t:
            return int(edge["start_node_id"]), None
        if t >= 1.0 - min_t:
            return int(edge["end_node_id"]), None

        px, py = lerp_point(edge["start"], edge["end"], t)
        existing = self.find_node_near(px, py)
        if existing is not None and existing in (edge["start_node_id"], edge["end_node_id"]):
            return int(existing), None
        if existing is not None:
            node_id = int(existing)
            t2, _ = project_point_to_segment(
                self.nodes[node_id]["x"],
                self.nodes[node_id]["y"],
                edge["start"],
                edge["end"],
            )
            t = t2
            if t <= min_t:
                return int(edge["start_node_id"]), None
            if t >= 1.0 - min_t:
                return int(edge["end_node_id"]), None
        else:
            node_id = self.create_node(px, py)

        start_id = int(edge["start_node_id"])
        end_id = int(edge["end_node_id"])
        # 이미 이 노드로 연결된 경우 중복 분할 방지
        if node_id in (start_id, end_id):
            return node_id, None
        for other in self.edges:
            if other["id"] == edge_id:
                continue
            ends = {other["start_node_id"], other["end_node_id"]}
            if node_id in ends and (start_id in ends or end_id in ends):
                # 이미 부분 연결 — 원본만 교체
                pass

        edge_a = self._make_edge(
            start_id,
            node_id,
            road_type=str(edge["type"]),
            lanes=int(edge["lanes"]),
            speed_limit=float(edge["speed_limit"]),
            width=float(edge["width"]),
            edge_id=int(edge["id"]),
            bidirectional=bool(edge.get("bidirectional", False)),
            pair_id=edge.get("pair_id"),
        )
        edge_b = self._make_edge(
            node_id,
            end_id,
            road_type=str(edge["type"]),
            lanes=int(edge["lanes"]),
            speed_limit=float(edge["speed_limit"]),
            width=float(edge["width"]),
            bidirectional=bool(edge.get("bidirectional", False)),
            pair_id=edge.get("pair_id"),
        )
        self.edges = [e for e in self.edges if e["id"] != edge_id]
        self.edges.append(edge_a)
        self.edges.append(edge_b)
        remap: SplitRemap = {
            "old_id": edge_id,
            "t": t,
            "edge_a": edge_a,
            "edge_b": edge_b,
        }
        return node_id, remap

    def _snap_endpoint(self, x: float, y: float, remaps: list[SplitRemap]) -> int:
        """끝점을 근처 노드 또는 도로 위 T자 접점으로 스냅."""
        near = self.find_node_near(x, y)
        if near is not None:
            return near

        touch = self._touch_distance()
        min_t = self._min_split_t()
        best: tuple[float, int, float] | None = None  # dist, edge_id, t
        for edge in list(self.edges):
            t, dist = project_point_to_segment(x, y, edge["start"], edge["end"])
            if dist > touch:
                continue
            if t <= min_t or t >= 1.0 - min_t:
                # 끝점 쪽이면 해당 노드로
                node_id = edge["start_node_id"] if t <= 0.5 else edge["end_node_id"]
                if distance([x, y], [self.nodes[node_id]["x"], self.nodes[node_id]["y"]]) <= touch:
                    return int(node_id)
                continue
            if best is None or dist < best[0]:
                best = (dist, int(edge["id"]), t)

        if best is not None:
            _, edge_id, t = best
            node_id, remap = self.split_edge_at_progress(edge_id, t)
            if remap is not None:
                remaps.append(remap)
            return node_id

        return self.create_node(x, y)

    def _infer_road_type(self, start_pt: list[float], end_pt: list[float]) -> str:
        length = distance(start_pt, end_pt)
        if length > 220:
            return "highway"
        if length > 90:
            return "city"
        return "residential"

    def _connect_crossings(self, new_edge_id: int, remaps: list[SplitRemap]) -> None:
        """새 Edge가 기존 Edge와 교차하면 양쪽을 분할해 연결."""
        min_t = self._min_split_t()
        # 여러 교차가 있을 수 있어 반복
        for _ in range(8):
            new_edge = self.get_road(new_edge_id)
            if new_edge is None:
                return
            hit: tuple[int, float, float] | None = None
            for other in list(self.edges):
                if other["id"] == new_edge_id:
                    continue
                shared = {
                    new_edge["start_node_id"],
                    new_edge["end_node_id"],
                } & {other["start_node_id"], other["end_node_id"]}
                if shared:
                    continue
                inter = segment_intersection(
                    new_edge["start"],
                    new_edge["end"],
                    other["start"],
                    other["end"],
                    endpoint_eps=min_t,
                )
                if inter is None:
                    continue
                t_new, t_other = inter
                hit = (int(other["id"]), t_new, t_other)
                break
            if hit is None:
                return
            other_id, t_new, t_other = hit
            node_id, remap_other = self.split_edge_at_progress(other_id, t_other)
            if remap_other is not None:
                remaps.append(remap_other)
            # new_edge가 이미 분할됐을 수 있음 — 현재 new_edge_id 기준으로 재분할
            current = self.get_road(new_edge_id)
            if current is None:
                # id가 유지되는 전반부일 수 있음
                return
            # 교차점이 이미 노드로 들어갔으면 new edge도 그 노드에서 분할
            node = self.nodes[node_id]
            t_proj, _ = project_point_to_segment(
                node["x"], node["y"], current["start"], current["end"]
            )
            _, remap_new = self.split_edge_at_progress(new_edge_id, t_proj if t_proj else t_new)
            if remap_new is not None:
                remaps.append(remap_new)
                # 이후 교차 검사는 새 조각(후반부)에도 적용
                new_edge_id = int(remap_new["edge_b"]["id"])

    def add_road(
        self,
        start: list[float],
        end: list[float],
        road_type: str | None = None,
        *,
        lanes: int | None = None,
        bidirectional: bool = False,
    ) -> dict[str, Any] | None:
        """
        Edge(도로) 추가. 끝점·T자 접점·교차점을 자동 연결합니다.

        Args:
            lanes: 차선 수 (1~6). None이면 도로 유형 기본값.
            bidirectional: True면 반대 방향 Edge도 함께 생성 (왕복).

        Returns:
            생성된 정방향 Edge. 너무 짧으면 None.
        """
        remaps: list[SplitRemap] = []
        start_node_id = self._snap_endpoint(float(start[0]), float(start[1]), remaps)
        end_node_id = self._snap_endpoint(float(end[0]), float(end[1]), remaps)

        if start_node_id == end_node_id:
            self.last_remaps = remaps
            return None

        start_node = self.nodes[start_node_id]
        end_node = self.nodes[end_node_id]
        start_pt = [start_node["x"], start_node["y"]]
        end_pt = [end_node["x"], end_node["y"]]
        if distance(start_pt, end_pt) < 8.0:
            self.last_remaps = remaps
            return None

        # 동일 방향 Edge만 중복으로 본다
        for existing in self.edges:
            if (
                existing["start_node_id"] == start_node_id
                and existing["end_node_id"] == end_node_id
            ):
                self.last_remaps = remaps
                return existing

        if road_type is None:
            road_type = self._infer_road_type(start_pt, end_pt)

        spec = ROAD_TYPES.get(road_type, ROAD_TYPES["city"])
        lane_count = int(spec["lanes"] if lanes is None else lanes)
        lane_count = max(1, min(6, lane_count))
        # 차선 수에 비례해 도로 폭 조정
        base_width = float(spec["width"])
        width = max(base_width, lane_count * 9.0)

        edge = self._make_edge(
            start_node_id,
            end_node_id,
            road_type=road_type,
            lanes=lane_count,
            speed_limit=float(spec["speed_limit"]),
            width=width,
            bidirectional=bool(bidirectional),
        )
        self.edges.append(edge)

        if bidirectional:
            # 이미 반대 방향이 있으면 재사용, 없으면 생성
            reverse = None
            for existing in self.edges:
                if (
                    existing["start_node_id"] == end_node_id
                    and existing["end_node_id"] == start_node_id
                ):
                    reverse = existing
                    break
            if reverse is None:
                reverse = self._make_edge(
                    end_node_id,
                    start_node_id,
                    road_type=road_type,
                    lanes=lane_count,
                    speed_limit=float(spec["speed_limit"]),
                    width=width,
                    bidirectional=True,
                    pair_id=int(edge["id"]),
                )
                self.edges.append(reverse)
            edge["pair_id"] = int(reverse["id"])
            reverse["pair_id"] = int(edge["id"])
            reverse["bidirectional"] = True

        self._connect_crossings(int(edge["id"]), remaps)
        if bidirectional and edge.get("pair_id"):
            pair = self.get_road(int(edge["pair_id"]))
            if pair is not None:
                self._connect_crossings(int(pair["id"]), remaps)
        self.last_remaps = remaps
        return self.get_road(int(edge["id"])) or edge

    def get_road(self, road_id: int) -> dict[str, Any] | None:
        for edge in self.edges:
            if edge["id"] == road_id:
                return edge
        return None

    def edges_from_node(self, node_id: int) -> list[dict[str, Any]]:
        """노드에서 출발하거나 도착하는 Edge."""
        return [
            e
            for e in self.edges
            if e["start_node_id"] == node_id or e["end_node_id"] == node_id
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": list(self.nodes.values()),
            "roads": self.edges,
        }

    def export_snapshot(self) -> dict[str, Any]:
        """도시 저장용 네트워크 스냅샷."""
        return {
            "nodes": list(self.nodes.values()),
            "roads": self.edges,
            "_next_node_id": self._next_node_id,
            "_next_road_id": self._next_road_id,
        }

    def load_snapshot(self, snapshot: dict[str, Any]) -> None:
        """저장된 네트워크 복원."""
        self.nodes = {int(n["id"]): n for n in snapshot.get("nodes", [])}
        self.edges = list(snapshot.get("roads", []))
        self._next_node_id = int(snapshot.get("_next_node_id", max(self.nodes.keys(), default=0) + 1))
        self._next_road_id = int(
            snapshot.get("_next_road_id", max((e.get("id", 0) for e in self.edges), default=0) + 1)
        )
