"""
안전장치 검증 — 사람 영역 쓰기 시도 시 즉시 ValueError 나는지 확인.

실제 네트워크 호출 없이 파라미터 검증만 돌리는 테스트 (안전 100%).
"""

import _common  # noqa: F401

from sheets import schema
from sheets.gsheet import _validate_bot_write


def 구분선(제목):
    print()
    print("=" * 60)
    print(제목)
    print("=" * 60)


def 케이스(설명, row, values, expect_fail=True):
    try:
        _validate_bot_write(row, values)
        if expect_fail:
            print(f"❌ [실패_감지X] {설명}  (ValueError 기대했으나 통과됨)")
            return False
        else:
            print(f"✅ [정상_통과]   {설명}")
            return True
    except ValueError as e:
        if expect_fail:
            print(f"✅ [정상_차단]   {설명}")
            print(f"    사유: {e}")
            return True
        else:
            print(f"❌ [실패_차단X] {설명}  (통과 기대했으나 ValueError)")
            print(f"    사유: {e}")
            return False


def main():
    구분선("안전장치 검증")

    results = []

    # 위반 케이스 (전부 차단돼야 함)
    results.append(케이스("1행 쓰기 시도 (안내문구 보호)",
                        row=1, values={"크림상태": "x"}))
    results.append(케이스("2행 쓰기 시도 (헤더 보호)",
                        row=2, values={"크림상태": "x"}))
    results.append(케이스("사람 영역 '브랜드' 쓰기",
                        row=3, values={"브랜드": "x"}))
    results.append(케이스("사람 영역 '할인율' 쓰기",
                        row=3, values={"할인율": 0.5}))
    results.append(케이스("존재하지 않는 컬럼명",
                        row=3, values={"미존재컬럼": "x"}))
    results.append(케이스("봇 + 사람 영역 혼합 (하나라도 있으면 전체 거부)",
                        row=3, values={"크림상태": "정상", "브랜드": "x"}))

    # 통과 케이스
    results.append(케이스("정상: 봇 영역 단일 (크림상태)",
                        row=3, values={"크림상태": "정상"},
                        expect_fail=False))
    results.append(케이스("정상: 봇 영역 다수",
                        row=3, values={
                            "공급가(=하한가)": 41300,
                            "크림현재입찰가": 52000,
                            "갱신일": "2026-04-20 10:30",
                            "크림상태": "정상",
                        }, expect_fail=False))
    results.append(케이스("정상: 데이터 영역 깊은 행 (row=1000)",
                        row=1000, values={"크림상태": "정상"},
                        expect_fail=False))

    구분선(f"총 {len(results)}건 중 {sum(results)}건 통과")
    if all(results):
        print("[OK] 안전장치 동작 정상")
    else:
        print("[FAIL] 일부 안전장치가 작동하지 않음 — 코드 재점검 필요")


if __name__ == "__main__":
    main()
