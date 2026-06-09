# src/generator.py
# 输出 M3U 和 TXT 文件模块
# - 央视频道按 CCTV_ORDER 顺序排列
# - 多源输出：同一频道名重复多条，播放器自动 fallback（无额外后缀）

from pathlib import Path
from typing import List, Dict
from src.config import OUTPUT_DIR, M3U_FILE, TXT_FILE, CCTV_ORDER
from src.logger import logger

def is_cctv_category(cat: str) -> bool:
    """判断是否为央视频道分类"""
    return "央视" in cat or "CCTV" in cat or "📺央视频道" in cat

def sort_channels_by_cctv_order(channels: List[dict]) -> List[dict]:
    """按照 CCTV_ORDER 顺序排序央视频道，未匹配的放最后"""
    def cctv_key(ch):
        name = ch["name"]
        for idx, std in enumerate(CCTV_ORDER):
            if std.lower() == name.lower() or name.lower().startswith(std.lower()):
                return idx
        return len(CCTV_ORDER)
    return sorted(channels, key=cctv_key)

def generate_m3u(channels_by_category: Dict[str, List[dict]], output_path: Path) -> None:
    """
    生成标准 M3U8 格式文件
    - 央视频道按 CCTV_ORDER 排序
    - 多源输出：相同频道名重复多条，播放器自动 fallback
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        f.write("# 提示：每个频道包含多个备用源，播放器会自动切换\n\n")

        for cat, channels in channels_by_category.items():
            if not channels:
                continue

            # 央视频道强制排序
            if is_cctv_category(cat):
                channels = sort_channels_by_cctv_order(channels)
            # 其他分类保持原有顺序（由 demo_filter 保证）

            f.write(f"# 分类: {cat}\n")

            for ch in channels:
                name = ch["name"]
                urls = ch.get("urls", [ch.get("url")])

                # 输出所有备用源，不添加任何后缀
                for url in urls:
                    extinf = f'#EXTINF:-1 tvg-id="{ch.get("id", "")}" tvg-logo="{ch.get("logo", "")}" group-title="{cat}",{name}'
                    f.write(f"{extinf}\n{url}\n")

    total_sources = sum(len(ch.get("urls", [ch.get("url")])) for chs in channels_by_category.values() for ch in chs)
    logger.info(f"✅ M3U 文件已生成: {output_path} (共 {total_sources} 个源)")

def generate_txt(channels_by_category: Dict[str, List[dict]], output_path: Path) -> None:
    """生成 TXT 文件，每个频道只取第一个最佳源（TXT 格式不支持多源）"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# IPTV 播放列表\n")
        f.write("# 格式: 频道名,URL\n")
        f.write("# 注：如需多源自动切换，请使用 M3U 文件\n\n")

        for cat, channels in channels_by_category.items():
            if not channels:
                continue

            if is_cctv_category(cat):
                channels = sort_channels_by_cctv_order(channels)

            f.write(f"\n{cat},#genre#\n")
            for ch in channels:
                url = ch.get("urls", [ch.get("url")])[0]   # 只输出最佳源
                f.write(f"{ch['name']},{url}\n")

    total_channels = sum(len(ch) for chs in channels_by_category.values() for ch in chs)
    logger.info(f"✅ TXT 文件已生成: {output_path} (共 {total_channels} 个频道)")

def generate_outputs_from_demo(ordered_channels: List[dict]) -> None:
    """
    ordered_channels 已按照 demo.txt 的顺序排列（包含 demo_category 字段）
    按 demo_category 分组后输出 M3U 和 TXT
    """
    if not ordered_channels:
        logger.warning("无频道数据，跳过输出生成")
        return

    groups = {}
    for ch in ordered_channels:
        cat = ch.get("demo_category", "其他")
        groups.setdefault(cat, []).append(ch)

    # 统计信息
    for cat, chs in groups.items():
        logger.info(f"📂 分类 '{cat}': {len(chs)} 个频道")
        if chs:
            avg_lat = sum(c.get("latency", 0) for c in chs) / len(chs)
            logger.info(f"   平均延迟: {avg_lat:.0f}ms")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_m3u(groups, OUTPUT_DIR / M3U_FILE)
    generate_txt(groups, OUTPUT_DIR / TXT_FILE)
