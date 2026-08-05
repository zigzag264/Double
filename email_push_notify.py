# -*- coding: utf-8 -*-
"""
Push 触发邮件通知脚本
在 GitHub Actions 中由 push 事件触发，发送更新摘要到邮箱。
与 email_content_builder.py 共用相同的 HTML 格式。
"""

import os
import sys
import smtplib
import json
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

from email_content_builder import (
    _SECTION, _build_latest_draw_html, _build_predictions_html, _build_ranking_html
)

# ==================== 配置 ====================

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.qq.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASSWORD")
RECIPIENT = os.environ.get("EMAIL_RECIPIENT")
DRY_RUN = os.environ.get("EMAIL_DRY_RUN", "").lower() == "true"

REQUIRED = [SMTP_USER, SMTP_PASS, RECIPIENT]
if not all(REQUIRED):
    if DRY_RUN:
        print("ℹ️  Dry-run 模式：缺少邮件凭证，仅打印邮件内容\n")
    else:
        print("❌ 缺少邮件凭证，请设置 SMTP_USER / SMTP_PASSWORD / EMAIL_RECIPIENT")
        sys.exit(1)


def _data_path(name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", name)


# ==================== 数据获取 ====================

def get_git_info():
    author, msg, files, stat = "unknown", "no commit info", [], ""
    try:
        author = subprocess.run(["git", "log", "-1", "--format=%an"], capture_output=True, text=True, check=True).stdout.strip()
        msg = subprocess.run(["git", "log", "-1", "--format=%s"], capture_output=True, text=True, check=True).stdout.strip()
        files = subprocess.run(["git", "diff", "--name-only", "HEAD~1", "HEAD"], capture_output=True, text=True, check=True).stdout.strip().split("\n")
        stat = subprocess.run(["git", "diff", "--stat", "HEAD~1", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        pass
    return author, msg, [f for f in files if f], stat


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ==================== HTML 构建 ====================

def build_html():
    author, commit_msg, files, stat = get_git_info()
    latest = load_json(_data_path("lottery_history.json"))
    pred = load_json(_data_path("ai_predictions.json"))
    hist = load_json(_data_path("predictions_history.json"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lh = latest or {}
    draw_data = lh.get("data", [{}])[0] if lh.get("data") else {}
    nd = lh.get("next_draw", {})

    # 提交信息 HTML
    files_html = ""
    if files and files[0]:
        items = "".join(f'<li style="font-size:13px;color:#475569;padding:2px 0">{f}</li>' for f in files)
        files_html = f'<ul style="margin:8px 0 0;padding-left:20px">{items}</ul>'

    html = f'''
    <div style="max-width:600px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;background:#ffffff;padding:0;color:#1e293b">
      <div style="background:linear-gradient(135deg,#1e293b,#3b82f6);padding:28px 24px;text-align:center;border-radius:12px 12px 0 0">
        <div style="font-size:28px;margin-bottom:4px">🎯</div>
        <h1 style="color:#ffffff;font-size:20px;font-weight:800;margin:0;letter-spacing:-0.5px">双色球 AI 预测</h1>
        <p style="color:#93c5fd;font-size:13px;margin:4px 0 0">项目更新通知 · {now}</p>
      </div>
      <div style="padding:20px 24px">
        {_SECTION.format("📦 提交信息")}
        <table style="width:100%;border-collapse:collapse;background:#f8fafc;border-radius:8px;overflow:hidden">
          <tr><td style="padding:12px 16px">
            <div style="font-size:13px;color:#475569;margin-bottom:4px"><span style="color:#94a3b8">作者</span> {author}</div>
            <div style="font-size:14px;font-weight:600;color:#1e293b">{commit_msg}</div>
            {files_html}
          </td></tr>
        </table>
        {_SECTION.format("🏆 最新开奖")}
        {_build_latest_draw_html(draw_data, nd)}
        {_SECTION.format("📊 命中排行 Top 10")}
        {_build_ranking_html(hist)}
        {_SECTION.format("🔮 AI 全部预测")}
        {_build_predictions_html(pred)}
      </div>
      <div style="background:#f8fafc;padding:16px 24px;text-align:center;border-top:1px solid #e2e8f0;border-radius:0 0 12px 12px">
        <p style="font-size:12px;color:#94a3b8;margin:0">
          本邮件由 GitHub Actions 自动推送 ·
          <a href="https://github.com/zhens/double-color-ball" style="color:#3b82f6;text-decoration:none">double-color-ball</a>
        </p>
      </div>
    </div>'''
    return html


# ==================== 发送 ====================

def send():
    html = build_html()
    subject = f"[双色球] 项目更新 · {datetime.now().strftime('%m-%d %H:%M')}"

    if DRY_RUN:
        print("=" * 60)
        print(f"[DRY-RUN] 收件人: {RECIPIENT}")
        print(f"[DRY-RUN] 主题: {subject}")
        print("=" * 60)
        print(html)
        print("=" * 60)
        print("ℹ️  Dry-run 模式，邮件未实际发送")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = RECIPIENT
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [RECIPIENT], msg.as_string())
        print("✅ 推送通知邮件发送成功")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    send()