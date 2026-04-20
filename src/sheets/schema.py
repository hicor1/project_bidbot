"""
상품마스터 시트 스키마 정의 — 한 파일, 한 책임.

책임: 시트의 열 구조·역할·타입·파싱 규칙을 '단일 진실 소스' 로 보관한다.
     gsheet.py, models.py, core/* 등 모든 상위 모듈은 여기만 참조.

스키마 변경이 필요하면 여기만 고치면 된다.
원본 참조: docs/sheet_template.xlsx, docs/개발노트.md §11.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# ─────────────────────────────────────────────────────────────
# 레이아웃
# ─────────────────────────────────────────────────────────────
NOTICE_ROW = 1   # 1행: 안내문구 (병합, 읽기 시 스킵)
HEADER_ROW = 2   # 2행: 헤더
DATA_START_ROW = 3  # 3행부터 데이터

DEFAULT_WORKSHEET_NAME = "상품마스터"

# gspread.Worksheet.get_all_records 파라미터: head=HEADER_ROW
GSPREAD_HEAD = HEADER_ROW


# ─────────────────────────────────────────────────────────────
# 컬럼 정의
# ─────────────────────────────────────────────────────────────
Owner = Literal["human", "bot"]


@dataclass(frozen=True)
class Column:
    """한 컬럼의 메타. 순서는 리스트 index 로 관리 (1-based)."""
    name: str           # 시트 헤더에 실제로 쓰이는 문자열 (한글)
    owner: Owner        # human / bot — 누가 쓰는가
    memo: str = ""      # 사람용 메모 (의미/규칙)


# 순서 = 시트 컬럼 1..N. 변경 시 템플릿 xlsx 와 반드시 동기화.
COLUMNS: tuple[Column, ...] = (
    Column("브랜드",            "human", "필수"),
    Column("포이즌",            "human", "V=등록, 빈값=미등록"),
    Column("크림",              "human", "V=등록, 빈값=미등록"),
    Column("출고처",            "human", ""),
    Column("NAME",             "human", "앞뒤 공백/탭 strip"),
    Column("CODE",             "human", "고유키 일부 (SIZE 와 조합), 숫자/문자 혼재 허용"),
    Column("SIZE",             "human", "고유키 일부"),
    Column("수량",              "human", "int, 0=해당 마켓 등록 off"),
    Column("정상가",            "human", "int"),
    Column("할인율",            "human", "float, 0~1"),
    Column("공급가(=하한가)",   "bot",   "정상가×(1-할인율) 반올림. 리프라이싱 min."),
    Column("크림현재입찰가",    "bot",   "KREAM 에 현재 걸려있는 내 입찰가. 실패/off/보류 시 빈값."),
    Column("포이즌현재입찰가",  "bot",   "POIZON 에 현재 걸려있는 내 입찰가. 실패/off/보류 시 빈값."),
    Column("갱신일",            "bot",   "YYYY-MM-DD HH:MM (KST, 텍스트)"),
    Column("크림상태",          "bot",   "정상 / off / 보류 / 오류:<사유>"),
    Column("포이즌상태",        "bot",   "정상 / off / 보류 / 오류:<사유>"),
)

TOTAL_COLUMNS = len(COLUMNS)  # 16


# ─────────────────────────────────────────────────────────────
# 인덱스 편의 상수 (1-based 시트 열 번호)
#   gspread 는 1-based 를 쓴다. 파이썬 0-based 가 필요하면 -1.
# ─────────────────────────────────────────────────────────────
def _col_index(name: str) -> int:
    for i, c in enumerate(COLUMNS, start=1):
        if c.name == name:
            return i
    raise KeyError(f"알 수 없는 컬럼명: {name}")


COL_BRAND = _col_index("브랜드")
COL_POIZON_FLAG = _col_index("포이즌")
COL_KREAM_FLAG = _col_index("크림")
COL_SHIP_FROM = _col_index("출고처")
COL_NAME = _col_index("NAME")
COL_CODE = _col_index("CODE")
COL_SIZE = _col_index("SIZE")
COL_QTY = _col_index("수량")
COL_LIST_PRICE = _col_index("정상가")
COL_DISCOUNT = _col_index("할인율")
COL_SUPPLY_PRICE = _col_index("공급가(=하한가)")
COL_KREAM_BID_NOW = _col_index("크림현재입찰가")
COL_POIZON_BID_NOW = _col_index("포이즌현재입찰가")
COL_UPDATED_AT = _col_index("갱신일")
COL_KREAM_STATUS = _col_index("크림상태")
COL_POIZON_STATUS = _col_index("포이즌상태")


HUMAN_COLUMN_NAMES: tuple[str, ...] = tuple(
    c.name for c in COLUMNS if c.owner == "human"
)
BOT_COLUMN_NAMES: tuple[str, ...] = tuple(
    c.name for c in COLUMNS if c.owner == "bot"
)
BOT_COLUMN_INDICES: tuple[int, ...] = tuple(
    i for i, c in enumerate(COLUMNS, start=1) if c.owner == "bot"
)


# ─────────────────────────────────────────────────────────────
# 상태 열 값
# ─────────────────────────────────────────────────────────────
STATUS_OK = "정상"
STATUS_OFF = "off"
STATUS_HOLD = "보류"  # 사람이 수동 입력 → 봇 스킵
STATUS_ERROR_PREFIX = "오류:"


def make_error_status(reason: str) -> str:
    """봇이 상태 열에 기록할 오류 문자열. 사유는 짧게, 핵심만."""
    reason = (reason or "").strip() or "unknown"
    return f"{STATUS_ERROR_PREFIX}{reason}"


# ─────────────────────────────────────────────────────────────
# 파싱 유틸 — 시트 값은 관대하게 받고 내부에선 타입 고정
# ─────────────────────────────────────────────────────────────
def parse_flag(value) -> bool:
    """V / 'V' / 빈값 / None 모두 허용. 대소문자 무시. 그 외는 False."""
    if value is None:
        return False
    s = str(value).strip().upper()
    return s == "V"


def parse_int(value, *, default: int | None = None) -> int | None:
    """빈값/None → default. 소수는 반올림. 실패 시 default."""
    if value is None or value == "":
        return default
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def parse_float(value, *, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_str(value, *, default: str = "") -> str:
    if value is None:
        return default
    # NAME 이 탭으로 끝나는 실측 사례 있음 → strip 필수
    return str(value).strip()


def compute_supply_price(list_price: int | None, discount: float | None) -> int | None:
    """공급가 = 정상가 × (1 - 할인율). 실패 시 None."""
    if list_price is None or discount is None:
        return None
    if list_price <= 0:
        return None
    if not (0 <= discount < 1):
        return None
    return int(round(list_price * (1 - discount)))
