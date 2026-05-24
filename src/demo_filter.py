# src/demo_filter.py
# Demo 频道筛选与排序模块，返回带分类标签的频道列表

from pathlib import Path
from typing import List, Tuple, Dict
from src.config import DEMO_FILE
from src.alias_matcher import get_alias_matcher

try:
    from src.config import DEMO_MATCH_MODE
except ImportError:
    DEMO_MATCH_MODE = "contains"

def parse_demo_order_with_categories(demo_file: Path = DEMO_FILE) -> List[Tuple[str, str]]:
    """解析 demo.txt，返回 [(分类, 标准化频道名), ...]，按出现顺序"""
    if not demo_file.exists():
        print(f"⚠️ Demo 文件不存在: {demo_file}")
        return []
    matcher = get_alias_matcher()
    order = []
    current_category = None
    with open(demo_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.endswith(",#genre#"):
                current_category = line[:-7]
                continue
            if line.startswith('#'):
                continue
            if current_category is not None:
                demo_name = line
                if matcher:
                    demo_name = matcher.normalize(demo_name)
                order.append((current_category, demo_name))
            else:
                order.append(("其他", line))
    print(f"📋 从 demo.txt 解析到 {len(order)} 个有序频道，共 {len(set(c for c,_ in order))} 个分类")
    return order

def match_channel_name(channel_name: str, demo_name: str) -> bool:
    if DEMO_MATCH_MODE == "exact":
        return channel_name == demo_name
    else:
        return demo_name in channel_name or channel_name in demo_name

def filter_and_order_by_demo(channels: list, alias_matcher=None) -> Tuple[List[dict], Dict[str, list]]:
    """
    根据 demo.txt 筛选并排序频道。
    返回 (ordered_channels, category_map)
    ordered_channels: 按 demo 顺序排列的频道字典列表（每个字典增加 'demo_category' 字段）
    category_map: 分类名 -> 该分类下的频道列表（用于输出统计）
    """
    demo_order = parse_demo_order_with_categories()
    if not demo_order:
        print("⚠️ demo.txt 为空，跳过筛选")
        return channels, {}

    # 建立频道名到频道的映射（标准化后的名称）
    name_to_channel = {ch["name"]: ch for ch in channels}
    matched = []
    category_map = {}
    matched_names = set()

    for category, demo_name in demo_order:
        # 精确匹配优先
        if demo_name in name_to_channel:
            ch = name_to_channel[demo_name].copy()
            ch["demo_category"] = category
            if ch["name"] not in matched_names:
                matched.append(ch)
                matched_names.add(ch["name"])
                category_map.setdefault(category, []).append(ch)
                continue
        # 模糊匹配
        for ch in channels:
            if ch["name"] in matched_names:
                continue
            if match_channel_name(ch["name"], demo_name):
                ch_copy = ch.copy()
                ch_copy["demo_category"] = category
                matched.append(ch_copy)
                matched_names.add(ch["name"])
                category_map.setdefault(category, []).append(ch_copy)
                break

    print(f"🎯 Demo 筛选：原始 {len(channels)} 个频道 -> 匹配 {len(matched)} 个频道（按 demo 顺序，匹配模式: {DEMO_MATCH_MODE}）")
    return matched, category_map
