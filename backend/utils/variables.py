"""프로젝트 전역 상수(all_variable.json) 로더."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
VARIABLES_PATH = BASE_DIR / "all_variable.json"


@lru_cache(maxsize=1)
def load_all_variables() -> dict[str, Any]:
    """
    all_variable.json을 읽어 딕셔너리로 반환합니다.

    Returns:
        JSON 루트 객체. 파일이 없으면 빈 dict.
    """
    if not VARIABLES_PATH.is_file():
        return {}
    with VARIABLES_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def get_variable(section: str, key: str, default: Any = None) -> Any:
    """
    섹션·키로 상수 값을 조회합니다.

    Args:
        section: 최상위 JSON 키 (예: physics).
        key: 섹션 내 키.
        default: 키가 없을 때 반환값.

    Returns:
        설정 값 또는 default.
    """
    data = load_all_variables()
    return data.get(section, {}).get(key, default)


def is_render() -> bool:
    """Render 네이티브 런타임 여부 (플랫폼이 RENDER=true를 주입)."""
    return os.environ.get("RENDER", "").strip().lower() in ("true", "1")


def env_str(*names: str, default: str = "") -> str:
    """첫 번째로 설정된 환경 변수 값을 반환합니다."""
    for name in names:
        value = os.environ.get(name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def env_bool(name: str, default: bool = False) -> bool:
    """환경 변수 불리언. 비어 있으면 default."""
    value = os.environ.get(name)
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def data_dir() -> Path:
    """JSON 저장 경로. DATA_DIR이 있으면 그 위치, 없으면 저장소 루트."""
    configured = env_str("DATA_DIR")
    if configured:
        path = Path(configured)
        path.mkdir(parents=True, exist_ok=True)
        return path
    return BASE_DIR
