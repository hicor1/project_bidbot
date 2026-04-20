"""
구글시트 읽기 테스트 — 안전 (읽기만).

확인 항목:
1. 서비스 계정 인증 성공
2. 시트/탭 열기 성공
3. 2행 헤더 + 3행~ 데이터 추출
4. 헤더가 schema 와 일치하는지 검증
"""

import _common  # noqa: F401  (.env 로드 + src path)

from sheets import schema
from sheets.gsheet import open_worksheet, read_header_and_rows, validate_headers


def 구분선(제목):
    print()
    print("=" * 60)
    print(제목)
    print("=" * 60)


def main():
    구분선("1. 워크시트 열기")
    ws = open_worksheet()
    print(f"시트 제목  : {ws.spreadsheet.title}")
    print(f"워크시트   : {ws.title}")
    print(f"행 수      : {ws.row_count}")
    print(f"열 수      : {ws.col_count}")

    구분선("2. 헤더 + 데이터 행 읽기")
    headers, rows = read_header_and_rows(ws)
    print(f"헤더 열수  : {len(headers)}")
    print(f"데이터 행수: {len(rows)}")
    print()
    print("헤더:")
    for i, h in enumerate(headers, start=1):
        print(f"  [{i:2d}] {h}")

    구분선("3. 스키마 검증")
    problems = validate_headers(headers)
    if not problems:
        print("[OK] 시트 헤더가 schema.py 와 완벽히 일치")
    else:
        print("[WARN] 불일치 발견:")
        for p in problems:
            print(f"  - {p}")

    구분선("4. 데이터 행 미리보기 (상위 5건)")
    for i, row in enumerate(rows[:5], start=1):
        print(f"\n[{i}]")
        for k, v in row.items():
            display = v if v != "" else "(빈값)"
            print(f"  {k:20s} = {display}")

    구분선(f"총 {len(rows)}행 확인 완료")


if __name__ == "__main__":
    main()
