"""프로젝트 전역 상수(all_variable.json) 로더."""

from __future__ import annotations

import json
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
