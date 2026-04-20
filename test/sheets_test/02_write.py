"""
구글시트 쓰기 테스트 — 봇 영역만.

안전 전략:
  1. 타겟 셀 3개의 현재 값을 백업
  2. 테스트 값으로 갱신 (batch)
  3. 3초 후 원래 값으로 자동 원복
  4. 마지막에 최종 상태 다시 읽어 원복 확인

기본 타겟: 3행(첫 데이터 행)의 봇 영역 3개 셀
  - 공급가(=하한가)
  - 갱신일
  - 크림상태

설정은 아래 상수에서 변경 가능. 사람 영역 컬럼을 넣으면 ValueError 로 즉시 중단됨.
"""

import time
from datetime import datetime

import _common  # noqa: F401

from sheets.gsheet import (
    open_worksheet,
    read_header_and_rows,
    update_row_bot_cells,
)


# ─────────────────────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────────────────────
TARGET_ROW = 3          # 1-based. 3 = 첫 데이터 행
TEST_VALUES = {
    "공급가(=하한가)": 999,                  # 원래 비어있다가 999 로 바뀌어야
    "갱신일": "테스트중",
    "크림상태": "테스트",
}
SLEEP_SEC = 3           # 쓰기 후 원복 전 대기 (시트에서 눈으로 확인할 시간)
# ─────────────────────────────────────────────────────────────


def 구분선(제목):
    print()
    print("=" * 60)
    print(제목)
    print("=" * 60)


def 셀값_읽기(ws, row, col_names):
    """지정 행의 여러 컬럼 값 dict 반환."""
    headers, rows = read_header_and_rows(ws)
    idx_in_rows = row - 3  # 3행이 rows[0]
    if idx_in_rows < 0 or idx_in_rows >= len(rows):
        raise RuntimeError(f"row {row} 은 시트의 데이터 범위 밖입니다.")
    source = rows[idx_in_rows]
    return {name: source.get(name, "") for name in col_names}


def main():
    ws = open_worksheet()
    print(f"시트 : {ws.spreadsheet.title} / {ws.title}")
    print(f"타겟 행: {TARGET_ROW}")
    print(f"변경 대상: {list(TEST_VALUES.keys())}")

    구분선("1. 원본 값 백업")
    원본 = 셀값_읽기(ws, TARGET_ROW, TEST_VALUES.keys())
    for k, v in 원본.items():
        display = v if v != "" else "(빈값)"
        print(f"  {k:20s} = {display}")

    구분선("2. 테스트 값 쓰기")
    for k, v in TEST_VALUES.items():
        print(f"  {k:20s} ← {v}")
    update_row_bot_cells(ws, TARGET_ROW, TEST_VALUES)
    print("[OK] batch_update 호출 완료")

    구분선(f"3. {SLEEP_SEC}초 대기 — 구글시트에서 직접 눈으로 확인 가능")
    for i in range(SLEEP_SEC, 0, -1):
        print(f"  원복까지 {i}초...")
        time.sleep(1)

    구분선("4. 원복 (원본 값 복원)")
    update_row_bot_cells(ws, TARGET_ROW, 원본)
    print("[OK] 원복 요청 완료")

    구분선("5. 최종 확인 — 원본 상태로 돌아왔는지")
    최종 = 셀값_읽기(ws, TARGET_ROW, TEST_VALUES.keys())
    모두_원복 = True
    for k in TEST_VALUES.keys():
        before = 원본[k]
        after = 최종[k]
        ok = before == after
        mark = "✅" if ok else "❌"
        print(f"  {mark} {k:20s}  원본={before!r:20s} → 최종={after!r}")
        if not ok:
            모두_원복 = False

    구분선("결과")
    if 모두_원복:
        print("[OK] 쓰기 → 원복 전체 사이클 정상")
    else:
        print("[FAIL] 원복 검증 실패 — 시트 확인 필요")


if __name__ == "__main__":
    main()
