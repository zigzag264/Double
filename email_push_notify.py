# -*- coding: utf-8 -*-
"""
Push 触发邮件通知脚本
在 GitHub Actions 中由 push 事件触发，发送更新摘要到邮箱。
与 email_content_builder.py 共用相同的 HTML 格式。
"""

import os
import sys
import smtplib
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

from email_content_builder import build_html_digest, load_data, validate_data

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


# ==================== HTML 构建 ====================

def build_html():
    author, commit_msg, files, stat = get_git_info()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # 使用统一的数据加载（与每日定时推送一致）
    data = load_data()
    errors, warnings = validate_data(data)

    commit_info = {
        "author": author,
        "message": commit_msg,
        "files": [f for f in files if f],
    }

    return build_html_digest(data, warnings, generated_at=now, commit_info=commit_info)


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