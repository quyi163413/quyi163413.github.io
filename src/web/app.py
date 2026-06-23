# src/web/app.py
"""Flask 应用工厂"""

import os
from pathlib import Path
from flask import Flask, send_from_directory
from flask_cors import CORS
from src.web.api import api_bp
from src.config import WEB_SERVER_HOST, WEB_SERVER_PORT, OUTPUT_DIR

def create_app():
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    app.config['SECRET_KEY'] = os.urandom(24)
    CORS(app)
    
    # 注册 API 蓝图
    app.register_blueprint(api_bp)
    
    # 静态文件服务（输出目录）
    @app.route('/files/<path:filename>')
    def serve_output(filename):
        return send_from_directory(OUTPUT_DIR, filename)
    
    # 主页
    @app.route('/')
    def index():
        return send_from_directory(app.template_folder, 'index.html')
    
    return app

def run_server():
    app = create_app()
    print(f"🌐 Web 管理界面启动: http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}")
    app.run(host=WEB_SERVER_HOST, port=WEB_SERVER_PORT, debug=False, threaded=True)
