"""
판매입찰 가격 수정 — ⚠️ 실제 KREAM 에서 내 입찰 가격이 변경됨.

⚠️ 체결 방지 수칙 ⚠️
  - 수정 후 가격도 반드시 **시세 최저가 훨씬 위** 로 유지
  - ASK_ID 는 03_등록.py 에서 받은 값을 넣을 것

설정: 아래 상수만 수정.
"""

import _common
_common.init_session()

# ─────────────────────────────────────────────────────────────
# 설정 (반드시 확인)
# ─────────────────────────────────────────────────────────────
ASK_ID = 0                  # ⚠️ 03_등록.py 가 반환한 ask_id
새_가격 = 8_888_000         # ⚠️ 여전히 체결 불가능한 높은 가격으로
# ─────────────────────────────────────────────────────────────

from markets.kream import sell_asks  # noqa: E402


def main():
    if ASK_ID == 0:
        print("[중지] ASK_ID 설정되지 않음. 03_등록.py 결과를 넣어주세요.")
        return

    print(f"\n⚠️  판매입찰 가격수정 시작")
    print(f"  ask_id  = {ASK_ID}")
    print(f"  새_가격 = {새_가격:,}")
    print()

    result = sell_asks.판매입찰_가격수정(ask_id=ASK_ID, 새_가격=새_가격)

    if result["성공"]:
        print("[OK] 수정 성공")
        print(f"  ask_id   = {result['ask_id']}")
        print(f"  새_가격   = {result['새_가격']:,}")
        print(f"  정산금액  = {result['정산금액']:,}" if result.get('정산금액') else "")
    else:
        print("[FAIL] 수정 실패")
        print(f"  사유: {result['사유']}")


if __name__ == "__main__":
    main()
