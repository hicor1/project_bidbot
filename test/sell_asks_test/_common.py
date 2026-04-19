"""테스트 공통 설정 — src import path + 세션 초기화."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "..", "src"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)


def init_session():
    """환경변수로부터 세션 초기화. 이후 markets.kream.* 자유 사용."""
    from markets.kream import session

    email = os.environ.get("KREAM_EMAIL")
    password = os.environ.get("KREAM_PW")
    if not email or not password:
        raise SystemExit("[FAIL] 환경변수 KREAM_EMAIL / KREAM_PW 필요")

    session.configure(email=email, password=password)
    print(f"[session] 초기화 완료 ({session.snapshot()})")
