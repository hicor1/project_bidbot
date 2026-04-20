"""
판매입찰 취소(삭제) — ⚠️ 실제 KREAM 에서 내 입찰이 내려감.

설정: 아래 상수만 수정.
"""

import _common
_common.init_session()

# ─────────────────────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────────────────────
ASK_ID = 160401193   # ⚠️ 취소할 ask_id (03_등록.py 결과 또는 01_목록_조회.py 의 id)
# ─────────────────────────────────────────────────────────────

from markets.kream import sell_asks  # noqa: E402


def main():
    if ASK_ID == 0:
        print("[중지] ASK_ID 설정되지 않음.")
        return

    print(f"\n⚠️  판매입찰 삭제 시작 (ask_id={ASK_ID})\n")

    result = sell_asks.판매입찰_삭제(ask_id=ASK_ID)

    if result["성공"]:
        print(f"[OK] 삭제 성공 (ask_id={result['ask_id']})")
    else:
        print(f"[FAIL] 삭제 실패: {result['사유']}")
        print(f"  _raw: {result.get('_raw')}")


if __name__ == "__main__":
    main()
