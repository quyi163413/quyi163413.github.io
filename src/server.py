#!/usr/bin/env python3
# src/server.py
"""Web 管理界面服务入口（Flask 版本）"""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web.app import run_server

if __name__ == "__main__":
    run_server()
