#!/bin/bash
set -e

echo "=========================================="
echo "IPTV 智能整理平台 Docker 容器启动"
echo "架构: $(uname -m)"
echo "=========================================="

mkdir -p /app/data /app/output
cd /app

RUN_MODE=${RUN_MODE:-once}
INTERVAL=${SCHEDULE_INTERVAL:-21600}

# 后台运行 HTTP 文件服务器
echo "启动 HTTP 文件服务器，端口 ${WEB_SERVER_PORT:-8080}"
cd /app/output
python -m http.server ${WEB_SERVER_PORT:-8080} --bind 0.0.0.0 &
HTTP_PID=$!

# 等待 HTTP 服务启动
sleep 2

run_collector() {
    while true; do
        echo "$(date): 开始采集任务..."
        cd /app
        python -m src.run
        echo "$(date): 任务完成"
        
        if [ "$RUN_MODE" = "once" ]; then
            break
        fi
        
        echo "等待 ${INTERVAL} 秒后继续..."
        sleep $INTERVAL
    done
}

# 执行采集
run_collector

if [ "$RUN_MODE" = "once" ]; then
    echo "✅ 一次性任务完成，HTTP 服务器继续运行"
    echo "📺 访问地址: http://localhost:${WEB_SERVER_PORT:-8080}/tv.m3u"
    echo "📄 TXT 地址: http://localhost:${WEB_SERVER_PORT:-8080}/tv.txt"
    echo "🔄 多源切换地址: http://localhost:${WEB_SERVER_PORT:-8080}/tv_multi.m3u"
    wait $HTTP_PID
fi
