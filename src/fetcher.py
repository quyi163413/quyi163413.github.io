# src/fetcher.py
# 源拉取模块：支持缓存、ETag/Last-Modified 检测、增量更新

import asyncio
import aiohttp
from src.config import HEADERS, TIMEOUT, RETRY_MAX_ATTEMPTS, RETRY_BACKOFF_FACTOR, RETRY_MAX_WAIT, ENABLE_RETRY
from src.database import get_db_cache

class FetchError(Exception):
    pass

async def check_source_update(url: str) -> tuple:
    """
    检查源是否有更新，返回 (has_update, new_etag, new_last_modified)
    通过 HEAD 请求获取 ETag 和 Last-Modified，与数据库缓存对比。
    """
    db = await get_db_cache()
    cached_etag, cached_last_modified = await db.get_raw_headers(url)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.head(url, timeout=TIMEOUT, headers=HEADERS, allow_redirects=True) as resp:
                if resp.status == 200:
                    new_etag = resp.headers.get('ETag', '')
                    new_last_modified = resp.headers.get('Last-Modified', '')
                    # 如果 ETag 或 Last-Modified 有变化，则认为有更新
                    if (new_etag and new_etag != cached_etag) or (new_last_modified and new_last_modified != cached_last_modified):
                        return True, new_etag, new_last_modified
                    else:
                        return False, new_etag, new_last_modified
                else:
                    # 如果 HEAD 失败，认为有更新（重新拉取）
                    return True, '', ''
        except Exception:
            return True, '', ''

async def fetch_url_with_cache(session, url: str, force: bool = False) -> str:
    """
    拉取单个 URL 内容，支持缓存。如果 force=True，则强制拉取并更新缓存。
    """
    db = await get_db_cache()
    if not force:
        cached = await db.get_raw_source(url)
        if cached is not None:
            print(f"📦 使用缓存: {url}")
            return cached

    attempt = 0
    while True:
        attempt += 1
        try:
            async with session.get(url, timeout=TIMEOUT, headers=HEADERS) as resp:
                if resp.status != 200:
                    raise FetchError(f"HTTP {resp.status}")
                content = await resp.text()
                # 保存到缓存，同时保存 etag 和 last_modified
                etag = resp.headers.get('ETag', '')
                last_modified = resp.headers.get('Last-Modified', '')
                await db.set_raw_source(url, content, etag, last_modified)
                return content
        except Exception as e:
            if not ENABLE_RETRY or attempt >= RETRY_MAX_ATTEMPTS:
                raise FetchError(str(e))
            wait_time = min(RETRY_BACKOFF_FACTOR ** (attempt - 1), RETRY_MAX_WAIT)
            print(f"  重试 {url} ({attempt}/{RETRY_MAX_ATTEMPTS})，等待 {wait_time}s")
            await asyncio.sleep(wait_time)

async def fetch_all_sources(sources: list, incremental: bool = True) -> dict:
    """
    并行拉取所有源，支持增量更新。
    返回 {url: content} 字典，对于未更新的源使用缓存内容。
    """
    # 1. 检查每个源是否有更新
    update_tasks = [check_source_update(url) for url in sources]
    update_results = await asyncio.gather(*update_tasks)
    urls_to_fetch = []
    for url, (has_update, new_etag, new_last_modified) in zip(sources, update_results):
        if has_update:
            print(f"🔄 源有更新: {url}")
            urls_to_fetch.append(url)
        else:
            print(f"✅ 源无变化: {url}")

    # 2. 并行拉取有更新的源
    async with aiohttp.ClientSession() as session:
        fetch_tasks = [fetch_url_with_cache(session, url, force=True) for url in urls_to_fetch]
        fetched_contents = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        result = {}
        # 处理拉取结果
        for url, content in zip(urls_to_fetch, fetched_contents):
            if isinstance(content, Exception):
                print(f"⚠️ 拉取失败 {url}: {content}")
                # 拉取失败时，尝试使用旧缓存
                db = await get_db_cache()
                cached = await db.get_raw_source(url)
                result[url] = cached
            else:
                result[url] = content
        # 未更新的源，从缓存获取内容
        for url in sources:
            if url not in result:
                db = await get_db_cache()
                cached = await db.get_raw_source(url)
                result[url] = cached
    return result
