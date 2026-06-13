# src/epg_injector.py
"""EPG 信息注入模块：为 M3U 输出添加 tvg-id 和 tvg-logo"""

from typing import Dict, List, Optional
from src.iptv_org_adapter import get_iptv_org_adapter
from src.config import ENABLE_EPG_INJECTION
from src.logger import logger


class EPGInjector:
    """为频道注入 EPG 元数据"""
    
    def __init__(self):
        self.adapter = get_iptv_org_adapter()
        self.enabled = ENABLE_EPG_INJECTION and self.adapter.enabled
        self.injected_count = 0
        self._injection_cache: Dict[str, str] = {}
    
    def inject_epg_metadata(self, channels: List[Dict]) -> List[Dict]:
        """为频道列表注入 tvg-id 和 tvg-logo"""
        if not self.enabled:
            logger.info("⏭️ EPG 注入已跳过（适配器未启用或功能已禁用）")
            return channels
        
        self.injected_count = 0
        
        for ch in channels:
            channel_name = ch.get("name", "")
            
            # 检查缓存
            if channel_name in self._injection_cache:
                epg_id = self._injection_cache[channel_name]
            else:
                # 获取 EPG ID
                epg_id = self.adapter.get_epg_id(channel_name)
                self._injection_cache[channel_name] = epg_id
            
            if epg_id:
                ch["tvg_id"] = epg_id
                self.injected_count += 1
                
                # 如果频道没有 logo，从 iptv-org 获取
                if not ch.get("logo"):
                    ch["logo"] = self.adapter.get_logo_url(epg_id)
        
        if self.injected_count > 0:
            logger.info(f"📺 EPG 注入完成：{self.injected_count}/{len(channels)} 个频道已匹配")
        return channels
    
    def get_tvg_line(self, channel: Dict) -> str:
        """生成 EXTINF 中的 EPG 标签字符串"""
        tags = []
        
        if channel.get("tvg_id"):
            tags.append(f'tvg-id="{channel["tvg_id"]}"')
        if channel.get("logo"):
            tags.append(f'tvg-logo="{channel["logo"]}"')
        if channel.get("group_title"):
            tags.append(f'group-title="{channel["group_title"]}"')
        
        return " ".join(tags)


# 全局实例
_injector = None


def get_epg_injector() -> EPGInjector:
    global _injector
    if _injector is None:
        _injector = EPGInjector()
    return _injector
