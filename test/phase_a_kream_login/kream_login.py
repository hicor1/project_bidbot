"""
KREAM 이메일 로그인 API 호출 (Phase A 검증용)

원본: KREAM_BASE/Module/Function/KREAM_로그인.py
- KREAM_헤더_필수값_가져오기()
- KREAM_login_이메일_request()
에서 핵심만 발췌, 전역 dict/lock/보판driver 등 제거.

Phase A 디버깅 강화 (2026-04-19):
- /login GET 실패 시 응답 본문/헤더 출력
- 5xx 계열은 자동 재시도 (3회, 지수 백오프)
- referer 단순화 (고정 키워드 제거)
- requests.Session 사용 (쿠키/커넥션 재사용)
"""

import json
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup


KREAM_LOGIN_PAGE = "https://kream.co.kr/login"
KREAM_LOGIN_API = "https://api.kream.co.kr/api/auth/login"


def 기본헤더_구성():
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


def _페이지_GET_재시도(session, url, headers, timeout, 최대재시도=3):
    """
    5xx / 연결오류 시 재시도. 마지막 응답(또는 예외)을 함께 반환.
    """
    마지막_응답 = None
    마지막_예외 = None
    for 시도 in range(1, 최대재시도 + 1):
        try:
            response = session.get(url, headers=headers, timeout=timeout)
            마지막_응답 = response
            if response.status_code < 500:
                return response, None
            print(
                f"[WARN] GET {url} → HTTP {response.status_code} "
                f"(시도 {시도}/{최대재시도})"
            )
        except requests.RequestException as exc:
            마지막_예외 = exc
            print(
                f"[WARN] GET {url} → 예외 {type(exc).__name__}: {exc} "
                f"(시도 {시도}/{최대재시도})"
            )

        if 시도 < 최대재시도:
            대기 = 2 ** 시도  # 2, 4
            print(f"       {대기}s 대기 후 재시도")
            time.sleep(대기)

    return 마지막_응답, 마지막_예외


def _응답_진단_출력(response):
    """500 같은 이상 응답에서 서버/WAF 힌트 추출."""
    print("----- 응답 진단 -----")
    print(f"status         : {response.status_code}")
    관심_응답헤더 = [
        "server", "cf-ray", "cf-cache-status", "x-amz-cf-id",
        "x-powered-by", "x-cache", "via", "content-type",
    ]
    for k in 관심_응답헤더:
        v = response.headers.get(k)
        if v:
            print(f"{k:<15}: {v}")
    본문 = response.text or ""
    미리보기 = 본문[:600].replace("\n", " ")
    print(f"body preview   : {미리보기}")
    # WAF/차단 힌트
    힌트들 = []
    저 = 본문.lower()
    for 키 in ["cloudflare", "akamai", "cloudfront", "captcha",
              "access denied", "forbidden", "blocked", "rate limit"]:
        if 키 in 저:
            힌트들.append(키)
    if 힌트들:
        print(f"힌트           : {', '.join(힌트들)}")
    print("---------------------")


def KREAM_필수헤더_가져오기(timeout=13):
    """
    kream.co.kr/login 페이지의 NUXT config 에서
    apiVersion, buildVersion, webRequestSecret, webDid 를 추출하여
    필수 헤더를 구성한다.
    """
    session = requests.Session()
    headers = 기본헤더_구성()

    response, 예외 = _페이지_GET_재시도(
        session=session,
        url=KREAM_LOGIN_PAGE,
        headers=headers,
        timeout=timeout,
    )

    if 예외 is not None and response is None:
        raise RuntimeError(f"/login GET 연결 실패: {예외}")

    if response is None:
        raise RuntimeError("/login GET: 응답 없음")

    if response.status_code >= 400:
        _응답_진단_출력(response)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    cookies_dict = response.cookies.get_dict()

    script = soup.find("script", string=re.compile(r"window\.__NUXT__\.config"))
    if script is None:
        _응답_진단_출력(response)
        raise RuntimeError("NUXT config 스크립트를 찾지 못했습니다.")

    match = re.search(r"window\.__NUXT__\.config\s*=\s*({.*})", script.string)
    if match is None:
        raise RuntimeError("NUXT config 본문 파싱 실패")

    config_text = match.group(1)
    config_text = re.sub(r"(?<=\{|,)(\s*)([a-zA-Z0-9_]+)(\s*):", r'"\2":', config_text)
    config_text = re.sub(r",\s*([}\]])", r"\1", config_text)

    config_dict = json.loads(config_text)["public"]

    headers["x-kream-api-version"] = config_dict["apiVersion"]
    headers["x-kream-client-datetime"] = datetime.now().strftime("%Y%m%d%H%M%S+0900")
    headers["x-kream-web-build-version"] = config_dict["buildVersion"]
    headers["x-kream-web-request-secret"] = config_dict["webRequestSecret"]

    webDid = cookies_dict.get("webDid")
    if not webDid:
        raise RuntimeError("webDid 쿠키를 받지 못했습니다.")
    headers["x-kream-device-id"] = "web;" + webDid

    print(
        f"[OK] 필수헤더 획득 "
        f"(api={config_dict['apiVersion']}, build={config_dict['buildVersion']})"
    )
    return headers, session


def KREAM_이메일_로그인(email, password, timeout=13):
    """
    성공 시 (True, access_token, 응답시간_ms, status, 응답본문_요약) 반환
    실패 시 (False, None, 응답시간_ms, status, 응답본문_요약) 반환
    """
    headers, session = KREAM_필수헤더_가져오기(timeout=timeout)

    payload = {"email": email, "password": password}

    t0 = datetime.now()
    response = session.post(
        KREAM_LOGIN_API,
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    응답시간_ms = int((datetime.now() - t0).total_seconds() * 1000)

    try:
        body = response.json()
    except ValueError:
        body = {"_raw": response.text[:500]}

    access_token = body.get("access_token") if isinstance(body, dict) else None

    body_요약 = (
        {k: v for k, v in body.items() if k != "access_token"}
        if isinstance(body, dict)
        else body
    )

    if response.status_code >= 400:
        _응답_진단_출력(response)

    성공 = response.status_code == 200 and bool(access_token)
    return 성공, access_token, 응답시간_ms, response.status_code, body_요약
