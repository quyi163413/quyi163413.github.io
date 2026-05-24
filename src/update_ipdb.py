#!/usr/bin/env python3
# IP 数据库自动更新模块（使用稳定 CDN 源）

import requests
import time
from pathlib import Path
from src.config import IP_DATABASE_FILE

PRIMARY_URL = "https://cdn.1008.site/gh/nmgliangwei/qqwry@main/qqwry.dat"
BACKUP_URL = "https://raw.githubusercontent.com/FW27623/qqwry/main/qqwry.dat"
MAX_RETRIES = 3
RETRY_DELAY = 5

def download_file(url, filename):
    print(f"正在从 {url} 下载...")
    try:
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        content_type = response.headers.get('content-type', '')
        if 'text/html' in content_type and '404' in response.text[:100]:
            raise Exception("返回了404错误页面")
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        if Path(filename).stat().st_size < 1024 * 1024:
            raise Exception("下载的文件过小，可能无效")
        print(f"✅ 成功下载: {filename}")
        return True
    except Exception as e:
        print(f"⚠️ 下载失败: {e}")
        return False

def download_with_retry(url, filename, max_retries=MAX_RETRIES, delay=RETRY_DELAY):
    for attempt in range(max_retries):
        if download_file(url, filename):
            return True
        if attempt < max_retries - 1:
            print(f"等待 {delay} 秒后重试...")
            time.sleep(delay)
    return False

def update_ip_database():
    if download_with_retry(PRIMARY_URL, IP_DATABASE_FILE):
        return True, None
    print("主源失败，尝试备用源...")
    if download_with_retry(BACKUP_URL, IP_DATABASE_FILE):
        return True, None
    return False, "所有下载源均不可用"

if __name__ == "__main__":
    print("=" * 50)
    print("纯真 IP 数据库更新工具")
    print("=" * 50)
    success, err = update_ip_database()
    if not success:
        print(f"\n⚠️ IP 数据库更新失败: {err}")
        if IP_DATABASE_FILE.exists():
            print("  已有数据库文件可用，将继续使用旧版本。")
        else:
            print("  没有可用数据库文件，IP 归属地解析功能将不可用。")
    else:
        print("\n✅ 数据库已成功更新")
