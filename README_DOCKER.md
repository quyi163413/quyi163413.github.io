# IPTV 智能整理平台 Docker 部署指南

本指南帮助你快速在任意支持 Docker 的 Linux 设备（x86_64 / ARM64）上部署 IPTV 采集服务。  
容器内置 HTTP 文件服务器，采集完成后可直接通过 `http://设备IP:端口/tv.m3u` 或 `/tv.txt` 获取播放列表，无需额外配置 Nginx。

---

## 一、前提条件

- 已安装 **Docker** 和 **Docker Compose**（或 Docker Engine 24+ 内置 Compose v2）
- 开放目标端口（如 `8080`）用于访问播放列表
- 确保设备有稳定的网络连接（用于拉取 IPTV 源）

---

## 二、部署步骤

### 1. 下载项目文件

将以下完整项目结构打包或直接克隆到设备上：
iptv-collector/
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── .env.example
├── requirements.txt
├── alias.txt
├── blacklist.txt
├── demo.txt
├── src/
│ ├── init.py
│ ├── alias_matcher.py
│ ├── blacklist_filter.py
│ ├── classifier.py
│ ├── config.py
│ ├── database.py
│ ├── demo_filter.py
│ ├── fetcher.py
│ ├── ffmpeg_validator.py
│ ├── generator.py
│ ├── ip_resolver.py
│ ├── logger.py
│ ├── merger.py
│ ├── parser.py
│ ├── run.py
│ ├── server.py
│ ├── speed_tester.py
│ └── update_ipdb.py
├── data/ # 自动生成（缓存数据库）
└── output/ # 自动生成（播放列表）

使用 Docker Compose 一键构建并启动：
docker-compose up -d --build
