# src/source_pool/discoverer.py
"""源发现器 - 多源抓取、去重、入库"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.config import IPTV_SOURCES
from src.fetcher import fetch_all_sources_incremental
from src.parser import parse_and_dedupe
from src.database import get_db_cache
from src.logger import logger
from src.source_pool.models import RawSource, SourceStatus


class SourceDiscoverer:
    """源发现器 - 负责从多个源抓取新源"""
    
    def __init__(self, pool_db_path: Path = None):
        self.pool_db_path = pool_db_path or Path("data/source_pool.json")
        self.pool_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.pool: Dict[str, RawSource] = {}
        self._load_pool()
    
    def _load_pool(self):
        """加载源池数据库"""
        if self.pool_db_path.exists():
            try:
                with open(self.pool_db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        # 转换时间字符串为 datetime
                        value["discovered_at"] = datetime.fromisoformat(value["discovered_at"])
                        if value.get("last_check"):
                            value["last_check"] = datetime.fromisoformat(value["last_check"])
                        self.pool[key] = RawSource.from_dict(value)
                logger.info(f"📦 加载源池: {len(self.pool)} 个源")
            except Exception as e:
                logger.warning(f"加载源池失败: {e}")
                self.pool = {}
    
    def _save_pool(self):
        """保存源池数据库"""
        try:
            data = {key: value.to_dict() for key, value in self.pool.items()}
            # 转换 datetime 为字符串
            for key, value in data.items():
                value["discovered_at"] = value["discovered_at"].isoformat()
                if value["last_check"]:
                    value["last_check"] = value["last_check"].isoformat()
            with open(self.pool_db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存源池失败: {e}")
    
    async def discover(self, db=None) -> Dict[str, List[RawSource]]:
        """发现新源，按频道名分组"""
        logger.info("🔍 开始发现新源...")
        
        # 拉取所有源
        raw_contents = await fetch_all_sources_incremental(IPTV_SOURCES, db)
        channels_dict = parse_and_dedupe(raw_contents)
        
        new_sources = []
        existing_keys = set(self.pool.keys())
        
        for ch in channels_dict.values():
            raw_source = RawSource(
                url=ch["url"],
                channel_name=ch["name"],
                source_url=ch.get("source_url", "unknown"),
                discovered_at=datetime.now(),
                status=SourceStatus.PENDING
            )
            key = raw_source.get_key()
            
            if key not in existing_keys:
                self.pool[key] = raw_source
                new_sources.append(raw_source)
            else:
                # 更新已有源的最后检查时间
                self.pool[key].last_check = datetime.now()
        
        self._save_pool()
        
        # 按频道名分组
        grouped = {}
        for src in new_sources:
            if src.channel_name not in grouped:
                grouped[src.channel_name] = []
            grouped[src.channel_name].append(src)
        
        logger.info(f"✅ 发现新源: {len(new_sources)} 个，涉及 {len(grouped)} 个频道")
        return grouped
    
    def get_pending_sources(self, limit: int = 100) -> List[RawSource]:
        """获取待验证的源"""
        pending = [s for s in self.pool.values() if s.status == SourceStatus.PENDING]
        return sorted(pending, key=lambda x: x.discovered_at)[:limit]
    
    def get_failed_sources(self, max_fail_count: int = 3) -> List[RawSource]:
        """获取失败次数过多的源"""
        return [s for s in self.pool.values() if s.fail_count >= max_fail_count]
    
    def update_source_status(self, source_key: str, status: str, 
                              latency: int = 0, success: bool = True):
        """更新源状态"""
        if source_key in self.pool:
            self.pool[source_key].status = status
            self.pool[source_key].last_check = datetime.now()
            if success:
                self.pool[source_key].success_count += 1
                self.pool[source_key].latency = latency
            else:
                self.pool[source_key].fail_count += 1
            self._save_pool()
    
    def get_statistics(self) -> dict:
        """获取源池统计信息"""
        stats = {
            "total": len(self.pool),
            "pending": sum(1 for s in self.pool.values() if s.status == SourceStatus.PENDING),
            "verified": sum(1 for s in self.pool.values() if s.status == SourceStatus.VERIFIED),
            "failed": sum(1 for s in self.pool.values() if s.status == SourceStatus.FAILED),
            "promoted": sum(1 for s in self.pool.values() if s.status == SourceStatus.PROMOTED),
        }
        return stats
