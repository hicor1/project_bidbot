"""
KREAM 이메일 로그인 API 호출 (Phase A 검증용)

원본: KREAM_BASE/Module/Function/KREAM_로그인.py
- KREAM_헤더_필수값_가져오기()
- KREAM_login_이메일_request()
에서 핵심만 발췌, 전역 dict/lock/보판driver 등 제거.
"""

import json
import re
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
        "referer": "https://kream.co.kr/search?keyword=847146WSDSD4191&tab=products",
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


def KREAM_필수헤더_가져오기(timeout=13):
    """
    kream.co.kr/login 페이지의 NUXT config 에서
    apiVersion, buildVersion, webRequestSecret, webDid 를 추출하여
    필수 헤더를 구성한다.
    """
    headers = 기본헤더_구성()

    response = requests.get(KREAM_LOGIN_PAGE, headers=headers, timeout=timeout)
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

    headers["x-kream-api-version"] = config_dict["apiVersion"]
    headers["x-kream-client-datetime"] = datetime.now().strftime("%Y%m%d%H%M%S+0900")
    headers["x-kream-web-build-version"] = config_dict["buildVersion"]
    headers["x-kream-web-request-secret"] = config_dict["webRequestSecret"]

    webDid = cookies_dict.get("webDid")
    if not webDid:
        raise RuntimeError("webDid 쿠키를 받지 못했습니다.")
    headers["x-kream-device-id"] = "web;" + webDid

    return headers


def KREAM_이메일_로그인(email, password, timeout=13):
    """
    성공 시 (True, access_token, 응답시간_ms, status, 응답본문_요약) 반환
    실패 시 (False, None, 응답시간_ms, status, 응답본문_요약) 반환
    """
    headers = KREAM_필수헤더_가져오기(timeout=timeout)

    payload = {"email": email, "password": password}

    t0 = datetime.now()
    response = requests.post(
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

    body_요약 = {k: v for k, v in body.items() if k != "access_token"} if isinstance(body, dict) else body

    성공 = response.status_code == 200 and bool(access_token)
    return 성공, access_token, 응답시간_ms, response.status_code, body_요약
