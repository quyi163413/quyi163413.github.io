#!/usr/bin/env python3
# src/server.py
# IPTV Web 服务器 - 提供文件服务、API 和 Web 管理界面

import os
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiohttp import web
from src.config import OUTPUT_DIR, WEB_SERVER_HOST, WEB_SERVER_PORT
from src.logger import logger
from src.web.api import setup_routes


def get_static_dir() -> Path:
    """获取静态文件目录"""
    return Path(__file__).parent / "web" / "static"


async def init_app():
    """初始化 Web 应用"""
    app = web.Application()

    # 注册 API 路由
    setup_routes(app)

    # 静态文件服务
    static_dir = get_static_dir()
    if static_dir.exists():
        app.router.add_static('/static', static_dir)
        logger.info(f"📁 静态文件目录: {static_dir}")
    else:
        logger.warning(f"⚠️ 静态文件目录不存在: {static_dir}")

    # 默认路由：返回管理界面
    async def index_handler(request):
        index_path = static_dir / "index.html"
        if index_path.exists():
            return web.FileResponse(index_path)
        return web.Response(text="管理界面未找到，请检查静态文件", status=404)

    app.router.add_get('/', index_handler)

    # 文件服务：提供 output 目录下的文件
    async def file_handler(request):
        filename = request.match_info.get('filename', '')
        if not filename:
            return web.Response(status=404)
        file_path = OUTPUT_DIR / filename
        if file_path.exists() and file_path.is_file():
            return web.FileResponse(file_path)
        return web.Response(status=404)

    app.router.add_get('/{filename}', file_handler)

    # 添加跨域支持
    @web.middleware
    async def cors_middleware(request, handler):
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    app.middlewares.append(cors_middleware)

    return app


def start_server():
    """启动 Web 服务器"""
    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    app = web.Application()
    # 注册路由
    setup_routes(app)

    # 静态文件
    static_dir = get_static_dir()
    if static_dir.exists():
        app.router.add_static('/static', static_dir)
        logger.info(f"📁 静态文件目录: {static_dir}")
    else:
        logger.warning(f"⚠️ 静态文件目录不存在: {static_dir}")

    # 默认首页
    async def index_handler(request):
        index_path = static_dir / "index.html"
        if index_path.exists():
            return web.FileResponse(index_path)
        return web.Response(text="管理界面未找到", status=404)
    app.router.add_get('/', index_handler)

    # 文件服务（output 目录）
    async def file_handler(request):
        filename = request.match_info.get('filename', '')
        if not filename:
            return web.Response(status=404)
        file_path = OUTPUT_DIR / filename
        if file_path.exists() and file_path.is_file():
            return web.FileResponse(file_path)
        return web.Response(status=404)
    app.router.add_get('/{filename}', file_handler)

    # CORS 中间件
    @web.middleware
    async def cors_middleware(request, handler):
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    app.middlewares.append(cors_middleware)

    # 启动服务
    logger.info(f"🌐 Web 管理界面启动: http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}/")
    logger.info(f"📄 播放列表: http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}/tv.m3u")
    logger.info(f"📄 TXT 列表: http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}/tv.txt")
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        logger.info("⏹️ 服务器已停止")
    except Exception as e:
        logger.exception(f"❌ 服务器启动失败: {e}")
        sys.exit(1)
