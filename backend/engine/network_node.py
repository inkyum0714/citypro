"""Phase 2: 교차로(Node) 정의."""

from __future__ import annotations

from typing import Any


def node_dict(node_id: int, x: float, y: float) -> dict[str, Any]:
    """
    교차로 노드 직렬화 dict를 만듭니다.

    Args:
        node_id: 노드 ID.
        x: 화면/월드 x.
        y: 화면/월드 y.

    Returns:
        id, x, y를 포함하는 dict.
    """
    return {"id": node_id, "x": round(x, 2), "y": round(y, 2)}
