"""
Phase A 실행 엔트리.

환경변수:
  KREAM_EMAIL, KREAM_PW

출력 원칙:
  - access_token / 비밀번호 등 민감값은 절대 평문 출력 X
  - 토큰은 앞 8자 + "..." 마스킹
  - 에러 메시지 본문은 찍되, 쿠키/토큰 값은 찍지 않는다
"""

import os
import sys
import traceback
from datetime import datetime

from kream_login import KREAM_이메일_로그인


def 마스킹(값, head=8):
    if not 값:
        return "(없음)"
    if len(값) <= head:
        return "***"
    return 값[:head] + "..."


def main():
    print("=" * 60)
    print(f"[Phase A] KREAM 이메일 로그인 테스트")
    print(f"실행 시각: {datetime.now().isoformat()}")
    print("=" * 60)

    email = os.environ.get("KREAM_EMAIL")
    password = os.environ.get("KREAM_PW")

    if not email or not password:
        print("[FAIL] 환경변수 KREAM_EMAIL / KREAM_PW 가 설정되어 있지 않습니다.")
        sys.exit(2)

    print(f"계정: {email[:3]}***{email[email.find('@'):]}")
    print()

    try:
        성공, access_token, 응답시간_ms, status, body_요약 = KREAM_이메일_로그인(
            email=email, password=password
        )
    except Exception as exc:
        print(f"[FAIL] 예외 발생: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        sys.exit(1)

    print(f"HTTP status : {status}")
    print(f"응답시간    : {응답시간_ms} ms")
    print(f"access_token: {마스킹(access_token)}")
    print(f"응답 본문(토큰 제외): {body_요약}")
    print()

    if 성공:
        print("[OK] 로그인 성공 — Phase B 진행 가능")
        sys.exit(0)
    else:
        print("[FAIL] 로그인 실패 — 응답 본문 확인 필요")
        sys.exit(1)


if __name__ == "__main__":
    main()
