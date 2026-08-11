from __future__ import annotations

import sys
from pathlib import Path

# 允许“不安装项目，直接 python run.py”。
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from upscaler.app import main


if __name__ == "__main__":
    main()
