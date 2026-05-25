#!/usr/bin/env python3
import asyncio
import sys
import os
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import (
    IPTV_SOURCES, ENABLE_REGION_FILTER, PREFERRED_LOCATION, PREFERRED_ISP,
    ENABLE_IP_RESOLVE, ENABLE_DEMO_FILTER, ENABLE_ALIAS, ENABLE_BLACKLIST,
    DATABASE_ENABLE, CACHE_EXPIRY_SECONDS, DATABASE_TABLE
)
from src.fetcher import fetch_all_sources, check_sources_changed
from src.parser import parse_and_dedupe
from src.speed_tester import test_channels_concurrent
from src.ffmpeg_validator import validate_batch, cleanup as ffmpeg_cleanup
from src.classifier import classify_and_filter
from src.generator import generate_outputs_from_demo
from src.merger import merge_channels_by_name
from src.ip_resolver import get_resolver, matches_region
from src.blacklist_filter import get_blacklist_filter
from src.demo_filter import filter_and_order_by_demo
from src.alias_matcher import get_alias_matcher
from src.database import get_db_cache, channel_key

async def init_ip_resolver():
    if not ENABLE_IP_RESOLVE:
        print("⚙️ IP解析未启用")
        return
    resolver = get_resolver()
    if resolver.is_available:
        print("✅ IP解析器已就绪")
    else:
        print("⚠️ IP解析器不可用，将跳过地域筛选")

def filter_by_region(channels):
    if not ENABLE_REGION_FILTER:
        return channels
    preferred_locations = [loc.strip() for loc in PREFERRED_LOCATION.split(",") if loc.strip()]
    preferred_isps = [isp.strip() for isp in PREFERRED_ISP.split(",") if isp.strip()]
    if not preferred_locations and not preferred_isps:
        return channels
    print(f"🎯 地域筛选: 地域={preferred_locations}, 运营商={preferred_isps}")
    resolver = get_resolver()
    if not resolver.is_available:
        print("⚠️ IP解析器不可用，跳过地域筛选")
        return channels
    filtered = []
    for ch in channels:
        ip_info = ch.get("ip_info")
        if ip_info and matches_region(ip_info, preferred_locations, preferred_isps):
            filtered.append(ch)
    print(f"  筛选结果: {len(filtered)}/{len(channels)} 个频道通过地域筛选")
    return filtered

async def load_from_cache(db) -> list:
    """从数据库加载所有有效的频道源"""
    if not db._conn:
        return []
    table = f"{DATABASE_TABLE}_speed"
    try:
        cursor = await db._conn.execute(f'SELECT name, url, latency, video_codec, ip_info FROM {table}')
        rows = await cursor.fetchall()
        await cursor.close()
        channels = []
        for row in rows:
            name, url, latency, video_codec, ip_info_json = row
            ch = {
                "name": name,
                "url": url,
                "latency": latency,
                "video_codec": video_codec,
                "ip_info": json.loads(ip_info_json) if ip_info_json else None
            }
            channels.append(ch)
        print(f"📂 从数据库加载了 {len(channels)} 个频道源")
        return channels
    except Exception as e:
        print(f"⚠️ 从数据库加载失败: {e}")
        return []

async def save_to_cache(db, channels):
    """将频道源列表保存到数据库"""
    for ch in channels:
        key = channel_key(ch["name"], ch["url"])
        await db.set_speed_result(key, ch)
    print(f"💾 已保存 {len(channels)} 个频道源到数据库缓存")

