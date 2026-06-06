# src/ffmpeg_validator.py
import asyncio
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor
from src.config import FFMPEG_ENABLE, TIMEOUT, MAX_WORKERS, FFMPEG_STRICT

_thread_pool = None
_ffprobe_available = None

def get_thread_pool():
    global _thread_pool
    if _thread_pool is None:
        _thread_pool = ThreadPoolExecutor(max_workers=min(MAX_WORKERS, 3))
    return _thread_pool

def check_ffprobe_sync():
    try:
        result = subprocess.run(["ffprobe", "-version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False

async def check_ffprobe():
    global _ffprobe_available
    if _ffprobe_available is not None:
        return _ffprobe_available
    loop = asyncio.get_event_loop()
    _ffprobe_available = await loop.run_in_executor(get_thread_pool(), check_ffprobe_sync)
    if _ffprobe_available:
        print("✅ ffprobe 可用（深度验证已启用）")
    else:
        print("⚠️ ffprobe 不可用，将跳过深度验证")
    return _ffprobe_available

def validate_sync(url: str, timeout: int) -> dict:
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams",
        "-analyzeduration", "5000000", "-probesize", "5000000",
        url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout, text=True)
        if result.returncode != 0:
            return {"valid": not FFMPEG_STRICT, "has_video": False, "video_codec": "", "has_audio": False}
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        has_video = any(s.get("codec_type") == "video" for s in streams)
        video_codec = next((s.get("codec_name", "").lower() for s in streams if s.get("codec_type") == "video"), "")
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        valid = has_video or has_audio
        if not valid and not FFMPEG_STRICT:
            valid = True
        return {"valid": valid, "has_video": has_video, "video_codec": video_codec, "has_audio": has_audio}
    except Exception:
        return {"valid": not FFMPEG_STRICT, "has_video": False, "video_codec": "", "has_audio": False}

async def validate_with_ffprobe(channel):
    if not FFMPEG_ENABLE:
        return {"valid": True, "has_video": True, "video_codec": "unknown", "has_audio": True}
    if not await check_ffprobe():
        return {"valid": True, "has_video": True, "video_codec": "unknown", "has_audio": True}
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(get_thread_pool(), validate_sync, channel.url, TIMEOUT)
        if hasattr(channel, 'video_codec'):
            channel.video_codec = result.get("video_codec", "")
        return result
    except Exception:
        return {"valid": not FFMPEG_STRICT, "has_video": False, "video_codec": "", "has_audio": False}

async def validate_batch(channels: list) -> list:
    if not FFMPEG_ENABLE:
        print("⚙️ ffmpeg 深度验证未启用，跳过")
        return channels
    if not await check_ffprobe():
        print("⚠️ ffprobe 不可用，跳过深度验证，全部频道视为有效")
        return channels
    semaphore = asyncio.Semaphore(min(MAX_WORKERS, 3))
    async def validate_one(ch):
        async with semaphore:
            result = await validate_with_ffprobe(ch)
            return ch, result.get("valid", True)
    tasks = [validate_one(ch) for ch in channels]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    valid = []
    for res in results:
        if isinstance(res, Exception):
            continue
        ch, ok = res
        if ok:
            valid.append(ch)
    print(f"🔍 ffmpeg 深度验证完成，通过 {len(valid)}/{len(channels)} 个频道")
    return valid

async def validate_with_ffmpeg_batch(channels: list) -> list:
    """对外统一入口"""
    return await validate_batch(channels)

def cleanup():
    global _thread_pool
    if _thread_pool:
        _thread_pool.shutdown(wait=False)
        _thread_pool = None
