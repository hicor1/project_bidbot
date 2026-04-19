"""
제품·사이즈별 시세 조회 — 안전 (읽기만).

설정: 아래 상수만 수정.
"""

import _common
_common.init_session()

# ─────────────────────────────────────────────────────────────
# 설정 (테스트할 상품)
# ─────────────────────────────────────────────────────────────
PRODUCT_ID = 13100      # KREAM 상품 ID (URL 마지막 숫자)
OPTION = "230"          # 사이즈 / 옵션 ('230', 'XL', 'ONE SIZE' 등)

# 자기경쟁 방지용 내 입찰가 (해당 상품에 내가 올린 가격 목록)
내_입찰가들 = []         # 예: [155000, 160000]
# ─────────────────────────────────────────────────────────────

from markets.kream import prices  # noqa: E402


def main():
    print(f"\n시세 조회: product_id={PRODUCT_ID}, option={OPTION}\n")

    시세 = prices.판매입찰_시세(PRODUCT_ID, OPTION)
    print(f"일반 판매 최저가 (lowest_normal): {_fmt(시세['lowest_ask_normal'])}")
    print(f"즉시판매가       (highest_bid) : {_fmt(시세['highest_bid'])}")
    print(f"판매입찰 수      (일반만)       : {len(시세['asks'])}")

    print("\n판매입찰 상위 10건 (가격 오름차순):")
    for i, a in enumerate(시세["asks"][:10], start=1):
        print(f"  [{i}] price={a['price']:,}  quantity={a['quantity']}")

    경쟁 = prices.경쟁자_최저가(PRODUCT_ID, OPTION, 내_입찰가들=내_입찰가들)
    print(f"\n경쟁자 최저가 (내 {내_입찰가들} 제외): {_fmt(경쟁)}")

    if 경쟁 is not None:
        제안 = 경쟁 - 1000
        print(f"→ bidbot 제안가 (경쟁-1000): {제안:,}")


def _fmt(v):
    if v is None:
        return "(없음)"
    if isinstance(v, (int, float)):
        return f"{v:,}"
    return str(v)


if __name__ == "__main__":
    main()
