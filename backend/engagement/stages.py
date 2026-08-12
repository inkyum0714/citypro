"""스테이지형 시드 맵 챌린지 정의."""

from __future__ import annotations

from typing import Any


def _road(rid: int, start: list[float], end: list[float], *, start_n: int, end_n: int, road_type: str = "city") -> dict[str, Any]:
    specs = {
        "city": {"lanes": 2, "speed_limit": 50, "width": 18},
        "highway": {"lanes": 3, "speed_limit": 90, "width": 26},
        "residential": {"lanes": 1, "speed_limit": 30, "width": 14},
    }
    spec = specs.get(road_type, specs["city"])
    return {
        "id": rid,
        "start_node_id": start_n,
        "end_node_id": end_n,
        "start": start,
        "end": end,
        "type": road_type,
        **spec,
    }


def _node(nid: int, x: float, y: float) -> dict[str, Any]:
    return {"id": nid, "x": x, "y": y}


def _network(nodes: list[dict], roads: list[dict], next_node: int, next_road: int) -> dict[str, Any]:
    return {
        "nodes": nodes,
        "roads": roads,
        "_next_node_id": next_node,
        "_next_road_id": next_road,
    }


def stage_catalog() -> list[dict[str, Any]]:
    """플레이 가능한 스테이지 목록 (시드 맵 + 목표 + 보상)."""
    return [
        {
            "id": "stage_01_first_flow",
            "name": "스테이지 1 · 첫 흐름",
            "description": "L자 도로에서 차량 5대가 목적지에 도착하세요.",
            "difficulty": 1,
            "reward_coins": 80,
            "reward_xp": 40,
            "goals": [
                {"metric": "trips_completed", "target": 5, "label": "완주 5회"},
            ],
            "network": _network(
                [
                    _node(1, 80, 280),
                    _node(2, 380, 280),
                    _node(3, 380, 80),
                ],
                [
                    _road(1, [80, 280], [380, 280], start_n=1, end_n=2),
                    _road(2, [380, 280], [380, 80], start_n=2, end_n=3),
                ],
                4,
                3,
            ),
            "hints": ["자동 차량 생성을 켜고 흐름을 관찰하세요."],
        },
        {
            "id": "stage_02_junction",
            "name": "스테이지 2 · 교차로 구축",
            "description": "십자 도로를 확장하고, 버스 정류장 1개를 세우세요.",
            "difficulty": 2,
            "reward_coins": 120,
            "reward_xp": 55,
            "goals": [
                {"metric": "roads_built", "target": 2, "label": "도로 2개 추가"},
                {"metric": "bus_stops_built", "target": 1, "label": "정류장 1개"},
                {"metric": "trips_completed", "target": 8, "label": "완주 8회"},
            ],
            "network": _network(
                [
                    _node(1, 100, 300),
                    _node(2, 300, 300),
                    _node(3, 500, 300),
                    _node(4, 300, 100),
                    _node(5, 300, 500),
                ],
                [
                    _road(1, [100, 300], [300, 300], start_n=1, end_n=2),
                    _road(2, [300, 300], [500, 300], start_n=2, end_n=3),
                    _road(3, [300, 100], [300, 300], start_n=4, end_n=2),
                    _road(4, [300, 300], [300, 500], start_n=2, end_n=5),
                ],
                6,
                5,
            ),
            "hints": ["하단 도구에서 정류장 배치를 사용하세요."],
        },
        {
            "id": "stage_03_cargo_line",
            "name": "스테이지 3 · 화물 노선",
            "description": "트럭 화물을 분류하고 골든 아워를 유지하세요.",
            "difficulty": 3,
            "reward_coins": 160,
            "reward_xp": 70,
            "goals": [
                {"metric": "cargo_classified", "target": 3, "label": "화물 분류 3건"},
                {"metric": "golden_flow_seconds", "target": 25, "label": "골든 흐름 25초"},
                {"metric": "trips_completed", "target": 10, "label": "완주 10회"},
            ],
            "network": _network(
                [
                    _node(1, 60, 200),
                    _node(2, 260, 200),
                    _node(3, 460, 200),
                    _node(4, 660, 200),
                    _node(5, 260, 40),
                    _node(6, 460, 360),
                ],
                [
                    _road(1, [60, 200], [260, 200], start_n=1, end_n=2, road_type="highway"),
                    _road(2, [260, 200], [460, 200], start_n=2, end_n=3, road_type="highway"),
                    _road(3, [460, 200], [660, 200], start_n=3, end_n=4, road_type="highway"),
                    _road(4, [260, 40], [260, 200], start_n=5, end_n=2),
                    _road(5, [460, 200], [460, 360], start_n=3, end_n=6),
                ],
                7,
                6,
            ),
            "hints": ["트럭을 관찰 도구로 클릭한 뒤 화물을 분류하세요.", "차량이 원활히 달리면 골든 아워가 쌓입니다."],
        },
        {
            "id": "stage_04_rescue",
            "name": "스테이지 4 · 구조 작전",
            "description": "혼잡한 도시에서 사고를 정리하고 정류장을 운영하세요.",
            "difficulty": 4,
            "reward_coins": 200,
            "reward_xp": 90,
            "goals": [
                {"metric": "accidents_cleared", "target": 2, "label": "사고 정리 2건"},
                {"metric": "bus_stops_built", "target": 2, "label": "정류장 2개"},
                {"metric": "trips_completed", "target": 12, "label": "완주 12회"},
            ],
            "network": _network(
                [
                    _node(1, 80, 80),
                    _node(2, 280, 80),
                    _node(3, 480, 80),
                    _node(4, 80, 280),
                    _node(5, 280, 280),
                    _node(6, 480, 280),
                    _node(7, 280, 480),
                ],
                [
                    _road(1, [80, 80], [280, 80], start_n=1, end_n=2),
                    _road(2, [280, 80], [480, 80], start_n=2, end_n=3),
                    _road(3, [80, 280], [280, 280], start_n=4, end_n=5),
                    _road(4, [280, 280], [480, 280], start_n=5, end_n=6),
                    _road(5, [80, 80], [80, 280], start_n=1, end_n=4),
                    _road(6, [280, 80], [280, 280], start_n=2, end_n=5),
                    _road(7, [480, 80], [480, 280], start_n=3, end_n=6),
                    _road(8, [280, 280], [280, 480], start_n=5, end_n=7),
                ],
                8,
                9,
            ),
            "hints": ["사고를 유도하려면 차량을 많이 배치하세요.", "경찰/견인으로 현장을 정리하세요."],
        },
    ]


def get_stage(stage_id: str) -> dict[str, Any] | None:
    return next((s for s in stage_catalog() if s["id"] == stage_id), None)


def stage_public(stage: dict[str, Any], *, completed: bool = False, progress: dict[str, float] | None = None) -> dict[str, Any]:
    progress = progress or {}
    goals_out = []
    for g in stage.get("goals") or []:
        metric = g["metric"]
        target = float(g["target"])
        cur = float(progress.get(metric, 0))
        goals_out.append(
            {
                **g,
                "progress": min(target, cur),
                "completed": cur >= target,
            }
        )
    return {
        "id": stage["id"],
        "name": stage["name"],
        "description": stage["description"],
        "difficulty": stage.get("difficulty", 1),
        "reward_coins": stage.get("reward_coins", 0),
        "reward_xp": stage.get("reward_xp", 0),
        "goals": goals_out,
        "hints": stage.get("hints") or [],
        "completed": completed,
        "all_goals_met": bool(goals_out) and all(g["completed"] for g in goals_out),
    }
