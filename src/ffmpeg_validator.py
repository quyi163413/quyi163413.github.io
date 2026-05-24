# src/ffmpeg_validator.py
# ffmpeg/ffprobe 深度验证模块（使用线程池避免阻塞）

import asyncio
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor
from src.config import FFMPEG_ENABLE, TIMEOUT, MAX_WORKERS, FFMPEG_STRICT

_thread_pool = None

def get_thread_pool():
    global _thread_pool
    if _thread_pool is None:
        _thread_pool = ThreadPoolExecutor(max_workers=min(MAX_WORKERS, 3))
    return _thread_pool

def check_ffprobe_sync():
    try:
        result = subprocess.run(["ffprobe", "-version"], capture_output=True, timeout=5, text=True)
        return result.returncode == 0
    except Exception:
        return False

async def check_ffprobe():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(get_thread_pool(), check_ffprobe_sync)

def validate_with_ffprobe_sync(url: str, timeout: int) -> dict:
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams",
        "-analyzeduration", "5000000", "-probesize", "5000000", url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout, text=True)
        if result.returncode != 0:
            return {"valid": not FFMPEG_STRICT, "has_video": False, "video_codec": "", "has_audio": False}
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        has_video = False
        video_codec = ""
        for s in streams:
            if s.get("codec_type") == "video":
                has_video = True
                video_codec = s.get("codec_name", "").lower()
                break
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        valid = has_video or has_audio
        if not valid and not FFMPEG_STRICT:
            valid = True
        return {"valid": valid, "has_video": has_video, "video_codec": video_codec, "has_audio": has_audio}
    except Exception:
        return {"valid": not FFMPEG_STRICT, "has_video": False, "video_codec": "", "has_audio": False}

async def validate_with_ffprobe(channel: dict) -> dict:
    if not FFMPEG_ENABLE:
        return {"valid": True, "video_codec": "unknown"}
    if not await check_ffprobe():
        return {"valid": True, "video_codec": "unknown"}
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(get_thread_pool(), validate_with_ffprobe_sync, channel["url"], TIMEOUT)
    return result

async def validate_batch(channels: list) -> list:
    if not FFMPEG_ENABLE:
        print("⚙️ ffmpeg 深度验证未启用，跳过")
        return channels
    if not await check_ffprobe():
        print("⚠️ ffprobe 不可用，跳过深度验证，全部频道视为有效")
        return channels
    semaphore = asyncio.Semaphore(3)
    async def validate_one(ch):
        async with semaphore:
            result = await validate_with_ffprobe(ch)
            if result.get("valid"):
                ch["video_codec"] = result.get("video_codec", "")
                return ch
            return None
    tasks = [validate_one(ch) for ch in channels]
    results = await asyncio.gather(*tasks)
    valid = [r for r in results if r is not None]
    print(f"🔍 ffmpeg 深度验证完成，通过 {len(valid)}/{len(channels)} 个频道")
    return valid

def cleanup():
    global _thread_pool
    if _thread_pool:
        _thread_pool.shutdown(wait=False)
        _thread_pool = None
