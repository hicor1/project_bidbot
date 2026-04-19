"""
KREAM 내 판매입찰(일반) 생명주기 관리 — 한 파일, 한 책임.

책임: 내가 KREAM에 올린 **일반 판매입찰**의 목록/등록/수정/삭제.
     보관판매(보판)는 이 파일 범위 아님 (추후 storage_asks.py 로 분리).

원본 참조:
  - KREAM_BASE/Module/Function/KREAM_판매입찰_입찰관리.py   (등록/삭제)
  - KREAM_BASE/Module/Function/KREAM_제품별_판매입찰가격수정.py  (수정)
  - KREAM_BASE/Module/Function/KREAM_제품별_판매입찰상세정보.py  (수정 전 기존값 조회)
  - KREAM_BASE/Module/Function/KREAM_판매내역V판매입찰.py    (목록 조회)
"""

from __future__ import annotations

import time
from typing import Optional

from . import http


KREAM_API_BASE = "https://api.kream.co.kr"

# 내 입찰 관련 엔드포인트
_URL_ADDRESSES = f"{KREAM_API_BASE}/api/users/me/addresses"
_URL_ASKS = f"{KREAM_API_BASE}/api/m/asks"            # POST 등록/수정
_URL_ASKS_BIDDING = f"{_URL_ASKS}/bidding"            # GET 목록
_URL_ASK_DETAIL = f"{_URL_ASKS}/{{ask_id}}"           # GET 상세 / DELETE 삭제

# 페이지 사이즈는 KREAM 상한 50 고정
_PAGE_SIZE = 50
# 페이지 누적 호출 시 차단 방지 간격
_PAGE_SLEEP_SEC = 0.5
# 페이지 간격 지연이 필요해지는 누적 페이지 수
_PAGE_SLEEP_AFTER = 10


# ─────────────────────────────────────────────────────────────
# 배송지
# ─────────────────────────────────────────────────────────────
def 기본_배송지_ID() -> int:
    """기본 배송지 ID. 판매입찰 등록 시 필수값."""
    response = http.get(_URL_ADDRESSES)
    response.raise_for_status()
    data = response.json()
    default = next((d for d in data if d.get("is_default") is True), None)
    if default is None:
        if not data:
            raise RuntimeError("등록된 배송지가 없습니다.")
        return data[0]["id"]
    return default["id"]


# ─────────────────────────────────────────────────────────────
# 목록 조회
# ─────────────────────────────────────────────────────────────
def 내_판매입찰_목록(상태_필터: Optional[str] = None) -> list[dict]:
    """내 판매입찰 전체 페이지 순회 후 통합 리스트 반환.

    상태_필터:
        None      → 전체
        "입찰중"  → status_display == "입찰중" 만
        "만료"    → status_display == "만료" 만
    """
    result: list[dict] = []
    페이지 = 1
    while True:
        단건들 = _내_판매입찰_단일페이지(페이지)
        if not 단건들:
            break
        result.extend(단건들)
        페이지 += 1
        if 페이지 > _PAGE_SLEEP_AFTER:
            time.sleep(_PAGE_SLEEP_SEC)

    if 상태_필터 is not None:
        result = [d for d in result if d["상태"] == 상태_필터]
    return result


def _내_판매입찰_단일페이지(페이지: int) -> list[dict]:
    """단일 페이지 조회. 다음 페이지가 없으면 빈 리스트.

    KREAM 은 범위 밖 커서에 대해 404 Not Found 를 반환한다 (규격상 이상하지만
    실측 확인). 이를 '페이지 없음' 신호로 해석. 다른 에러는 그대로 전파.
    """
    params = {
        "per_page": str(_PAGE_SIZE),
        "cursor": 페이지,
        "start_date": "2020-01-01",
        "end_date": "2050-12-31",
    }
    response = http.get(_URL_ASKS_BIDDING, params=params)

    # KREAM: 범위 초과 커서 → 404 ("더 이상 없음" 신호로 간주)
    if response.status_code == 404:
        return []

    response.raise_for_status()
    data = response.json()
    items = data.get("items") or []
    return [_목록_아이템_정리(item) for item in items]


def _목록_아이템_정리(item: dict) -> dict:
    """KREAM 원시 응답 → bidbot 이 쓰는 최소 필드로 정리."""
    product = item.get("product") or {}
    release = product.get("release") or {}
    product_option = item.get("product_option") or {}
    price_breakdown = item.get("price_breakdown") or {}
    return {
        "id": item.get("id"),
        "product_id": item.get("product_id"),
        "option": product_option.get("key") or item.get("option"),
        "price": price_breakdown.get("price") or item.get("price"),
        "정산금액": price_breakdown.get("total_payout"),
        "수수료": (price_breakdown.get("processing_fee") or {}).get("value"),
        "상태": item.get("status_display"),
        "만료일": item.get("expires_at"),
        "입찰일": item.get("date_created"),
        "is_keep_on_deferred": item.get("is_keep_on_deferred"),
        "상품명_국문": release.get("translated_name"),
        "상품명_영문": release.get("name"),
        "품번": release.get("style_code"),
        "발매가": release.get("original_price"),
        "_raw": item,  # 디버깅용
    }


