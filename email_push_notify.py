# -*- coding: utf-8 -*-
"""
Push 触发邮件通知脚本
在 GitHub Actions 中由 push 事件触发，发送更新摘要到邮箱。
"""

import os
import sys
import smtplib
import json
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

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


# ==================== 获取变更摘要 ====================

def get_git_info():
    """获取最近一次提交的信息"""
    try:
        # 提交者
        author = subprocess.run(
            ["git", "log", "-1", "--format=%an"],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        # 提交信息
        msg = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        # 变更文件列表
        files = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True, check=True
        ).stdout.strip().split("\n")

        # 变更统计
        stat = subprocess.run(
            ["git", "diff", "--stat", "HEAD~1", "HEAD"],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        return author, msg, [f for f in files if f], stat
    except Exception as e:
        return "unknown", "no commit info", [], str(e)


def get_lottery_summary():
    """读取最新开奖数据摘要"""
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "lottery_history.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        latest = data.get("data", [{}])[0]
        nd = data.get("next_draw", {})
        return (
            f"  最新期号: {latest.get('period', '—')} "
            f"({latest.get('date', '—')})\n"
            f"  开奖号码: {' '.join(latest.get('red_balls', []))} "
            f"+ {latest.get('blue_ball', '')}\n"
            f"  下期预告: {nd.get('next_period', '—')} "
            f"{nd.get('next_date_display', '')} {nd.get('weekday', '')}"
        )
    except Exception as e:
        return f"  (读取失败: {e})"


def get_prediction_summary():
    """读取 AI 预测摘要"""
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "ai_predictions.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        models = data.get("models", [])
        lines = [
            f"  目标期号: {data.get('target_period', '—')}  "
            f"预测日期: {data.get('prediction_date', '—')}",
            f"  模型数: {len(models)}"
        ]
        for m in models:
            lines.append(f"    - {m['model_name']}")
        return "\n".join(lines)
    except Exception as e:
        return f"  (读取失败: {e})"


# ==================== 邮件构建 ====================

def build_body():
    author, commit_msg, files, stat = get_git_info()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = []
    sep = "━" * 34

    lines.append(sep)
    lines.append("  双色球 AI 预测 · 项目更新通知")
    lines.append(f"  推送时间: {now}")
    lines.append(sep)
    lines.append("")

    # 提交信息
    lines.append("【提交信息】")
    lines.append(f"  作者: {author}")
    lines.append(f"  提交: {commit_msg}")
    lines.append("")

    # 变更文件
    lines.append("【变更文件】")
    if files and files[0]:
        for f in files:
            lines.append(f"  - {f}")
    else:
        lines.append("  (首次提交或无法获取变更列表)")
    lines.append("")
    lines.append(f"  统计: {stat}")
    lines.append("")

    # 最新开奖
    lines.append("【最新开奖】")
    lines.append(get_lottery_summary())
    lines.append("")

    # AI 预测
    lines.append("【AI 预测】")
    lines.append(get_prediction_summary())
    lines.append("")

    # 尾部
    lines.append(sep)
    lines.append("  本邮件由 GitHub Actions 自动推送")
    lines.append("  https://github.com/zhens/double-color-ball")
    lines.append(sep)

    return "\n".join(lines)


# ==================== 发送 ====================

def send():
    body = build_body()
    subject = f"[双色球] 项目更新推送 — {datetime.now().strftime('%m-%d %H:%M')}"

    if DRY_RUN:
        print("=" * 60)
        print(f"[DRY-RUN] 收件人: {RECIPIENT}")
        print(f"[DRY-RUN] 主题: {subject}")
        print("=" * 60)
        print(body)
        print("=" * 60)
        print("ℹ️  Dry-run 模式，邮件未实际发送")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = RECIPIENT
    msg.attach(MIMEText(body, "plain", "utf-8"))

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