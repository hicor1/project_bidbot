"""
KREAM 제품별 시세/경쟁 입찰 조회 — 한 파일, 한 책임.

책임: 지정한 (product_id, option) 의 **일반 판매입찰** 시세를 읽는다. 쓰기 없음.
     보관판매(보판_95/100) 로직은 포함하지 않음 (추후 필요 시 별도 파일).

bidbot 리프라이싱은 "내 입찰 빼고 경쟁자 최저가" 만 알면 충분하므로 인터페이스를
그 목적에 맞게 최소화했다.

원본 참조: KREAM_BASE/Module/Function/KREAM_제품별_입찰정보.py
  - 보관판매 관련 분기(is_immediate_delivery, inventory_95) 전부 제외.
  - sales_options.lowest_normal / highest_bid 만 활용.
"""

from __future__ import annotations

from typing import Iterable, Optional

from . import http


KREAM_API_BASE = "https://api.kream.co.kr"


# ─────────────────────────────────────────────────────────────
# Public
# ─────────────────────────────────────────────────────────────
def 판매입찰_시세(product_id: int | str, option: str) -> dict:
    """(product_id, option) 의 일반 판매입찰 시세.

    반환 필드:
        lowest_ask_normal: 일반 판매 최저가 (KREAM sales_options.lowest_normal)
        highest_bid      : 즉시판매가 (구매자 최고 입찰)
        asks             : [{"price": int, "quantity": int}, ...]  일반 판매입찰 원시
    """
    product_info, asks_raw = _fetch_product_and_asks(product_id, option)

    sales_option = _pick_sales_option(product_info, option)

    lowest_normal = sales_option.get("lowest_normal") if sales_option else None
    highest_bid = sales_option.get("highest_bid") if sales_option else None

    asks = [
        {"price": a["price"], "quantity": a.get("quantity", 1)}
        for a in asks_raw
        if a.get("is_immediate_delivery_item") is False
    ]
    asks.sort(key=lambda d: d["price"])

    return {
        "lowest_ask_normal": lowest_normal,
        "highest_bid": highest_bid,
        "asks": asks,
    }


def 경쟁자_최저가(
    product_id: int | str,
    option: str,
    내_입찰가들: Optional[Iterable[int]] = None,
) -> Optional[int]:
    """내 입찰을 제외한 경쟁자 최저 판매입찰가. 경쟁자 없으면 None.

    내_입찰가들: 내가 해당 (product_id, option) 에 올린 가격 목록.
                자기경쟁 방지를 위해 제외.
    """
    시세 = 판매입찰_시세(product_id, option)
    asks = 시세["asks"]
    공식_최저 = 시세["lowest_ask_normal"]

    # 내 입찰 차감 (가격 동일한 건 하나씩만 카운트 감소)
    내_입찰가_목록 = list(내_입찰가들) if 내_입찰가들 else []
    asks_남음: list[dict] = []
    for a in asks:
        price = a["price"]
        quantity = a["quantity"]
        일치건수 = 내_입찰가_목록.count(price)
        남은수량 = quantity - 일치건수
        if 남은수량 > 0:
            asks_남음.append({"price": price, "quantity": 남은수량})

    # 공식 최저가(lowest_normal)가 asks_raw 에 안 잡혔을 수 있음 → 후보에 포함
    후보 = [a["price"] for a in asks_남음]
    if 공식_최저 is not None and 공식_최저 not in 내_입찰가_목록:
        후보.append(공식_최저)

    if not 후보:
        return None
    return min(후보)


# ─────────────────────────────────────────────────────────────
# Internal
# ─────────────────────────────────────────────────────────────
def _fetch_product_and_asks(product_id: int | str, option: str) -> tuple[dict, list]:
    """제품 상세와 판매입찰 리스트를 함께 반환."""
    detail_url = f"{KREAM_API_BASE}/api/p/products/{product_id}/{option}"
    asks_url = (
        f"{KREAM_API_BASE}/api/p/products/{product_id}/{option}/asks"
        "?cursor=1&per_page=50&sort=price[asc],option[asc]"
    )

    detail = http.get(detail_url, timeout=10)
    detail.raise_for_status()
    detail_json = detail.json()

    asks = http.get(asks_url, timeout=10)
    asks.raise_for_status()
    asks_items = (asks.json() or {}).get("items") or []

    return detail_json, asks_items


def _pick_sales_option(product_info: dict, option: str) -> Optional[dict]:
    """product_info.sales_options 에서 입력 option 과 일치하는 항목."""
    sales_options = product_info.get("sales_options") or []
    for so in sales_options:
        product_option = so.get("product_option") or {}
        if product_option.get("key") == option:
            return so
    return None
