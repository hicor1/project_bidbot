"""sheets 테스트 공통 — sell_asks_test/_common.py 와 동일 정책.

- 프로젝트 루트 .env 자동 로드 (python-dotenv 있으면 사용, 없으면 자체 파서)
- src import path 추가
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
    if not os.path.exists(path):
        return
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(path, override=False)
        return
    except ImportError:
        pass

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
