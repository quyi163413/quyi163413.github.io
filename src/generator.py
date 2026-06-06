# src/generator.py
# 输出 M3U 和 TXT 文件模块

from pathlib import Path
from typing import List, Dict
from src.config import OUTPUT_DIR, M3U_FILE, TXT_FILE, OUTPUT_CATEGORY_ORDER
from src.logger import logger

def generate_m3u(channels_by_category: Dict[str, List[dict]], output_path: Path) -> None:
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for cat in OUTPUT_CATEGORY_ORDER:
            if cat not in channels_by_category:
                continue
            f.write(f'\n#EXTINF:-1 group-title="{cat}",{cat}\n')
            for ch in channels_by_category[cat]:
                url = ch.get("urls", [ch.get("url")])[0]
                tvg_id = ch.get("id", "")
                tvg_logo = ch.get("logo", "")
                group = ch.get("group_title", cat)
                name = ch["name"]
                extinf = f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{tvg_logo}" group-title="{group}",{name}'
                f.write(f"{extinf}\n{url}\n")
    logger.info(f"✅ M3U 文件已生成: {output_path}")

def generate_txt(channels_by_category: Dict[str, List[dict]], output_path: Path) -> None:
    with open(output_path, 'w', encoding='utf-8') as f:
        for cat in OUTPUT_CATEGORY_ORDER:
            if cat not in channels_by_category:
                continue
            f.write(f"\n{cat}频道,#genre#\n")
            for ch in channels_by_category[cat]:
                f.write(f"{ch['name']}\n")
    logger.info(f"✅ TXT 文件已生成: {output_path}")

def generate_outputs_from_demo(ordered_channels: List[dict]) -> None:
    if not ordered_channels:
        logger.warning("无频道数据，跳过输出生成")
        return

    groups = {}
    for ch in ordered_channels:
        cat = ch.get("demo_category", "其他")
        groups.setdefault(cat, []).append(ch)

    def category_key(cat: str) -> int:
        for idx, base in enumerate(OUTPUT_CATEGORY_ORDER):
            if base in cat:
                return idx
        return len(OUTPUT_CATEGORY_ORDER)
    
    sorted_cats = sorted(groups.keys(), key=lambda x: (category_key(x), x))
    final_groups = {cat: groups[cat] for cat in sorted_cats}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_m3u(final_groups, OUTPUT_DIR / M3U_FILE)
    generate_txt(final_groups, OUTPUT_DIR / TXT_FILE)
