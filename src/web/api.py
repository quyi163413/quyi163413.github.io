# src/web/api.py
"""REST API 接口"""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from aiohttp import web

from src.stable import StableManager
from src.source_pool import SourceDiscoverer
from src.candidate import CandidateObserver
from src.config import (
    MAX_WORKERS, TIMEOUT, FFMPEG_ENABLE,
    MAX_SOURCES_PER_CHANNEL, CACHE_HOURS
)
from src.logger import logger


class APIHandler:
    """API 路由处理器"""

    def __init__(self):
        self.stable_manager = StableManager()
        self.discoverer = SourceDiscoverer()
        self.candidate_observer = CandidateObserver()

    async def get_status(self, request: web.Request) -> web.Response:
        """获取系统状态"""
        stable_sources = self.stable_manager.get_active_sources()
        fixed_sources = {n: s for n, s in self.stable_manager.stable_sources.items() if s.is_fixed}

        # 获取候选池统计
        candidate_stats = self.candidate_observer.get_statistics()
        source_stats = self.discoverer.get_statistics()

        status = {
            "stable_count": len(stable_sources),
            "fixed_count": len(fixed_sources),
            "candidate_pool": candidate_stats,
            "source_pool": source_stats,
            "last_update": "2026-06-22 10:00:00",  # TODO: 从数据库读取最后更新时间
            "config": {
                "max_workers": MAX_WORKERS,
                "timeout": TIMEOUT,
                "ffmpeg_enable": FFMPEG_ENABLE,
                "max_sources_per_channel": MAX_SOURCES_PER_CHANNEL,
                "cache_hours": CACHE_HOURS,
            },
            "timestamp": datetime.now().isoformat(),
        }
        return web.json_response(status)

    async def get_channels(self, request: web.Request) -> web.Response:
        """获取稳定版频道列表，支持搜索和筛选"""
        query = request.query
        search = query.get("search", "").strip().lower()
        category = query.get("category", "").strip()
        fixed_only = query.get("fixed_only", "false").lower() == "true"

        channels = []
        for name, src in self.stable_manager.stable_sources.items():
            if src.status != "active":
                continue

            # 搜索过滤
            if search and search not in name.lower():
                continue

            # 固定源过滤
            if fixed_only and not src.is_fixed:
                continue

            # 分类筛选（需要从频道名推断分类，或从demo匹配）
            if category:
                # 简单分类推断
                cat = self._infer_category(name)
                if category != cat:
                    continue

            # 获取延迟和编码
            latency = src.latency if src.latency else 0
            codec = src.video_codec or "unknown"

            channels.append({
                "name": name,
                "url": src.url,
                "latency": latency,
                "codec": codec,
                "is_fixed": src.is_fixed,
                "category": self._infer_category(name),
                "last_verified": src.last_verified.isoformat() if src.last_verified else None,
                "fail_count": src.fail_count,
            })

        # 按名称排序
        channels.sort(key=lambda x: x["name"])
        return web.json_response({
            "total": len(channels),
            "channels": channels
        })

    def _infer_category(self, name: str) -> str:
        """简单推断频道分类"""
        name_lower = name.lower()
        if "cctv" in name_lower or "央视" in name:
            return "央视"
        if "卫视" in name:
            return "卫视"
        if any(p in name for p in ["北京", "上海", "广东", "浙江", "江苏", "湖南"]):
            return "地方"
        if any(kw in name_lower for kw in ["香港", "澳门", "台湾", "tvb", "凤凰"]):
            return "港澳台"
        return "其他"

    async def add_fixed_source(self, request: web.Request) -> web.Response:
        """添加固定源"""
        try:
            data = await request.json()
            name = data.get("name", "").strip()
            url = data.get("url", "").strip()

            if not name or not url:
                return web.json_response({"error": "频道名和URL不能为空"}, status=400)

            # 检查是否已存在
            if name in self.stable_manager.stable_sources:
                existing = self.stable_manager.stable_sources[name]
                if existing.is_fixed:
                    return web.json_response({"error": f"频道 {name} 已是固定源"}, status=409)

            # 添加固定源
            success = self.stable_manager.set_fixed_source(name, url)
            if success:
                logger.info(f"📌 通过 Web 管理界面添加固定源: {name}")
                return web.json_response({"message": f"已添加固定源: {name}"})
            else:
                return web.json_response({"error": "添加失败，请检查URL是否有效"}, status=500)

        except Exception as e:
            logger.error(f"添加固定源失败: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def remove_fixed_source(self, request: web.Request) -> web.Response:
        """删除固定源"""
        try:
            name = request.match_info.get("name", "").strip()
            if not name:
                return web.json_response({"error": "频道名不能为空"}, status=400)

            success = self.stable_manager.remove_fixed_source(name)
            if success:
                logger.info(f"🗑️ 通过 Web 管理界面删除固定源: {name}")
                return web.json_response({"message": f"已删除固定源: {name}"})
            else:
                return web.json_response({"error": f"频道 {name} 不是固定源或不存在"}, status=404)

        except Exception as e:
            logger.error(f"删除固定源失败: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def get_config(self, request: web.Request) -> web.Response:
        """获取当前配置"""
        config = {
            "max_workers": MAX_WORKERS,
            "timeout": TIMEOUT,
            "ffmpeg_enable": FFMPEG_ENABLE,
            "max_sources_per_channel": MAX_SOURCES_PER_CHANNEL,
            "cache_hours": CACHE_HOURS,
            "autonomous_mode": False,  # TODO: 读取环境变量
        }
        return web.json_response(config)

    async def update_config(self, request: web.Request) -> web.Response:
        """更新配置（需要重启生效）"""
        # 简单实现：只记录日志，返回提示
        return web.json_response({"message": "配置已更新，请重启服务生效"}, status=200)


def setup_routes(app: web.Application):
    """注册 API 路由"""
    handler = APIHandler()
    app.router.add_get("/api/status", handler.get_status)
    app.router.add_get("/api/channels", handler.get_channels)
    app.router.add_post("/api/fixed_sources", handler.add_fixed_source)
    app.router.add_delete("/api/fixed_sources/{name}", handler.remove_fixed_source)
    app.router.add_get("/api/config", handler.get_config)
    app.router.add_post("/api/config", handler.update_config)