async def main():
    print("🚀 IPTV智能整理平台启动")
    print(f"📡 配置：超时={os.getenv('TIMEOUT','10')}s, 并发={os.getenv('MAX_WORKERS','10')}, ffmpeg={os.getenv('FFMPEG_ENABLE','true')}")
    print(f"📋 增强过滤: demo={ENABLE_DEMO_FILTER}, alias={ENABLE_ALIAS}, blacklist={ENABLE_BLACKLIST}")

    await init_ip_resolver()
    if os.getenv("FFMPEG_ENABLE", "true").lower() == "true":
        from src.ffmpeg_validator import check_ffprobe
        await check_ffprobe()

    db = await get_db_cache()

    # 先检测源是否有变化
    print("\n🔍 检测源更新状态...")
    changed_urls, unchanged_urls, _ = await check_sources_changed(IPTV_SOURCES)
    
    use_cache = False
    if not changed_urls and DATABASE_ENABLE:
        # 所有源都无变化，使用缓存
        last_update = await db.get_last_update_time()
        if last_update is not None:
            age = int(time.time()) - last_update
            if age < CACHE_EXPIRY_SECONDS:
                use_cache = True
                print(f"✅ 所有源无变化，且数据库缓存有效（剩余 {CACHE_EXPIRY_SECONDS - age} 秒），将使用缓存数据")
            else:
                print(f"⏰ 数据库缓存已过期，需要重新采集")
        else:
            print("📦 数据库为空，将执行完整采集")
    else:
        print(f"🔄 检测到 {len(changed_urls)} 个源有变化，需要更新")
        if unchanged_urls:
            print(f"   {len(unchanged_urls)} 个源无变化，将使用缓存")

    if use_cache:
        cached_sources = await load_from_cache(db)
        if not cached_sources:
            print("⚠️ 缓存无数据，回退到完整采集")
            use_cache = False
        else:
            # 只对有变化的源进行重新拉取和测速
            if changed_urls:
                print(f"📥 仅更新 {len(changed_urls)} 个变化的源...")
                raw_contents = await fetch_all_sources(IPTV_SOURCES, force_refresh=True)
                new_channels_dict = parse_and_dedupe({url: raw_contents[url] for url in changed_urls if raw_contents.get(url)})
                if new_channels_dict:
                    new_valid = await test_channels_concurrent(new_channels_dict)
                    new_valid = await validate_batch(new_valid)
                    # 合并新旧数据
                    all_valid = cached_sources + new_valid
                    await save_to_cache(db, all_valid)
                    await db.set_last_update_time()
                    cached_sources = all_valid
            merged_channels = merge_channels_by_name(cached_sources)
            print(f"📊 从缓存合并后得到 {len(merged_channels)} 个频道")
    else:
        print("\n📥 执行完整采集流程...")
        raw_contents = await fetch_all_sources(IPTV_SOURCES, force_refresh=True)
        channels_dict = parse_and_dedupe(raw_contents)
        if not channels_dict:
            print("❌ 未获取到任何频道，请检查网络或源地址")
            return 1

        print(f"📊 原始频道数（去重后）: {len(channels_dict)}")

        valid_channels = await test_channels_concurrent(channels_dict)
        print(f"📊 通过HTTP测速的频道数: {len(valid_channels)}")

        valid_channels = await validate_batch(valid_channels)
        print(f"📊 通过ffmpeg深度验证的频道数: {len(valid_channels)}")

        if DATABASE_ENABLE:
            await save_to_cache(db, valid_channels)
            await db.set_last_update_time()

        merged_channels = merge_channels_by_name(valid_channels)
        print(f"📊 合并后的频道数: {len(merged_channels)}")

    # 后续统一过滤
    if ENABLE_BLACKLIST:
        blacklist_filter = get_blacklist_filter()
        before = len(merged_channels)
        merged_channels = blacklist_filter.filter_channels(merged_channels)
        print(f"📊 黑名单过滤后: {len(merged_channels)} (减少 {before - len(merged_channels)})")

    if ENABLE_DEMO_FILTER:
        before = len(merged_channels)
        ordered_channels, category_map = filter_and_order_by_demo(merged_channels)
        print(f"📊 Demo筛选后: {len(ordered_channels)} (减少 {before - len(ordered_channels)})")
        if not ordered_channels:
            print("❌ Demo 筛选后无频道，尝试不筛选")
            ordered_channels = merged_channels
    else:
        ordered_channels = merged_channels
        category_map = {}

    ordered_channels = filter_by_region(ordered_channels)
    if not ordered_channels:
        print("❌ 过滤后无有效频道")
        return 1

    generate_outputs_from_demo(ordered_channels, category_map)

    total = len(ordered_channels)
    print(f"🎉 完成！有效频道总数: {total}")
    ffmpeg_cleanup()
    await db.close()
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
