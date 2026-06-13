# src/global_channels.py
"""全球频道精选模块：从 iptv-org 源生成精选海外频道"""

import asyncio
from typing import List, Dict
from src.iptv_org_adapter import get_iptv_org_adapter
from src.config import ENABLE_GLOBAL_CHANNELS, GLOBAL_CHANNELS_LIMIT
from src.logger import logger

class GlobalChannelSelector:
    """全球频道精选器"""
    
    def __init__(self):
        self.adapter = get_iptv_org_adapter()
    
    async def get_selected_global_channels(self) -> List[Dict]:
        """获取精选的全球频道（带 EPG ID）"""
        if not self.adapter.enabled or not ENABLE_GLOBAL_CHANNELS:
            return []
        
        channels_data = await self.adapter.fetch_global_channels()
        if not channels_data:
            return []
        
        selected = []
        for ch in channels_data:
            # 只选择有稳定源的频道（在 index.m3u 中存在）
            epg_id = ch.get("id")
            if epg_id:
                selected.append({
                    "name": ch.get("name", epg_id),
                    "url": f"https://iptv-org.github.io/iptv/streams/{epg_id}.m3u8",  # 占位，实际需解析
                    "tvg_id": epg_id,
                    "logo": self.adapter.get_logo_url(epg_id),
                    "group_title": f"全球·{ch.get('country', 'Other')}",
                    "categories": ch.get("categories", [])
                })
        
        # 限制数量
        selected = selected[:GLOBAL_CHANNELS_LIMIT]
        logger.info(f"🌍 精选 {len(selected)} 个全球频道")
        return selected
    
    async def merge_with_domestic(self, domestic_channels: List[Dict]) -> List[Dict]:
        """合并国内频道和全球精选频道"""
        global_ch = await self.get_selected_global_channels()
        
        # 去重：避免重复添加已经在国内列表中的频道
        domestic_names = {ch["name"] for ch in domestic_channels}
        new_global = [ch for ch in global_ch if ch["name"] not in domestic_names]
        
        merged = domestic_channels + new_global
        logger.info(f"📊 合并后总频道数: {len(merged)} (国内 {len(domestic_channels)} + 全球 {len(new_global)})")
        return merged

# 全局实例
_selector = None

def get_global_selector() -> GlobalChannelSelector:
    global _selector
    if _selector is None:
        _selector = GlobalChannelSelector()
    return _selector
