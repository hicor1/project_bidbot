"""
입찰가 계산 — 한 파일, 한 책임.

책임: 시장 시세와 공급가(=하한가)로부터 '지금 올려야 할 판매 입찰가' 를 계산.
     외부 I/O 없음 (순수 함수). 마켓 공통.

공식: max(경쟁_최저가 - 감산, 공급가)
  - 경쟁자보다 '감산' 만큼 낮게 올려 노출 우선순위 선점
  - 단, 공급가 밑으로는 절대 내려가지 않음 (하한가 역할)

감산값(=경쟁자 대비 얼마나 낮출지)은 시장 관습상 1,000원을 기본값으로 쓴다.
필요 시 마켓/상품별로 다르게 넘길 수 있도록 인자로 노출.
"""

from __future__ import annotations

from typing import Optional


DEFAULT_UNDERCUT = 1_000   # 경쟁자 대비 낮출 기본 금액(원)
PRICE_GRID = 1_000         # 가격 단위 (원). KREAM 은 천원 단위 반올림이 관행.


def 제안_입찰가(
    경쟁_최저가: Optional[int],
    공급가: Optional[int],
    *,
    감산: int = DEFAULT_UNDERCUT,
    단위: int = PRICE_GRID,
) -> Optional[int]:
    """
    경쟁자 최저가와 공급가(=하한가)를 받아 내가 올릴 판매입찰가를 반환.

    규칙
    ----
    1. 공급가가 없거나 0 이하 → None (가격 결정 불가)
    2. 경쟁_최저가 가 None (경쟁자 없음) → 공급가로 고정 (방어적)
    3. 그 외 → max(경쟁_최저가 - 감산, 공급가), 천원 단위 내림 반올림
    4. 감산·단위는 음수면 0 취급 (방어)

    Returns
    -------
    int | None
    """
    if 공급가 is None or 공급가 <= 0:
        return None

    감산 = max(0, int(감산))
    단위 = max(1, int(단위))

    공급가_그리드 = _floor_to_grid(int(공급가), 단위)

    # 공급가가 단위보다 작으면 그리드 정렬 시 0 이 되어 올릴 수 없는 가격이 됨
    if 공급가_그리드 <= 0:
        return None

    if 경쟁_최저가 is None:
        return 공급가_그리드

    후보 = int(경쟁_최저가) - 감산
    결과 = max(후보, 공급가_그리드)
    return _floor_to_grid(결과, 단위)


def _floor_to_grid(value: int, grid: int) -> int:
    """단위(grid) 에 맞게 내림. grid=1000 이면 12345 → 12000."""
    if grid <= 1:
        return value
    # 음수가 들어오는 경우는 위에서 이미 걸러졌다고 가정
    return (value // grid) * grid
