# src/special_categories.py
"""智能分类模块 - 将 abc123 源的频道融入 demo 分类体系"""

import re
from typing import List, Dict, Tuple
from pathlib import Path
from collections import defaultdict

from src.logger import logger
from src.classifier import PROVINCES


# ========== 新分类关键词（用于创建新分类） ==========
NEW_CATEGORY_KEYWORDS = {
    "🎬 电影频道": [
        "电影", "影院", "影片", "CHC", "动作电影", "家庭影院", "影迷电影",
        "经典电影", "华语影院", "峨眉电影", "新片放映厅", "抗战经典影片",
        "经典香港电影", "CHC影迷电影", "CHC动作电影", "CHC家庭影院"
    ],
    "📺 电视剧频道": [
        "电视剧", "剧场", "热播", "TVB", "港剧", "韩剧", "美剧", "日剧", "穿越剧"
    ],
    "🎤 韩国女团": [
        "韩国女团", "女团", "kpop", "K-pop", "KPOP", "BLACKPINK", "TWICE",
        "IVE", "NewJeans", "LESSERAFIM", "aespa", "Red Velvet", "ITZY",
        "女团社", "颜老师", "歌团", "歌团★"
    ],
    "🎭 戏曲频道": [
        "戏曲", "京剧", "越剧", "黄梅戏", "豫剧", "评剧", "秦腔", "昆曲",
        "粤剧", "河北梆子", "梨园", "梨园春", "移动戏曲", "岭南戏曲",
        "陕西戏曲", "河南戏曲", "安徽戏曲"
    ],
    "🎵 音乐频道": [
        "音乐", "歌曲", "老歌", "金曲", "流行", "经典老歌", "香香音乐",
        "DJ", "舞曲", "动感", "节奏", "音悦", "经典歌曲"
    ],
    "📻 网络电台": [
        "电台", "广播", "FM", "AM", "网络电台", "音频", "听书", "有声",
        "动听", "音乐广播", "交通广播", "新闻广播"
    ],
    "🏀 体育频道": [
        "体育", "NBA", "CBA", "世界杯", "英超", "西甲", "德甲", "意甲",
        "法甲", "中超", "欧冠", "亚冠", "斯诺克", "WTA", "WTT", "BWF",
        "UFC", "赛车", "F1", "电竞", "五星体育"
    ],
    "👶 少儿频道": [
        "少儿", "儿童", "卡通", "动画", "金鹰卡通", "嘉佳卡通", "卡酷",
        "炫动卡通", "优漫卡通"
    ],
    "💰 财经频道": [
        "财经", "经济", "财富", "金融", "股票", "投资"
    ],
    "🌍 国际频道": [
        "国际", "海外", "美洲", "欧洲", "亚洲", "环球", "CGTN"
    ],
    "🎬 综合频道": [
        "综合", "生活", "休闲", "旅游", "农业", "教育", "法治", "军事"
    ],
    "🎭 其他": []
}


# 需要排除的关键词
EXCLUDE_KEYWORDS = [
    "广场舞", "健身", "教学", "讲座", "访谈", "天气预报",
    "直播", "回放", "全场", "解说", "原声", "字幕"
]


def detect_category_for_demo(name: str, demo_order: List[Tuple[str, str]]) -> Tuple[str, bool]:
    """
    根据频道名判断应该归入哪个 demo 分类
    返回 (分类名, 是否匹配成功)
    """
    name_lower = name.lower()
    
    # 1. 检测央视
    if re.search(r'(cctv|央视|中央台)', name_lower):
        for cat, _ in demo_order:
            if '央视' in cat:
                return cat, True
        # 如果没有央视分类，创建新分类
        return "📡 央视", False
    
    # 2. 检测省份/城市（地方频道）
    for prov in PROVINCES:
        if prov in name:
            # 查找 demo 中是否有对应的省份分类
            for cat, _ in demo_order:
                if prov in cat and ('频道' in cat or '☘️' in cat):
                    return cat, True
            # 否则创建新分类
            return f"☘️{prov}频道", False
    
    # 3. 检测直辖市简称
    alias_map = {"京": "北京", "沪": "上海", "津": "天津", "渝": "重庆"}
    for short, full in alias_map.items():
        if short in name:
            for cat, _ in demo_order:
                if full in cat and ('频道' in cat or '☘️' in cat):
                    return cat, True
            return f"☘️{full}频道", False
    
    # 4. 检测卫视（没有省份关键词的卫视）
    if '卫视' in name:
        for cat, _ in demo_order:
            if '卫视' in cat:
                return cat, True
        # 如果没有，归入"卫视"分类（可能 demo 中有）
        # 但 demo 中通常有"📡卫视频道"，我们找一下
        for cat, _ in demo_order:
            if '卫视' in cat:
                return cat, True
        return "📡 卫视", False
    
    # 5. 检测港澳台
    hmtj_keywords = ["香港", "澳门", "台湾", "港", "澳", "台"]
    for kw in hmtj_keywords:
        if kw in name:
            for cat, _ in demo_order:
                if '港澳台' in cat or '港·澳·台' in cat:
                    return cat, True
            return "🌊港·澳·台", False
    
    # 6. 没有匹配到任何已有分类
    return None, False


