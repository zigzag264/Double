# -*- coding: utf-8 -*-
"""
双色球本地服务器 — 静态文件 + 数据更新 API

功能:
1. 提供静态文件服务（替代 python -m http.server）
2. POST /api/update — 一键更新开奖数据 + AI 预测，并返回最新数据

启动: python server.py
访问: http://localhost:8000
"""

import json
import os
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta

# ==================== 配置区 ====================
PORT = 8080
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")


def load_env():
    """读取 .env 文件中的环境变量"""
    env = os.environ.copy()
    env_file = os.path.join(SCRIPT_DIR, ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def _read_json(rel_path):
    """读取 data/ 目录下的 JSON 数据文件"""
    path = os.path.join(DATA_DIR, rel_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"_error": str(e)}


def run_update():
    """执行数据更新流程：爬虫 → AI 预测。

    返回 (success, message, data)
    - data 包含更新后的 lottery_history / ai_predictions / predictions_history / token_usage
    """
    results = []
    env = load_env()

    # 1. 运行爬虫更新开奖数据
    print("\n" + "=" * 50)
    print("📡 [1/2] 更新开奖数据...")
    print("=" * 50)

    crawler_path = os.path.join(SCRIPT_DIR, "fetch_history", "fetch_lottery_history.py")
    try:
        proc = subprocess.run(
            [sys.executable, crawler_path],
            cwd=os.path.join(SCRIPT_DIR, "fetch_history"),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            results.append("✅ 开奖数据更新成功")
            print(proc.stdout[-2000:])
        else:
            results.append("❌ 开奖数据更新失败")
            print(proc.stdout[-2000:])
            print(proc.stderr[-2000:])
    except subprocess.TimeoutExpired:
        results.append("❌ 开奖数据更新超时")
    except Exception as e:
        results.append(f"❌ 开奖数据更新异常: {e}")

    # 2. 运行 AI 预测生成下期预测
    print("\n" + "=" * 50)
    print("🤖 [2/2] 生成 AI 预测...")
    print("=" * 50)

    ai_script = os.path.join(SCRIPT_DIR, "generate_ai_prediction.py")
    try:
        proc = subprocess.run(
            [sys.executable, ai_script],
            cwd=SCRIPT_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if proc.returncode == 0:
            results.append("✅ AI 预测生成成功")
            print(proc.stdout[-2000:])
        else:
            results.append("❌ AI 预测生成失败")
            print(proc.stdout[-2000:])
            print(proc.stderr[-2000:])
    except subprocess.TimeoutExpired:
        results.append("❌ AI 预测生成超时")
    except Exception as e:
        results.append(f"❌ AI 预测生成异常: {e}")

    # 3. 读取最新数据
    data = {
        "lottery_history": _read_json("lottery_history.json"),
        "ai_predictions": _read_json("ai_predictions.json"),
        "predictions_history": _read_json("predictions_history.json"),
        "token_usage": _read_json("token_usage.json"),
    }

    success = all("✅" in r for r in results)
    return success, "\n".join(results), data


class Handler(SimpleHTTPRequestHandler):
    """静态文件 + API 处理器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SCRIPT_DIR, **kwargs)

    # 禁用默认日志（避免刷屏）
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/update":
            self._handle_update()
        else:
            self.send_error(404, "Not Found")

    def _handle_update(self):
        """处理更新请求，返回 JSON"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        try:
            success, message, data = run_update()
            resp = {
                "success": success,
                "message": message,
                "data": data,
                "timestamp": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M"),
            }
        except Exception as e:
            resp = {
                "success": False,
                "message": f"更新异常: {e}",
                "data": None,
                "timestamp": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M"),
            }

        self.wfile.write(json.dumps(resp, ensure_ascii=False, indent=2).encode("utf-8"))


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("=" * 50)
    print("双色球开奖与 AI 预测数据展示系统")
    print("=" * 50)
    print(f"📡 服务器地址: http://localhost:{PORT}")
    print(f"🌐 请在浏览器中打开上述地址")
    print(f"🔄 POST /api/update — 一键更新数据")
    print(f"💡 提示: 按 Ctrl+C 停止服务器")
    print("=" * 50)
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.shutdown()


if __name__ == "__main__":
    main()