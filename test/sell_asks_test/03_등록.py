"""
판매입찰 등록 — ⚠️ 실제 KREAM 에 내 입찰이 등록됨.

⚠️ 체결 방지 수칙 ⚠️
  - 가격은 반드시 **시세 최저가의 3~5배 이상** 으로 설정
  - 등록 직후 ask_id 를 받아 기록 → 필요 시 05_삭제.py 로 바로 취소

설정: 아래 상수만 수정.
"""

import _common
_common.init_session()

# ─────────────────────────────────────────────────────────────
# 설정 (반드시 확인)
# ─────────────────────────────────────────────────────────────
PRODUCT_ID = 13100          # 테스트할 상품 ID
OPTION = "230"              # 사이즈
PRICE = 9_999_000           # ⚠️ 체결 불가능한 높은 가격으로!
IS_KEEP_ON_DEFERRED = False # 검수보류시 창고보관 여부
EXPIRES_IN = 180            # 입찰 유효기간 (일): 1/3/7/14/30/60/180
# shipping_address_id 는 자동으로 기본 배송지 사용. 특정 배송지 원하면 숫자 입력.
SHIPPING_ADDRESS_ID = None
# ─────────────────────────────────────────────────────────────

from markets.kream import sell_asks  # noqa: E402


def main():
    print("\n⚠️  판매입찰 등록 시작")
    print(f"  product_id = {PRODUCT_ID}")
    print(f"  option     = {OPTION}")
    print(f"  price      = {PRICE:,}")
    print(f"  is_keep_on_deferred = {IS_KEEP_ON_DEFERRED}")
    print(f"  expires_in = {EXPIRES_IN}")
    print()

    result = sell_asks.판매입찰_등록(
        product_id=PRODUCT_ID,
        option=OPTION,
        price=PRICE,
        shipping_address_id=SHIPPING_ADDRESS_ID,
        is_keep_on_deferred=IS_KEEP_ON_DEFERRED,
        expires_in=EXPIRES_IN,
    )

    if result["성공"]:
        print("[OK] 등록 성공")
        print(f"  ask_id = {result['ask_id']}")
        print()
        print("↓ 이 ID 를 04_가격수정.py / 05_삭제.py 에 넣어 다음 테스트 진행 ↓")
        print(f"ASK_ID = {result['ask_id']}")
    else:
        print("[FAIL] 등록 실패")
        print(f"  사유: {result['사유']}")


if __name__ == "__main__":
    main()