def classify_new_category(name: str) -> str:
    """对未匹配 demo 的频道，根据关键词判断应创建的新分类"""
    name_lower = name.lower()
    
    # 排除项
    for exclude in EXCLUDE_KEYWORDS:
        if exclude.lower() in name_lower:
            return None  # 跳过
    
    # 按优先级匹配新分类
    for category, keywords in NEW_CATEGORY_KEYWORDS.items():
        if category == "🎭 其他":
            continue
        for kw in keywords:
            if kw.lower() in name_lower:
                return category
    
    # 如果包含"频道"但未匹配，归入"综合频道"
    if "频道" in name:
        return "🎬 综合频道"
    
    return "🎭 其他"


async def fetch_and_classify_special_sources(db=None, demo_order: List[Tuple[str, str]] = None) -> Dict[str, List[Tuple[str, str]]]:
    """
    从 abc123 源采集频道，并智能映射到 demo 分类或新分类
    返回: {分类名: [(频道名, URL), ...]}
    """
    source_url = "https://tv.19860519.xyz/abc123"
    from src.fetcher import fetch_url_with_metadata
    
    try:
        content = await fetch_url_with_metadata(source_url, db)
        if not content:
            logger.warning(f"⚠️ 无法获取源: {source_url}")
            return {}
    except Exception as e:
        logger.error(f"❌ 获取源失败: {e}")
        return {}
    
    # 解析所有频道
    all_channels = []
    lines = content.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or line.endswith(',#genre#'):
            continue
        if ',' in line:
            parts = line.split(',', 1)
            if len(parts) == 2:
                name = parts[0].strip()
                url = parts[1].strip()
                if url.startswith(('http://', 'https://')):
                    all_channels.append((name, url))
    
    # 分类结果
    result = defaultdict(list)
    demo_categories = {cat for cat, _ in demo_order} if demo_order else set()
    
    for name, url in all_channels:
        # 先尝试匹配 demo 分类
        if demo_order:
            matched_cat, is_demo = detect_category_for_demo(name, demo_order)
            if matched_cat and is_demo:
                result[matched_cat].append((name, url))
                continue
        
        # 未匹配 demo，创建新分类
        new_cat = classify_new_category(name)
        if new_cat is None:
            # 跳过
            continue
        result[new_cat].append((name, url))
    
    # 去重（基于 URL）
    for cat in result:
        seen = set()
        unique = []
        for name, url in result[cat]:
            if url not in seen:
                seen.add(url)
                unique.append((name, url))
        result[cat] = unique
    
    # 统计
    total = sum(len(v) for v in result.values())
    logger.info(f"📊 智能分类统计: 共 {total} 个频道")
    for cat, channels in result.items():
        if channels:
            logger.info(f"   {cat}: {len(channels)} 个频道")
    
    return dict(result)


def append_special_to_output(
    special_data: Dict[str, List[Tuple[str, str]]],
    output_dir: Path,
    demo_order: List[Tuple[str, str]]
) -> Dict[str, int]:
    """
    将分类好的频道追加到输出文件
    - 如果分类在 demo_order 中，则插入到该分类末尾（不破坏顺序）
    - 如果分类不在 demo_order 中，则追加到文件末尾的新分类区块
    但这里简化处理：直接追加到文件末尾，因为插入会破坏现有文件的顺序结构。
    我们按照现有方式追加到末尾，但分类名会与 demo 分类保持一致。
    """
    if not special_data:
        return {}
    
    # 追加到 M3U
    m3u_path = output_dir / "tv.m3u"
    txt_path = output_dir / "tv.txt"
    
    total_appended = 0
    
    # 写入 M3U
    with open(m3u_path, 'a', encoding='utf-8') as f:
        f.write(f"\n# ========== 智能补充内容 ==========\n")
        for cat, channels in special_data.items():
            if not channels:
                continue
            f.write(f"\n# ----- {cat} ({len(channels)}个频道) -----\n")
            for name, url in channels:
                f.write(f'#EXTINF:-1 group-title="{cat}",{name}\n{url}\n')
                total_appended += 1
    
    # 写入 TXT
    with open(txt_path, 'a', encoding='utf-8') as f:
        f.write(f"\n# ========== 智能补充内容 ==========\n")
        for cat, channels in special_data.items():
            if not channels:
                continue
            f.write(f"\n{cat},#genre#\n")
            for name, url in channels:
                f.write(f"{name},{url}\n")
    
    logger.info(f"✅ 已将 {total_appended} 个智能分类频道追加到输出文件")
    return {cat: len(ch) for cat, ch in special_data.items()}
