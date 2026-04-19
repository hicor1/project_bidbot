"""
KREAM API 호출 래퍼 — 한 파일, 한 책임.

책임: KREAM API 요청 시 인증 오류(401/403)를 감지하고 세션을 갱신한 뒤 1회 재시도.

다른 모듈(prices.py, listings.py 등)은 requests 를 직접 쓰지 않고 이 래퍼의
request() / get() / post() 를 사용한다. 세션 헤더는 session.get_headers() 가 공급.
"""

from __future__ import annotations

from typing import Optional

import requests

from . import session


_AUTH_FAIL_STATUSES = {401, 403}


def request(
    method: str,
    url: str,
    *,
    params: Optional[dict] = None,
    json: Optional[dict] = None,
    timeout: float = 13,
    extra_headers: Optional[dict] = None,
) -> requests.Response:
    """KREAM API 1회 호출. 401/403 발생 시 세션 갱신 후 1회 재시도.

    extra_headers: 기본 인증 헤더 위에 덮어쓸 값 (예: referer 변경)
    """
    response = _send(method, url, params=params, json=json, timeout=timeout,
                     extra_headers=extra_headers)
    if response.status_code in _AUTH_FAIL_STATUSES:
        print(f"[http] {response.status_code} 감지 → 세션 갱신 후 재시도: {url}")
        session.force_refresh()
        response = _send(method, url, params=params, json=json, timeout=timeout,
                         extra_headers=extra_headers)
    return response


def get(url: str, **kwargs) -> requests.Response:
    return request("GET", url, **kwargs)


def post(url: str, **kwargs) -> requests.Response:
    return request("POST", url, **kwargs)


def _send(
    method: str,
    url: str,
    *,
    params: Optional[dict],
    json: Optional[dict],
    timeout: float,
    extra_headers: Optional[dict],
) -> requests.Response:
    headers = session.get_headers()
    if extra_headers:
        headers.update(extra_headers)
    return requests.request(
        method,
        url,
        headers=headers,
        params=params,
        json=json,
        timeout=timeout,
    )
