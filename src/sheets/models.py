"""
시트 행 도메인 모델 — 한 파일, 한 책임.

책임: 시트에서 읽어온 원시 dict 를 타입 지정된 파이썬 객체(ProductRow)로 변환한다.
     네트워크 I/O 는 이 파일에 없다 (그건 gsheet.py 의 책임).
     입찰가 계산 로직도 이 파일에 없다 (그건 core/pricing.py 의 책임).

여기서만 하는 것:
  - 원시 문자열 → 타입 파싱 (schema 의 parse_* 유틸 활용)
  - 고유키 (CODE, SIZE) 관리
  - 봇 동작용 파생값 — 특히 공급가 자동 계산
  - 행 번호(row_number) 보존 → 역기입 시 위치 식별
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from . import schema


# ─────────────────────────────────────────────────────────────
# ProductRow
# ─────────────────────────────────────────────────────────────
@dataclass
class ProductRow:
    """상품마스터 시트의 한 행을 타입 고정된 형태로 표현.

    필드명은 schema 의 컬럼명을 영문/스네이크로 매핑.
    시트 원본 값을 보존하고 싶은 경우 _raw 를 참조.
    """

    # 사람 영역
    brand: str = ""
    poizon_on: bool = False                 # 포이즌 V 플래그
    kream_on: bool = False                  # 크림 V 플래그
    ship_from: str = ""
    name: str = ""
    code: str = ""                          # CODE (숫자/문자 혼재 허용 → 문자열로 통일)
    size: str = ""
    qty: int = 0
    list_price: Optional[int] = None        # 정상가
    discount: Optional[float] = None        # 할인율 (0~1)

    # 봇 영역 (읽어올 수도, 계산해 쓸 수도)
    supply_price: Optional[int] = None      # 공급가 = 하한가
    kream_bid_now: Optional[int] = None     # 크림에 현재 걸린 내 입찰가
    poizon_bid_now: Optional[int] = None    # 포이즌에 현재 걸린 내 입찰가
    updated_at: str = ""                    # 갱신일 텍스트
    kream_status: str = ""
    poizon_status: str = ""

    # 위치/원본
    row_number: int = 0                     # 1-based 시트 행 번호 (역기입용)
    _raw: dict = field(default_factory=dict, repr=False)

    # ── 파생 ──
    @property
    def key(self) -> tuple[str, str]:
        """고유키 (CODE, SIZE). 둘 다 앞뒤 공백 제거, 대소문자 보존."""
        return (self.code.strip(), self.size.strip())

    @property
    def is_active_for_kream(self) -> bool:
        """KREAM 에 올려야 하는 행인가? (V + 수량 > 0 + 사람이 보류로 막지 않음)"""
        if not self.kream_on:
            return False
        if self.qty <= 0:
            return False
        if self.kream_status == schema.STATUS_HOLD:
            return False
        return True

    @property
    def is_active_for_poizon(self) -> bool:
        if not self.poizon_on:
            return False
        if self.qty <= 0:
            return False
        if self.poizon_status == schema.STATUS_HOLD:
            return False
        return True

    def compute_supply_price(self) -> Optional[int]:
        """정상가·할인율로 공급가 재계산. 실패 시 None."""
        return schema.compute_supply_price(self.list_price, self.discount)


# ─────────────────────────────────────────────────────────────
# 파싱: 시트 dict → ProductRow
# ─────────────────────────────────────────────────────────────
def from_dict(raw: dict, row_number: int) -> ProductRow:
    """read_header_and_rows() 결과의 한 dict 를 ProductRow 로 변환.

    파싱 실패는 예외로 던지지 않고 해당 필드를 None/기본값으로 둔다.
    유효성 검증은 상위 레이어(core/sync.py 등)에서 진행.
    """
    def get(col_name: str):
        return raw.get(col_name, "")

    return ProductRow(
        brand=schema.parse_str(get("브랜드")),
        poizon_on=schema.parse_flag(get("포이즌")),
        kream_on=schema.parse_flag(get("크림")),
        ship_from=schema.parse_str(get("출고처")),
        name=schema.parse_str(get("NAME")),
        code=schema.parse_str(get("CODE")),
        size=schema.parse_str(get("SIZE")),
        qty=schema.parse_int(get("수량"), default=0) or 0,
        list_price=schema.parse_int(get("정상가")),
        discount=schema.parse_float(get("할인율")),
        supply_price=schema.parse_int(get("공급가(=하한가)")),
        kream_bid_now=schema.parse_int(get("크림현재입찰가")),
        poizon_bid_now=schema.parse_int(get("포이즌현재입찰가")),
        updated_at=schema.parse_str(get("갱신일")),
        kream_status=schema.parse_str(get("크림상태")),
        poizon_status=schema.parse_str(get("포이즌상태")),
        row_number=row_number,
        _raw=dict(raw),
    )


def parse_rows(raw_rows: Iterable[dict]) -> list[ProductRow]:
    """여러 행 dict 를 ProductRow 리스트로. row_number 는 DATA_START_ROW 부터 자동 할당."""
    result: list[ProductRow] = []
    for i, raw in enumerate(raw_rows):
        row_number = schema.DATA_START_ROW + i
        result.append(from_dict(raw, row_number=row_number))
    return result


# ─────────────────────────────────────────────────────────────
# 고유키 인덱스
# ─────────────────────────────────────────────────────────────
def build_index(rows: Iterable[ProductRow]) -> dict[tuple[str, str], ProductRow]:
    """(CODE, SIZE) → ProductRow 매핑. 중복 키가 있으면 경고 후 마지막 행 채택."""
    idx: dict[tuple[str, str], ProductRow] = {}
    dupes: list[tuple[str, str]] = []
    for row in rows:
        key = row.key
        if not key[0] or not key[1]:
            # 빈 키는 인덱스에 넣지 않음 (신규 입력 중 일부 비어있는 행 등)
            continue
        if key in idx:
            dupes.append(key)
        idx[key] = row
    if dupes:
        print(f"[models] WARN: 중복 고유키 {len(dupes)}개. 마지막 행 채택. 예: {dupes[:3]}")
    return idx
