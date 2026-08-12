"""퀘스트·상점·업적 정의."""

from __future__ import annotations

from typing import Any

from utils.variables import get_variable


def xp_for_level(level: int) -> int:
    base = int(get_variable("engagement", "xp_per_level_base", 100))
    return base * max(1, level)


def daily_quest_templates() -> list[dict[str, Any]]:
    return [
        {
            "id": "build_roads",
            "label": "도로 건설",
            "description": "도로 3개 건설",
            "target": 3,
            "metric": "roads_built",
            "reward_coins": 40,
            "reward_xp": 25,
        },
        {
            "id": "move_traffic",
            "label": "교통 흐름",
            "description": "완주 15회 달성",
            "target": 15,
            "metric": "trips_completed",
            "reward_coins": 50,
            "reward_xp": 35,
        },
        {
            "id": "golden_hour",
            "label": "골든 아워",
            "description": "원활한 흐름(평균속도↑) 40초 유지",
            "target": 40,
            "metric": "golden_flow_seconds",
            "reward_coins": 55,
            "reward_xp": 40,
        },
        {
            "id": "accident_cleanup",
            "label": "사고 클린업",
            "description": "교통사고 2건 정리(경찰/견인)",
            "target": 2,
            "metric": "accidents_cleared",
            "reward_coins": 60,
            "reward_xp": 35,
        },
        {
            "id": "bus_stops",
            "label": "버스 정류장",
            "description": "정류장 2개 개설",
            "target": 2,
            "metric": "bus_stops_built",
            "reward_coins": 45,
            "reward_xp": 30,
        },
        {
            "id": "cargo_sort",
            "label": "화물 분류",
            "description": "트럭 화물 3건 분류",
            "target": 3,
            "metric": "cargo_classified",
            "reward_coins": 50,
            "reward_xp": 30,
        },
    ]


def shop_items() -> list[dict[str, Any]]:
    return [
        {
            "id": "booster_xp_1h",
            "name": "XP 부스터 (1시간)",
            "description": "획득 XP 1.5배",
            "price_coins": 80,
            "type": "booster",
            "booster_key": "xp_multiplier",
            "booster_value": 1.5,
            "duration_hours": 1,
        },
        {
            "id": "cosmetic_neon",
            "name": "네온 도로 스킨",
            "description": "도로·차량 네온 테마",
            "price_coins": 150,
            "type": "cosmetic",
            "cosmetic_id": "neon",
        },
        {
            "id": "cosmetic_sunset",
            "name": "선셋 스킨",
            "description": "따뜻한 저녁 톤 UI",
            "price_coins": 120,
            "type": "cosmetic",
            "cosmetic_id": "sunset",
        },
        {
            "id": "save_slot_extra",
            "name": "도시 저장 슬롯 +1",
            "description": "영구 저장 공간 확장",
            "price_coins": 200,
            "type": "save_slot",
            "slots_added": 1,
        },
    ]


def pro_plan_catalog() -> dict[str, Any]:
    return {
        "id": "cityflow_pro",
        "name": "CityFlow PRO",
        "price_display": "₩4,900/월",
        "benefits": [
            "광고 제거",
            "도시 저장 5슬롯",
            "VIP 이벤트·고급 분석",
            "일일 보너스 코인 2배",
            "주간 리더보드 PRO 배지",
        ],
    }


def achievements_catalog() -> list[dict[str, Any]]:
    return [
        {"id": "first_road", "label": "첫 도로", "metric": "roads_built", "target": 1, "reward_coins": 20},
        {"id": "mayor", "label": "도시 설계자", "metric": "roads_built", "target": 10, "reward_coins": 100},
        {"id": "traffic_master", "label": "교통 마스터", "metric": "trips_completed", "target": 100, "reward_coins": 150},
        {"id": "week_warrior", "label": "7일 연속 접속", "metric": "streak_days", "target": 7, "reward_coins": 200},
        {"id": "bus_network", "label": "버스 노선왕", "metric": "bus_stops_built", "target": 5, "reward_coins": 80},
        {"id": "cargo_master", "label": "물류 마스터", "metric": "cargo_classified", "target": 15, "reward_coins": 100},
        {"id": "golden_keeper", "label": "골든 키퍼", "metric": "golden_flow_seconds", "target": 300, "reward_coins": 120},
        {"id": "rescue_hero", "label": "구조 영웅", "metric": "accidents_cleared", "target": 10, "reward_coins": 90},
        {"id": "stage_clearer", "label": "스테이지 클리어", "metric": "stages_cleared", "target": 2, "reward_coins": 150},
    ]
