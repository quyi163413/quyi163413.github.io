# src/demo_filter.py
# Demo 频道筛选与排序模块，支持包含匹配，输出未匹配频道

from pathlib import Path
from typing import List, Tuple
from src.config import DEMO_FILE, OUTPUT_DIR
from src.alias_matcher import get_alias_matcher

# 匹配模式：'exact' 或 'contains'（推荐 contains）
DEMO_MATCH_MODE = "contains"

def parse_demo_order_with_categories(demo_file: Path = DEMO_FILE) -> List[Tuple[str, str]]:
    """解析 demo.txt，返回 [(分类, 标准化频道名), ...]"""
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
    """包含匹配：只要 demo_name 是 channel_name 的子串或反之即可"""
    if DEMO_MATCH_MODE == "exact":
        return channel_name == demo_name
    else:
        # 忽略大小写进行包含匹配
        cn_lower = channel_name.lower()
        dn_lower = demo_name.lower()
        return dn_lower in cn_lower or cn_lower in dn_lower

def filter_and_order_by_demo(channels: list) -> tuple:
    """
    根据 demo.txt 筛选并排序频道。
    返回 (matched_channels, unmatched_channels)
    matched_channels: 按 demo 顺序排列，每个频道增加 'demo_category' 字段
    unmatched_channels: 未匹配的频道列表
    """
    demo_order = parse_demo_order_with_categories()
    if not demo_order:
        print("⚠️ demo.txt 为空，跳过筛选")
        return channels, []

    # 建立频道名到频道的映射
    name_to_channel = {ch["name"]: ch for ch in channels}
    matched = []
    unmatched = list(channels)  # 先复制全部，然后移除匹配的
    matched_names = set()
    matched_demo_items = set()

    for category, demo_name in demo_order:
        # 精确匹配优先
        if demo_name in name_to_channel:
            ch = name_to_channel[demo_name].copy()
            ch["demo_category"] = category
            if ch["name"] not in matched_names:
                matched.append(ch)
                matched_names.add(ch["name"])
                matched_demo_items.add(demo_name)
                continue
        # 包含匹配（遍历未匹配的频道）
        found = False
        for ch in unmatched[:]:  # 遍历副本
            if ch["name"] in matched_names:
                continue
            if match_channel_name(ch["name"], demo_name):
                ch_copy = ch.copy()
                ch_copy["demo_category"] = category
                matched.append(ch_copy)
                matched_names.add(ch["name"])
                matched_demo_items.add(demo_name)
                # 从未匹配列表中移除
                unmatched = [c for c in unmatched if c["name"] != ch["name"]]
                found = True
                break
        if not found:
            # 可记录未匹配的 demo 项
            pass

    print(f"🎯 Demo 筛选：原始 {len(channels)} 个频道 -> 匹配 {len(matched)} 个频道，未匹配 {len(unmatched)} 个（匹配模式: {DEMO_MATCH_MODE}）")
    
    # 输出未匹配的 demo 项（帮助调试）
    demo_names_set = set(demo_name for _, demo_name in demo_order)
    matched_demo_set = matched_demo_items
    unmatched_demo = demo_names_set - matched_demo_set
    if unmatched_demo:
        print(f"⚠️ 以下 demo 频道未匹配到任何采集频道（前20个）: {list(unmatched_demo)[:20]}")
    
    return matched, unmatched

def write_shai_file(unmatched_channels: list, matched_count: int, total_raw: int):
    """输出未匹配的频道到 output/shai.txt"""
    shai_path = OUTPUT_DIR / "shai.txt"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(shai_path, "w", encoding="utf-8") as f:
        f.write(f"# Demo筛选丢弃的频道\n")
        f.write(f"# 原始频道总数: {total_raw}\n")
        f.write(f"# Demo匹配成功: {matched_count}\n")
        f.write(f"# 丢弃数量: {len(unmatched_channels)}\n")
        f.write(f"# 格式: 频道名,URL\n\n")
        for ch in unmatched_channels:
            url = ch["urls"][0] if ch.get("urls") else ch["url"]
            f.write(f"{ch['name']},{url}\n")
    print(f"📄 未匹配频道列表已保存到: {shai_path}")
