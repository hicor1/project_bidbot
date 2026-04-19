"""
KREAM 세션 신선도 관리 — 한 파일, 한 책임.

책임: KREAM API 호출에 필요한 유효한 헤더(토큰 포함)를 어떤 시점에도 제공한다.
- 최초 로그인 (이메일 → access_token)
- 필수헤더 획득 (NUXT config → apiVersion / buildVersion / webRequestSecret / webDid)
- 토큰 신선도 유지 (선제적 재로그인 + 외부 요청의 강제 재로그인 수용)
- 동시 접근 보호 (threading.Lock)

외부 모듈은 반드시 get_headers() 로만 접근한다.
내부 상태 _state 를 다른 파일에서 직접 import/수정하지 말 것.

원본 참조: KREAM_BASE/Module/Function/KREAM_로그인.py
  - KREAM_헤더_필수값_가져오기
  - KREAM_login_이메일_request
  - KREAM_로그인_정보 (글로벌 dict)
원본 참조: KREAM_BASE/Module/Function/KREAM_로그인체크.py
  - 로그인_유효_체크 (GET /my/profile)
원본 참조: KREAM_BASE/Module/Function/KREAM_로그인유지.py
  - 선제적 90분 재로그인 + 30초 단위 로그아웃 감지
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup


KREAM_LOGIN_PAGE = "https://kream.co.kr/login"
KREAM_LOGIN_API = "https://api.kream.co.kr/api/auth/login"
KREAM_PROFILE_URL = "https://kream.co.kr/my/profile"

# 선제적 재로그인 주기. KREAM이 약 2시간마다 토큰 만료시키므로 여유 있게.
_REFRESH_INTERVAL = timedelta(minutes=90)


_state = {
    "email": None,          # type: Optional[str]
    "password": None,       # type: Optional[str]
    "api_version": None,
    "build_version": None,
    "web_request_secret": None,
    "device_id": None,
    "access_token": None,
    "base_headers": None,   # 비로그인 필수헤더
    "auth_headers": None,   # 필수헤더 + Authorization Bearer
    "last_login_at": None,  # type: Optional[datetime]
}

_lock = threading.Lock()


# ─────────────────────────────────────────────────────────────
# Public API — 외부 모듈은 이 함수들만 호출한다
# ─────────────────────────────────────────────────────────────
def configure(email: str, password: str) -> None:
    """프로세스 시작 시 1회 호출. 자격증명 등록 + 첫 로그인."""
    with _lock:
        _state["email"] = email
        _state["password"] = password
        _login_locked()


def get_headers() -> dict:
    """항상 신선한 인증 헤더 반환. 필요 시 내부에서 재로그인.

    반환값은 복사본 — 호출자가 수정해도 내부 상태 영향 없음.
    """
    with _lock:
        if _refresh_needed_locked():
            _login_locked()
        if _state["auth_headers"] is None:
            raise RuntimeError(
                "KREAM 세션이 초기화되지 않았습니다. configure() 먼저 호출하세요."
            )
        return dict(_state["auth_headers"])


def force_refresh() -> None:
    """외부에서 401/403 감지 시 명시적 재로그인 요청."""
    with _lock:
        _login_locked()


def is_valid() -> bool:
    """현재 토큰이 KREAM 서버 기준으로 유효한지 실제 확인.

    원본: KREAM_로그인체크.로그인_유효_체크
    정기 헬스체크용. 실패하면 force_refresh() 로 복구 가능.
    """
    try:
        headers = get_headers()
        token = headers["authorization"].split("Bearer")[1].strip()
        cookies = {"_token.local.p-2": token}
        response = requests.get(
            KREAM_PROFILE_URL,
            cookies=cookies,
            headers=headers,
            timeout=10,
        )
        return "휴대폰 번호" in response.text
    except Exception as exc:
        print(f"[session] is_valid 오류: {exc}")
        return False


def snapshot() -> dict:
    """디버깅용 상태 스냅샷. 민감값 마스킹."""
    with _lock:
        token = _state["access_token"]
        return {
            "email": _state["email"],
            "api_version": _state["api_version"],
            "build_version": _state["build_version"],
            "device_id": _state["device_id"],
            "access_token": (token[:8] + "...") if token else None,
            "last_login_at": (
                _state["last_login_at"].isoformat()
                if _state["last_login_at"] else None
            ),
            "logged_in": _state["auth_headers"] is not None,
        }


# ─────────────────────────────────────────────────────────────
# Internal — _lock 을 이미 잡은 상태에서만 호출한다
# ─────────────────────────────────────────────────────────────
def _refresh_needed_locked() -> bool:
    if _state["auth_headers"] is None:
        return True
    last = _state["last_login_at"]
    if last is None:
        return True
    return datetime.now() - last > _REFRESH_INTERVAL


def _login_locked() -> None:
    email = _state["email"]
    password = _state["password"]
    if not email or not password:
        raise RuntimeError(
            "KREAM 자격증명이 없습니다. configure(email, password) 먼저 호출하세요."
        )

    base_headers = _fetch_base_headers()
    token = _email_login(base_headers, email, password)

    _state["base_headers"] = base_headers
    _state["auth_headers"] = {**base_headers, "authorization": f"Bearer {token}"}
    _state["access_token"] = token
    _state["api_version"] = base_headers.get("x-kream-api-version")
    _state["build_version"] = base_headers.get("x-kream-web-build-version")
    _state["device_id"] = base_headers.get("x-kream-device-id")
    _state["last_login_at"] = datetime.now()

    print(
        f"[session] 로그인 갱신 완료 "
        f"(api={_state['api_version']}, build={_state['build_version']})"
    )


def _default_base_headers() -> dict:
    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "cache-control": "no-cache",
        "origin": "https://kream.co.kr",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://kream.co.kr/",
        "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/137.0.0.0 Safari/537.36"
        ),
        "content-type": "application/json",
    }


def _fetch_base_headers() -> dict:
    """KREAM NUXT config 를 파싱해 필수헤더 구성."""
    headers = _default_base_headers()
    response = requests.get(KREAM_LOGIN_PAGE, headers=headers, timeout=13)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    cookies_dict = response.cookies.get_dict()

    script = soup.find("script", string=re.compile(r"window\.__NUXT__\.config"))
    if script is None:
        raise RuntimeError("NUXT config 스크립트를 찾지 못했습니다.")

    match = re.search(r"window\.__NUXT__\.config\s*=\s*({.*})", script.string)
    if match is None:
        raise RuntimeError("NUXT config 본문 파싱 실패")

    config_text = match.group(1)
    config_text = re.sub(r"(?<=\{|,)(\s*)([a-zA-Z0-9_]+)(\s*):", r'"\2":', config_text)
    config_text = re.sub(r",\s*([}\]])", r"\1", config_text)
    config_dict = json.loads(config_text)["public"]

    webDid = cookies_dict.get("webDid")
    if not webDid:
        raise RuntimeError("webDid 쿠키를 받지 못했습니다.")

    headers["x-kream-api-version"] = config_dict["apiVersion"]
    headers["x-kream-client-datetime"] = datetime.now().strftime("%Y%m%d%H%M%S+0900")
    headers["x-kream-web-build-version"] = config_dict["buildVersion"]
    headers["x-kream-web-request-secret"] = config_dict["webRequestSecret"]
    headers["x-kream-device-id"] = "web;" + webDid
    return headers


def _email_login(base_headers: dict, email: str, password: str) -> str:
    """이메일/비밀번호로 로그인 → access_token 반환."""
    payload = {"email": email, "password": password}
    response = requests.post(
        KREAM_LOGIN_API,
        headers=base_headers,
        json=payload,
        timeout=13,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"KREAM 로그인 실패: status={response.status_code}, body={response.text[:300]}"
        )
    body = response.json()
    token = body.get("access_token")
    if not token:
        raise RuntimeError(f"access_token 이 응답에 없음: {body}")
    return token
