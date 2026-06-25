#!/usr/bin/env python3
# gui_main.py
"""IPTV 管理桌面应用 (PyQt5)"""

import os
import sys
import threading
import random
from pathlib import Path

# ========== 设置环境变量 ==========
os.environ["AUTONOMOUS_MODE"] = "true"
os.environ["ENABLE_DEMO_FILTER"] = "true"
os.environ["ENABLE_ALIAS"] = "true"
os.environ["ENABLE_BLACKLIST"] = "true"
os.environ["DATABASE_ENABLE"] = "true"
os.environ["FFMPEG_ENABLE"] = "false"  # Windows 下打包不包含 ffmpeg，暂时关闭
os.environ["MAX_WORKERS"] = "20"
os.environ["TIMEOUT"] = "15"
# 关闭代理，避免国内用户拉取失败
os.environ["ENABLE_GITHUB_PROXY"] = "false"

# ========== 切换工作目录 ==========
if getattr(sys, 'frozen', False):
    base_dir = Path(sys.executable).parent
    os.chdir(base_dir)
else:
    base_dir = Path(__file__).parent
    os.chdir(base_dir)

sys.path.insert(0, str(base_dir))

from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEngineSettings

from src.web.threaded_server import run_server_in_thread


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IPTV 智能管理")
        self.setGeometry(100, 100, 1200, 800)

        self.port = random.randint(49152, 65535)
        self.server_thread = threading.Thread(
            target=run_server_in_thread,
            args=(self.port,),
            daemon=True
        )
        self.server_thread.start()

        QTimer.singleShot(2000, self.load_web)

    def load_web(self):
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(f"http://127.0.0.1:{self.port}/"))
        self.setCentralWidget(self.browser)

    def on_load_finished(self, ok):
        if not ok:
            QMessageBox.warning(
                self,
                "连接失败",
                "无法连接到本地服务器，请检查防火墙或重启应用。"
            )


def main():
    app = QApplication(sys.argv)
    profile = QWebEngineProfile.defaultProfile()
    profile.setHttpCacheType(QWebEngineProfile.NoCache)
    settings = QWebEngineSettings.defaultSettings()
    settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
    settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
    settings.setAttribute(QWebEngineSettings.AutoLoadImages, True)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
