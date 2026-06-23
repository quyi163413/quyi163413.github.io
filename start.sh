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

# ========== 启动 Web 管理界面（Flask） ==========
echo "启动 Web 管理界面，端口 ${WEB_SERVER_PORT:-8080}"
python -m src.server &
WEB_PID=$!

# 等待 Web 服务启动
sleep 3

# 检查 Web 服务是否正常运行
if ! kill -0 $WEB_PID 2>/dev/null; then
    echo "❌ Web 服务启动失败"
    exit 1
fi
echo "✅ Web 管理界面已启动: http://localhost:${WEB_SERVER_PORT:-8080}"

# ========== 采集任务 ==========
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
    echo "✅ 一次性任务完成，Web 服务继续运行"
    echo "📺 访问地址: http://localhost:${WEB_SERVER_PORT:-8080}/"
    echo "📄 TV列表: http://localhost:${WEB_SERVER_PORT:-8080}/tv.m3u"
    echo "🔄 多源切换: http://localhost:${WEB_SERVER_PORT:-8080}/tv_multi.m3u"
    wait $WEB_PID
fi
