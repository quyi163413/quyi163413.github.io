import sys
import asyncio
from PyQt5.QtCore import QThread, pyqtSignal, QObject

# 这个类用于在QThread中执行任务
class WorkerSignals(QObject):
    # 定义信号，用于向主线程发送日志消息
    log_signal = pyqtSignal(str)

class CollectionWorker(QThread):
    # 定义信号
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.loop = None

    def run(self):
        # 这里是后台线程的入口
        # 1. 创建一个新的事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 2. 执行你现有的采集主函数
        # 注意：需要将你项目中的 run.py 中的 main 函数改造为可导入的
        try:
            # 假设你的主采集函数在 src.run 中
            from src.run import main as collect_main
            # 由于 main 是 async 函数，需要用 asyncio 来运行
            self.loop.run_until_complete(collect_main())
        except Exception as e:
            self.log_signal.emit(f"❌ 采集过程发生错误: {e}")
        finally:
            if self.loop:
                self.loop.close()
            self.log_signal.emit("✅ 采集任务完成")
