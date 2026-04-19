"""테스트 공통 설정.

- 프로젝트 루트의 .env 자동 로드 (python-dotenv 있으면 사용, 없으면 자체 파서)
- src import path 추가
- 세션 초기화 (markets.kream.session.configure)

.env 샘플:
    KREAM_EMAIL=your_email@example.com
    KREAM_PW=your_password
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(PROJECT_ROOT, "src")
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")

if SRC not in sys.path:
    sys.path.insert(0, SRC)


def _load_env_file(path: str) -> None:
    """python-dotenv 가 있으면 그걸로, 없으면 최소 파서로 KEY=VALUE 로드.

    - 이미 환경변수에 있으면 덮어쓰지 않음 (shell set 가 우선)
    - 따옴표 제거 (양쪽 " 또는 ')
    - # 로 시작하는 줄, 빈 줄 무시
    """
    if not os.path.exists(path):
        return

    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(path, override=False)
        return
    except ImportError:
        pass

    # Fallback 파서
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value


_load_env_file(ENV_FILE)


def init_session():
    """환경변수로부터 세션 초기화. 이후 markets.kream.* 자유 사용."""
    from markets.kream import session

    email = os.environ.get("KREAM_EMAIL")
    password = os.environ.get("KREAM_PW")
    if not email or not password:
        raise SystemExit(
            "[FAIL] KREAM_EMAIL / KREAM_PW 미설정.\n"
            f"  해결 1) 프로젝트 루트에 .env 파일 생성: {ENV_FILE}\n"
            "            KREAM_EMAIL=...\n"
            "            KREAM_PW=...\n"
            "  해결 2) 터미널 환경변수로 설정 후 실행"
        )

    session.configure(email=email, password=password)
    print(f"[session] 초기화 완료 ({session.snapshot()})")