# ─────────────────────────────────────────────────────────────
# 등록
# ─────────────────────────────────────────────────────────────
def 판매입찰_등록(
    product_id: int | str,
    option: str,
    price: int,
    *,
    shipping_address_id: Optional[int] = None,
    is_keep_on_deferred: bool = False,
    expires_in: int = 180,
) -> dict:
    """신규 판매입찰 등록.

    shipping_address_id 미지정 시 기본 배송지 자동 사용.
    expires_in: 1/3/7/14/30/60/180 중 KREAM 허용값.

    반환:
        성공 시:  {"성공": True, "ask_id": int, "_raw": {...}}
        실패 시:  {"성공": False, "사유": str, "_raw": {...}}
    """
    if shipping_address_id is None:
        shipping_address_id = 기본_배송지_ID()

    payload = {
        "expires_in": expires_in,
        "product_id": str(product_id),   # 반드시 문자
        "option": str(option),           # 반드시 문자
        "price": price,
        "shipping_address_id": shipping_address_id,
        "is_keep_on_deferred": is_keep_on_deferred,
    }

    response = http.post(_URL_ASKS, json=payload)

    try:
        body = response.json()
    except ValueError:
        return {"성공": False, "사유": f"non-JSON 응답: {response.text[:300]}", "_raw": None}

    if body.get("status") == "live":
        return {"성공": True, "ask_id": body.get("id"), "_raw": body}

    사유 = body.get("message")
    error_fields = body.get("error_fields")
    if error_fields:
        사유 = f"{사유} ({error_fields})"
    if not 사유:
        사유 = f"알 수 없는 오류: {body}"
    return {"성공": False, "사유": 사유, "_raw": body}


# ─────────────────────────────────────────────────────────────
# 수정 (가격)
# ─────────────────────────────────────────────────────────────
def 판매입찰_가격수정(ask_id: int | str, 새_가격: int) -> dict:
    """기존 판매입찰의 가격만 변경.

    구현: 상세 GET → 기존 값 유지 + price만 교체 → 동일 POST /api/m/asks.

    반환:
        성공 시:  {"성공": True, "ask_id": ..., "새_가격": ..., "정산금액": int, "_raw": {...}}
        실패 시:  {"성공": False, "사유": str, "_raw": {...}}
    """
    상세 = _판매입찰_상세_조회(ask_id)
    if 상세 is None:
        return {"성공": False, "사유": f"ask_id={ask_id} 상세 조회 실패", "_raw": None}

    payload = {
        "id": ask_id,
        "expires_in": 상세["expires_in"],
        "is_instant": 상세["is_instant"],
        "product_id": 상세["product_id"],
        "option": 상세["option"],
        "price": 새_가격,
        "shipping_address_id": 상세["shipping_address_id"],
        "receipt_config_id": 상세["receipt_config_id"],
        "is_keep_on_deferred": 상세["is_keep_on_deferred"],
    }

    response = http.post(_URL_ASKS, json=payload)

    try:
        body = response.json()
    except ValueError:
        return {"성공": False, "사유": f"non-JSON 응답: {response.text[:300]}", "_raw": None}

    if "message" in body and "price" not in body:
        return {"성공": False, "사유": body["message"], "_raw": body}

    return {
        "성공": True,
        "ask_id": ask_id,
        "새_가격": body.get("price"),
        "정산금액": (body.get("price_breakdown") or {}).get("total_payout"),
        "_raw": body,
    }


def _판매입찰_상세_조회(ask_id: int | str) -> Optional[dict]:
    """수정 페이로드 구성을 위해 기존 입찰의 값을 가져온다."""
    response = http.get(_URL_ASK_DETAIL.format(ask_id=ask_id))
    if response.status_code != 200:
        return None
    try:
        body = response.json()
    except ValueError:
        return None
    try:
        return {
            "expires_in": body["expires_in"],
            "is_instant": body["is_instant"],
            "product_id": body["product_id"],
            "option": body["option"],
            "shipping_address_id": body["shipping_address"]["id"],
            "receipt_config_id": body["receipt"]["config"]["id"],
            "is_keep_on_deferred": body["is_keep_on_deferred"],
        }
    except (KeyError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────
# 삭제
# ─────────────────────────────────────────────────────────────
def 판매입찰_삭제(ask_id: int | str) -> dict:
    """판매입찰 취소.

    원본 로직: 응답 본문에 'Error' 가 들어있으면 유효하지 않은 ID로 판단.
              이미 삭제된 ID를 다시 호출해도 Error 는 안 뜸.

    반환:
        {"성공": True,  "ask_id": ...}
        {"성공": False, "ask_id": ..., "사유": "유효하지 않은 ID 혹은 이미 취소됨", "_raw": str}
    """
    response = http.request("DELETE", _URL_ASK_DETAIL.format(ask_id=ask_id))
    본문 = response.text or ""
    if "Error" in 본문:
        return {"성공": False, "ask_id": ask_id, "사유": "유효하지 않은 ID", "_raw": 본문[:300]}
    return {"성공": True, "ask_id": ask_id}
