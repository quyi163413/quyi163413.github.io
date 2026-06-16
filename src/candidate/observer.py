# src/candidate/observer.py
"""候选版观察者 - 新源在这里观察验证"""

import asyncio
import json
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

from src.logger import logger
from src.speed_tester import probe_channel_advanced
from src.config import TIMEOUT
from src.candidate.models import ObservationResult, CandidateStatus


class CandidateObserver:
    """
    候选版观察者
    
    观察策略:
    - 观察期: 24小时
    - 最少成功次数: 10次
    - 成功率要求: > 80%
    - 平均延迟要求: < 2000ms
    """
    
    OBSERVATION_HOURS = 24      # 观察期24小时
    MIN_SUCCESS_COUNT = 10      # 最少成功10次
    MIN_SUCCESS_RATE = 0.8      # 成功率80%以上
    MAX_AVG_LATENCY = 2000      # 平均延迟2000ms以内
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Path("data/candidate_pool.json")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._observations: Dict[str, ObservationResult] = {}
        self._load()
    
    def _load(self):
        """加载观察数据"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self._observations[k] = ObservationResult.from_dict(v)
                logger.info(f"📦 加载候选池: {len(self._observations)} 个候选源")
            except Exception as e:
                logger.warning(f"加载候选池失败: {e}")
    
    def _save(self):
        """保存观察数据"""
        try:
            data = {k: v.to_dict() for k, v in self._observations.items()}
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存候选池失败: {e}")
    
    def add_candidate(self, source_key: str, channel_name: str, url: str):
        """添加候选源"""
        if source_key not in self._observations:
            self._observations[source_key] = ObservationResult(
                source_key=source_key,
                channel_name=channel_name,
                url=url
            )
            logger.info(f"📝 添加候选源: {channel_name}")
            self._save()
    
    async def check_candidate(self, source_key: str, session: aiohttp.ClientSession) -> bool:
        """检查单个候选源"""
        obs = self._observations.get(source_key)
        if not obs:
            return False
        
        # 已稳定或已提升的跳过
        if obs.status in [CandidateStatus.STABLE, CandidateStatus.PROMOTED]:
            return obs.status == CandidateStatus.STABLE
        
        # 执行检查
        channel = {"name": obs.channel_name, "url": obs.url}
        _, latency, ok, _ = await probe_channel_advanced(session, channel)
        
        obs.check_count += 1
        obs.last_check = datetime.now()
        
        if ok:
            obs.success_count += 1
            obs.total_latency += latency
        else:
            obs.fail_count += 1
        
        # 判断是否达到稳定标准
        if obs.check_count >= self.MIN_SUCCESS_COUNT:
            if (obs.success_rate >= self.MIN_SUCCESS_RATE and 
                obs.avg_latency <= self.MAX_AVG_LATENCY):
                obs.status = CandidateStatus.STABLE
                logger.info(f"✅ 候选源已稳定: {obs.channel_name} (成功率:{obs.success_rate:.1%}, 延迟:{obs.avg_latency:.0f}ms)")
                self._save()
                return True
        
        self._save()
        return obs.status == CandidateStatus.STABLE
    
    async def observe_all(self, concurrency: int = 10) -> List[ObservationResult]:
        """观察所有候选源，返回新稳定源列表"""
        candidates = [k for k, v in self._observations.items() 
                     if v.status == CandidateStatus.OBSERVING]
        if not candidates:
            return []
        
        logger.info(f"🔍 观察 {len(candidates)} 个候选源...")
        
        semaphore = asyncio.Semaphore(concurrency)
        stable_results = []
        
        async with aiohttp.ClientSession() as session:
            async def observe_one(key):
                async with semaphore:
                    if await self.check_candidate(key, session):
                        return self._observations.get(key)
                    return None
            
            tasks = [observe_one(key) for key in candidates]
            results = await asyncio.gather(*tasks)
            stable_results = [r for r in results if r]
        
        logger.info(f"✅ 观察完成: {len(stable_results)} 个源达到稳定标准")
        return stable_results
    
    def get_candidates(self) -> List[ObservationResult]:
        """获取所有候选源"""
        return list(self._observations.values())
    
    def get_stable_candidates(self) -> List[ObservationResult]:
        """获取已稳定的候选源"""
        return [v for v in self._observations.values() if v.status == CandidateStatus.STABLE]
    
    def mark_promoted(self, source_key: str):
        """标记为已提升"""
        if source_key in self._observations:
            self._observations[source_key].status = CandidateStatus.PROMOTED
            self._observations[source_key].promoted_at = datetime.now()
            self._save()
    
    def get_statistics(self) -> dict:
        """获取候选池统计"""
        stats = {
            "total": len(self._observations),
            "observing": sum(1 for v in self._observations.values() if v.status == CandidateStatus.OBSERVING),
            "stable": sum(1 for v in self._observations.values() if v.status == CandidateStatus.STABLE),
            "promoted": sum(1 for v in self._observations.values() if v.status == CandidateStatus.PROMOTED),
            "rejected": sum(1 for v in self._observations.values() if v.status == CandidateStatus.REJECTED),
        }
        return stats
