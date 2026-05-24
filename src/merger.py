# src/merger.py
# 频道合并模块：按标准化名称合并，增加 CCTV 错位修复

import re
from collections import defaultdict
from src.config import MAX_SOURCES_PER_CHANNEL

def normalize_channel_name(name: str) -> str:
    """标准化频道名，保留数字差异"""
    name = re.sub(r'\s*(?:1080[pi]|720[pi]|4K|8K|HD|高清|超清|标清|流畅|付费|备\d*)\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[（(][^）)]*[）)]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'(?i)^CCTV\s*(\d+)$', r'CCTV-\1', name)
    name = re.sub(r'(?i)^CCTV\s*(\d+)\+$', r'CCTV-\1+', name)
    return name

def merge_channels_by_name(valid_channels: list) -> list:
    """按标准化名称合并，每个频道保留最多 MAX_SOURCES_PER_CHANNEL 个源"""
    groups = defaultdict(list)
    for ch in valid_channels:
        norm_name = normalize_channel_name(ch["name"])
        groups[norm_name].append(ch)

    merged = []
    for norm_name, ch_list in groups.items():
        def sort_key(ch):
            codec = ch.get("video_codec", "")
            codec_priority = 0 if codec == "h264" else 1 if codec == "hevc" else 2
            latency = ch.get("latency", 9999)
            return (codec_priority, latency)
        ch_list.sort(key=sort_key)
        top = ch_list[:MAX_SOURCES_PER_CHANNEL]
        primary = top[0]
        merged_ch = {
            "name": primary["name"],
            "urls": [c["url"] for c in top],
            "url": primary["url"],
            "latency": primary["latency"],
            "video_codec": primary["video_codec"],
            "group_title": primary.get("group_title", ""),
            "id": primary.get("tvg_id", ""),
            "logo": primary.get("tvg_logo", ""),
            "ip_info": primary.get("ip_info")
        }
        merged.append(merged_ch)
    print(f"🔄 频道合并完成：{len(valid_channels)} 个源 -> {len(merged)} 个频道")
    return merged

def fix_cctv_mismatch(channels: list) -> list:
    """
    修复央视频道错位问题：如果频道名是 CCTV-1 但 URL 明显指向 CCTV-17，则移除该 URL。
    同时检查其他数字不匹配的情况。
    """
    fixed = []
    for ch in channels:
        name = ch.get("name", "")
        # 检查是否为央视数字频道
        match = re.search(r'(?i)(?:CCTV[- ]?)(\d+)(?:\+?)', name)
        if match:
            expected_num = match.group(1)
            urls = ch.get("urls", [ch.get("url")])
            good_urls = []
            for url in urls:
                # 检查 URL 中是否包含其他明显的央视数字
                # 例如 "cctv17" 或 "cctv-17" 出现在 URL 中
                if re.search(r'cctv[-\s]*17', url, re.IGNORECASE):
                    if expected_num == "17":
                        good_urls.append(url)
                    else:
                        print(f"⚠️ 修复错位: {name} 的 URL 包含 cctv17，已丢弃: {url[:80]}...")
                elif re.search(r'cctv[-\s]*1[^0-9]', url, re.IGNORECASE):
                    if expected_num == "1":
                        good_urls.append(url)
                    else:
                        print(f"⚠️ 修复错位: {name} 的 URL 包含 cctv1，已丢弃: {url[:80]}...")
                elif re.search(r'cctv[-\s]*农业农村', url, re.IGNORECASE):
                    if expected_num == "17":
                        good_urls.append(url)
                    else:
                        print(f"⚠️ 修复错位: {name} 的 URL 包含 '农业农村' (CCTV-17)，已丢弃: {url[:80]}...")
                else:
                    good_urls.append(url)
            if good_urls:
                ch["urls"] = good_urls
                ch["url"] = good_urls[0]
                fixed.append(ch)
            else:
                print(f"⚠️ 频道 {name} 所有 URL 均被判定为错位，已丢弃整个频道")
        else:
            fixed.append(ch)
    print(f"🔧 央视错位修复完成，保留 {len(fixed)} 个频道")
    return fixed
