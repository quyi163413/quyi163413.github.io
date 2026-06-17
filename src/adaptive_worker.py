# src/adaptive_worker.py
"""自适应并发控制模块"""

import asyncio
import time
from typing import Optional
from src.config import MIN_WORKERS, MAX_WORKERS, DYNAMIC_CONCURRENCY


class AdaptiveWorkerPool:
    """自适应并发池，根据任务成功率动态调整并发数"""
    
    def __init__(self, min_workers: int = 5, max_workers: int = 20):
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.current_workers = min_workers
        self.stats = {"success": 0, "fail": 0, "avg_latency": 0}
        self._last_adjust = time.time()
        self._sample_size = 0
    
    async def get_worker_count(self) -> int:
        """根据最近任务表现动态调整并发数"""
        if not DYNAMIC_CONCURRENCY:
            return self.max_workers
        
        now = time.time()
        if now - self._last_adjust < 10:  # 每10秒调整一次
            return self.current_workers
        
        total = self.stats["success"] + self.stats["fail"]
        if total < 20:  # 样本不足，保守
            return self.current_workers
        
        success_rate = self.stats["success"] / total
        
        if success_rate > 0.85 and self.current_workers < self.max_workers:
            self.current_workers = min(self.current_workers + 2, self.max_workers)
            self._last_adjust = now
        elif success_rate < 0.5 and self.current_workers > self.min_workers:
            self.current_workers = max(self.current_workers - 2, self.min_workers)
            self._last_adjust = now
        
        # 重置统计，避免持续影响
        self.stats = {"success": 0, "fail": 0, "avg_latency": 0}
        return self.current_workers
    
    def record_result(self, success: bool, latency: int):
        """记录任务结果"""
        if success:
            self.stats["success"] += 1
        else:
            self.stats["fail"] += 1
        # 指数移动平均延迟
        if self.stats["avg_latency"]:
            self.stats["avg_latency"] = int(self.stats["avg_latency"] * 0.7 + latency * 0.3)
        else:
            self.stats["avg_latency"] = latency


# 全局实例
_adaptive_pool = None


def get_adaptive_pool() -> AdaptiveWorkerPool:
    global _adaptive_pool
    if _adaptive_pool is None:
        _adaptive_pool = AdaptiveWorkerPool(MIN_WORKERS, MAX_WORKERS)
    return _adaptive_pool
