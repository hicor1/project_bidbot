"""
src/markets/kream/session.py 수동 테스트.

검증 항목:
1. configure() → 최초 로그인 성공, 토큰 획득
2. get_headers() 복수 호출 → 같은 토큰 반환 (불필요한 재로그인 X)
3. force_refresh() → 토큰 재발급 (last_login_at 갱신)
4. is_valid() → 현재 세션이 KREAM 서버에서 유효한지 확인

실행:
  set KREAM_EMAIL=...
  set KREAM_PW=...
  C:\\Users\\hicor\\miniconda3\\envs\\spyder\\python.exe -X utf8 test\\session_test\\test_session.py
"""

import os
import sys
import time

# src 를 import path 에 추가 (pyproject.toml 의 src-layout 때문)
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "src"))
sys.path.insert(0, SRC)

from markets.kream import session  # noqa: E402


def 구분선(제목):
    print()
    print("=" * 60)
    print(제목)
    print("=" * 60)


def main():
    email = os.environ.get("KREAM_EMAIL")
    password = os.environ.get("KREAM_PW")
    if not email or not password:
        print("[FAIL] KREAM_EMAIL / KREAM_PW 환경변수 필요")
        sys.exit(2)

    구분선("1. configure() — 최초 로그인")
    session.configure(email=email, password=password)
    스냅샷1 = session.snapshot()
    print(f"snapshot: {스냅샷1}")
    assert 스냅샷1["logged_in"], "로그인 실패"
    print("[OK] 최초 로그인 성공")

    구분선("2. get_headers() 연속 호출 — 같은 토큰이어야 함 (재로그인 X)")
    h1 = session.get_headers()
    time.sleep(1)
    h2 = session.get_headers()
    스냅샷2 = session.snapshot()
    print(f"토큰 동일 여부: {h1['authorization'] == h2['authorization']}")
    assert h1["authorization"] == h2["authorization"], "불필요한 재로그인 발생"
    assert 스냅샷2["last_login_at"] == 스냅샷1["last_login_at"], (
        "last_login_at 이 변했음 (재로그인이 불필요하게 발생)"
    )
    print("[OK] 캐시된 헤더 재사용 확인")

    구분선("3. force_refresh() — 명시적 재로그인")
    이전_토큰 = 스냅샷2["access_token"]
    time.sleep(1)
    session.force_refresh()
    스냅샷3 = session.snapshot()
    print(f"이전 토큰: {이전_토큰}")
    print(f"새 토큰  : {스냅샷3['access_token']}")
    print(f"last_login_at 갱신: {스냅샷2['last_login_at']} → {스냅샷3['last_login_at']}")
    assert 스냅샷3["last_login_at"] != 스냅샷2["last_login_at"], (
        "force_refresh 후에도 last_login_at 이 변하지 않음"
    )
    print("[OK] 강제 재로그인 동작 확인")

    구분선("4. is_valid() — 현재 세션 서버측 유효성")
    유효 = session.is_valid()
    print(f"is_valid = {유효}")
    if 유효:
        print("[OK] 서버측 세션 유효")
    else:
        print("[WARN] 서버측 세션 무효 — 네트워크/차단/아이디 문제 점검 필요")

    구분선("전체 통과")


if __name__ == "__main__":
    main()
