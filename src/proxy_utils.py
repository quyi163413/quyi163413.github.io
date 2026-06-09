# src/proxy_utils.py
import asyncio
import aiohttp
from typing import Optional, Tuple
from urllib.parse import urlparse

from src.config import (
    GITHUB_RAW_PROXIES, ENABLE_GITHUB_PROXY, GITHUB_PROXY_TIMEOUT,
    HEADERS, TIMEOUT
)
from src.logger import logger

def should_proxy(url: str) -> bool:
    """判断是否需要代理加速"""
    if not ENABLE_GITHUB_PROXY:
        return False
    return "raw.githubusercontent.com" in url

def build_proxy_url(original_url: str, proxy_prefix: str) -> str:
    """构建代理 URL"""
    if proxy_prefix.startswith(("https://ghproxy.net/", "https://gh.api.99988866.xyz/")):
        # 直接拼接
        return f"{proxy_prefix}{original_url}"
    elif "raw.staticdn.net" in proxy_prefix or "raw.githubusercontents.com" in proxy_prefix:
        parsed = urlparse(original_url)
        # 代理只替换域名部分
        return f"{proxy_prefix}{parsed.path}"
    else:
        return f"{proxy_prefix}{original_url}"

async def fetch_with_proxy_fallback(
    session: aiohttp.ClientSession,
    url: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    依次尝试代理镜像拉取，直到成功或全部失败。
    返回 (content, used_proxy_prefix)
    """
    if not should_proxy(url):
        try:
            async with session.get(url, timeout=TIMEOUT, headers=HEADERS) as resp:
                if resp.status == 200:
                    return await resp.text(), None
                return None, None
        except Exception as e:
            logger.debug(f"直连 {url} 失败: {e}")
            return None, None

    # 直连失败或代理功能已启用，走代理
    for proxy_prefix in GITHUB_RAW_PROXIES:
        proxy_url = build_proxy_url(url, proxy_prefix)
        try:
            async with session.get(proxy_url, timeout=GITHUB_PROXY_TIMEOUT, headers=HEADERS) as resp:
                if resp.status == 200:
                    logger.info(f"✅ 代理拉取成功: {proxy_prefix[:40]}...")
                    return await resp.text(), proxy_prefix
                else:
                    logger.debug(f"代理 {proxy_prefix} 返回 {resp.status}")
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ 代理 {proxy_prefix} 超时")
        except Exception as e:
            logger.debug(f"代理 {proxy_prefix} 失败: {e}")
        await asyncio.sleep(0.2)  # 稍微间隔，避免请求过快

    return None, None
