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
    
    async def get_selected_global_channels(self, force_refresh: bool = False) -> List[Dict]:
        """获取精选的全球频道（带 EPG ID）"""
        if not self.adapter.enabled or not ENABLE_GLOBAL_CHANNELS:
            return []
        
        channels_data = await self.adapter.fetch_global_channels(force_refresh=force_refresh)
        if not channels_data:
            return []
        
        selected = []
        for ch in channels_data:
            # 只选择有 EPG ID 的频道
            epg_id = ch.get("id")
            if epg_id:
                # 获取国家名称
                country_code = ch.get("country", "")
                country_name = self._get_country_name(country_code)
                
                selected.append({
                    "name": ch.get("name", epg_id),
                    "url": "",  # URL 需要从 streams 中获取，这里留空由后续处理
                    "tvg_id": epg_id,
                    "logo": self.adapter.get_logo_url(epg_id),
                    "group_title": f"全球·{country_name}" if country_name else "全球频道",
                    "categories": ch.get("categories", []),
                    "languages": ch.get("languages", []),
                    "country": country_code,
                    "is_global": True
                })
        
        # 限制数量
        selected = selected[:GLOBAL_CHANNELS_LIMIT]
        if selected:
            logger.info(f"🌍 精选 {len(selected)} 个全球频道")
        return selected
    
    def _get_country_name(self, country_code: str) -> str:
        """获取国家中文名称"""
        country_map = {
            "CN": "中国", "US": "美国", "UK": "英国", "JP": "日本",
            "KR": "韩国", "FR": "法国", "DE": "德国", "IT": "意大利",
            "ES": "西班牙", "CA": "加拿大", "AU": "澳大利亚", "RU": "俄罗斯",
            "IN": "印度", "BR": "巴西", "MX": "墨西哥", "ZA": "南非"
        }
        return country_map.get(country_code, country_code)
    
    async def merge_with_domestic(self, domestic_channels: List[Dict], lazy_load: bool = True) -> List[Dict]:
        """合并国内频道和全球精选频道
        
        Args:
            domestic_channels: 国内频道列表
            lazy_load: 是否懒加载（根据 demo 判断是否需要海外频道）
        """
        if not ENABLE_GLOBAL_CHANNELS:
            return domestic_channels
        
        if lazy_load:
            # 懒加载：检查是否需要海外频道
            has_overseas = False
            for ch in domestic_channels:
                name = ch.get("name", "")
                if any(kw in name for kw in ["海外", "国际", "CGTN", "BBC", "CNN", "FOX", "NHK"]):
                    has_overseas = True
                    break
            
            if not has_overseas:
                logger.info("⏭️ 跳过全球频道加载（未检测到海外频道需求）")
                return domestic_channels
        
        global_ch = await self.get_selected_global_channels()
        
        if not global_ch:
            return domestic_channels
        
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
