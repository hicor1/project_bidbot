"""
구글시트 I/O — 한 파일, 한 책임.

책임: 상품마스터 시트와의 통신. 인증/접속/행 읽기/행 쓰기.
     스키마 해석(타입 변환)은 하지 않음 — 그건 models.py 의 책임.
     여기서는 "셀 값을 dict 로" 까지만.

사용 환경변수:
  GOOGLE_CREDENTIALS_PATH   서비스 계정 JSON 키 경로 (필수)
  GOOGLE_SHEET_ID           스프레드시트 ID (필수)
  GOOGLE_SHEET_WORKSHEET    탭 이름 (선택, 기본 '상품마스터')

원본 참조: KREAM_BASE/Module/Util/google_spread.py (방식만 참고)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from . import schema


# gspread 6.x: sheets.googleapis.com 만으로도 충분. 드라이브 스코프는 파일 목록 조회용.
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


@dataclass
class SheetConfig:
    credentials_path: str
    sheet_id: str
    worksheet_name: str = schema.DEFAULT_WORKSHEET_NAME

    @classmethod
    def from_env(cls) -> "SheetConfig":
        path = os.environ.get("GOOGLE_CREDENTIALS_PATH")
        sheet_id = os.environ.get("GOOGLE_SHEET_ID")
        ws = os.environ.get("GOOGLE_SHEET_WORKSHEET") or schema.DEFAULT_WORKSHEET_NAME
        if not path:
            raise RuntimeError("환경변수 GOOGLE_CREDENTIALS_PATH 필요")
        if not sheet_id:
            raise RuntimeError("환경변수 GOOGLE_SHEET_ID 필요")
        if not os.path.exists(path):
            raise RuntimeError(f"GOOGLE_CREDENTIALS_PATH 파일 없음: {path}")
        return cls(credentials_path=path, sheet_id=sheet_id, worksheet_name=ws)


# ─────────────────────────────────────────────────────────────
# 저수준: gspread 클라이언트/워크시트 핸들
# ─────────────────────────────────────────────────────────────
def _build_client(config: SheetConfig) -> gspread.Client:
    creds = Credentials.from_service_account_file(
        config.credentials_path, scopes=_SCOPES
    )
    return gspread.authorize(creds)


def open_worksheet(config: Optional[SheetConfig] = None) -> gspread.Worksheet:
    """환경설정대로 워크시트(탭) 핸들 반환.

    탭 이름이 안 맞으면 첫 번째 탭으로 fallback 하되 경고 출력.
    """
    config = config or SheetConfig.from_env()
    client = _build_client(config)
    sh = client.open_by_key(config.sheet_id)

    try:
        return sh.worksheet(config.worksheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.get_worksheet(0)
        available = [w.title for w in sh.worksheets()]
        print(
            f"[gsheet] WARN: 워크시트 '{config.worksheet_name}' 없음. "
            f"첫 번째 탭 '{ws.title}' 사용. 사용 가능 목록: {available}"
        )
        return ws


# ─────────────────────────────────────────────────────────────
# 읽기
# ─────────────────────────────────────────────────────────────
def read_header_and_rows(
    worksheet: Optional[gspread.Worksheet] = None,
) -> tuple[list[str], list[dict]]:
    """
    2행 헤더 + 3행부터의 데이터 반환.

    반환:
        (headers, rows)
          headers: 시트의 실제 헤더 문자열 리스트 (순서 그대로)
          rows   : [{헤더명: 값, ...}, ...]   3행부터 각 행

    값은 원시(gspread 가 돌려주는 그대로 str/int/float). 타입 변환은 상위에서.
    """
    if worksheet is None:
        worksheet = open_worksheet()

    all_values = worksheet.get_all_values()
    if len(all_values) < schema.HEADER_ROW:
        return [], []

    headers = [h.strip() for h in all_values[schema.HEADER_ROW - 1]]
    data_rows = all_values[schema.DATA_START_ROW - 1:]

    rows: list[dict] = []
    for raw in data_rows:
        # 빈 행 (모든 셀이 '') 은 스킵
        if not any(v.strip() if isinstance(v, str) else v for v in raw):
            continue
        # 열 수가 헤더보다 적으면 빈 문자열로 패딩
        padded = list(raw) + [""] * (len(headers) - len(raw))
        rows.append({headers[i]: padded[i] for i in range(len(headers))})
    return headers, rows


def validate_headers(headers: list[str]) -> list[str]:
    """실제 시트 헤더가 schema.COLUMNS 와 맞는지 검증.

    반환: 경고/오류 메시지 리스트 (빈 리스트면 정상).
    """
    messages: list[str] = []
    expected = [c.name for c in schema.COLUMNS]

    if len(headers) < len(expected):
        messages.append(
            f"헤더 수 부족: 시트 {len(headers)}개 vs 기대 {len(expected)}개"
        )

    # 순서대로 비교
    for i, (exp, actual) in enumerate(zip(expected, headers), start=1):
        if exp != actual:
            messages.append(
                f"열 {i} 헤더 불일치: 기대 '{exp}' vs 실제 '{actual}'"
            )

    if len(headers) > len(expected):
        extras = headers[len(expected):]
        messages.append(f"기대 외 추가 열 {len(extras)}개: {extras}")

    return messages
