"""core 테스트 공통 부트스트랩 (sheets_test 와 동일 정책)."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(PROJECT_ROOT, "src")

if SRC not in sys.path:
    sys.path.insert(0, SRC)
