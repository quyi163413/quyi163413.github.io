# src/generator.py
# 输出 M3U 和 TXT 文件模块，按 demo.txt 顺序输出
# 如果 demo.txt 为空，则按分类顺序输出所有频道

from pathlib import Path
from typing import List, Tuple, Dict
from collections import defaultdict
from src.config import OUTPUT_DIR, M3U_FILE, TXT_FILE
from src.logger import logger


def get_default_category_order(channels: List[dict]) -> List[Tuple[str, str]]:
    """
    当 demo_order 为空时，生成默认的分类顺序
    按固定分类顺序：央视、卫视、地方、港澳台、其他
    在每个分类中，频道按名称排序
    """
    # 定义分类优先级
    category_priority = {
        "央视": 0,
        "卫视": 1,
        "地方": 2,
        "港澳台": 3,
        "其他": 4
    }
    # 按分类分组
    groups = defaultdict(list)
    for ch in channels:
        cat = ch.get("demo_category", "其他")
        groups[cat].append(ch["name"])
    # 排序：先按优先级，再按名称
    sorted_cats = sorted(groups.keys(), key=lambda x: category_priority.get(x, 5))
    order = []
    for cat in sorted_cats:
        for name in sorted(groups[cat]):
            order.append((cat, name))
    return order


def generate_m3u_by_demo_order(
    channels_by_name: Dict[str, dict],
    demo_order: List[Tuple[str, str]],
    output_path: Path
) -> None:
    """
    生成 M3U 文件
    如果 demo_order 为空，则使用所有频道，并按分类顺序
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        # 如果 demo_order 为空，使用所有频道构建默认顺序
        if not demo_order:
            # 收集所有频道并生成默认顺序
            all_channels = list(channels_by_name.values())
            # 为每个频道补充 demo_category（如果没有则使用 group_title 或 "其他"）
            for ch in all_channels:
                if "demo_category" not in ch:
                    # 根据 group_title 推断分类
                    group = ch.get("group_title", "")
                    if group in ["央视", "卫视", "地方", "港澳台"]:
                        ch["demo_category"] = group
                    else:
                        ch["demo_category"] = "其他"
            demo_order = get_default_category_order(all_channels)
            logger.info("📋 demo.txt 为空，使用默认分类顺序输出所有频道")
        
        for cat, demo_name in demo_order:
            channel = channels_by_name.get(demo_name)
            if channel:
                url = channel.get("urls", [channel.get("url")])[0]
                name = channel.get("name", demo_name)
                clean_cat = cat.replace(",#genre#", "").strip()
                f.write(f'#EXTINF:-1 group-title="{clean_cat}",{name}\n')
                f.write(f"{url}\n")


def generate_txt_by_demo_order(
    channels_by_name: Dict[str, dict],
    demo_order: List[Tuple[str, str]],
    output_path: Path
) -> None:
    """生成 TXT 文件，逻辑同 M3U"""
    with open(output_path, 'w', encoding='utf-8') as f:
        current_cat = None
        # 如果 demo_order 为空，同样使用默认顺序
        if not demo_order:
            all_channels = list(channels_by_name.values())
            for ch in all_channels:
                if "demo_category" not in ch:
                    group = ch.get("group_title", "")
                    if group in ["央视", "卫视", "地方", "港澳台"]:
                        ch["demo_category"] = group
                    else:
                        ch["demo_category"] = "其他"
            demo_order = get_default_category_order(all_channels)
            logger.info("📋 demo.txt 为空，使用默认分类顺序生成 TXT")

        for cat, demo_name in demo_order:
            clean_cat = cat.replace(",#genre#", "").strip()
            if clean_cat != current_cat:
                current_cat = clean_cat
                f.write(f"{current_cat},#genre#\n")
            channel = channels_by_name.get(demo_name)
            if channel:
                url = channel.get("urls", [channel.get("url")])[0]
                name = channel.get("name", demo_name)
                f.write(f"{name},{url}\n")


def generate_multi_m3u_by_demo_order(
    channels_by_name: Dict[str, dict],
    demo_order: List[Tuple[str, str]],
    output_path: Path
) -> None:
    """生成多源 M3U 文件，逻辑同 M3U"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        if not demo_order:
            all_channels = list(channels_by_name.values())
            for ch in all_channels:
                if "demo_category" not in ch:
                    group = ch.get("group_title", "")
                    if group in ["央视", "卫视", "地方", "港澳台"]:
                        ch["demo_category"] = group
                    else:
                        ch["demo_category"] = "其他"
            demo_order = get_default_category_order(all_channels)
            logger.info("📋 demo.txt 为空，使用默认分类顺序生成多源 M3U")

        for cat, demo_name in demo_order:
            channel = channels_by_name.get(demo_name)
            if channel:
                urls = channel.get("urls", [channel.get("url")])
                valid_urls = [u for u in urls if u and u.startswith(('http://', 'https://'))]
                if valid_urls:
                    multi_url = " # ".join(valid_urls)
                    name = channel.get("name", demo_name)
                    clean_cat = cat.replace(",#genre#", "").strip()
                    f.write(f'#EXTINF:-1 group-title="{clean_cat}",{name}\n')
                    f.write(f"{multi_url}\n")


def generate_outputs_from_demo(ordered_channels: List[dict], demo_order: List[Tuple[str, str]]) -> None:
    """
    按照 demo.txt 的顺序输出 M3U 和 TXT 文件
    如果 demo_order 为空，则按分类顺序输出所有频道
    """
    if not ordered_channels:
        logger.warning("无频道数据，跳过输出生成")
        return

    # 构建 {标准化名称: 频道数据} 的字典
    channels_by_name = {ch["name"]: ch for ch in ordered_channels}
    for ch in ordered_channels:
        if "demo_name" in ch:
            channels_by_name[ch["demo_name"]] = ch

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成标准 M3U 文件
    generate_m3u_by_demo_order(channels_by_name, demo_order, OUTPUT_DIR / M3U_FILE)
    
    # 生成 TXT 文件
    generate_txt_by_demo_order(channels_by_name, demo_order, OUTPUT_DIR / TXT_FILE)
    
    # 生成多源 M3U 文件
    generate_multi_m3u_by_demo_order(channels_by_name, demo_order, OUTPUT_DIR / "tv_multi.m3u") 
