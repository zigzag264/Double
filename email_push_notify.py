# -*- coding: utf-8 -*-
"""
Push 触发邮件通知脚本
在 GitHub Actions 中由 push 事件触发，发送更新摘要到邮箱。
与 email_content_builder.py 共用相同的 HTML 格式。
"""

import subprocess

from email_content_builder import build_html_digest, load_data, validate_data
from email_smtp_utils import beijing_time, send_digest


# ==================== 数据获取 ====================

def get_git_info():
    """获取最近一次提交的信息：作者、标题、变更文件、统计。"""
    author, msg, files, stat = "unknown", "no commit info", [], ""
    try:
        author = subprocess.run(["git", "log", "-1", "--format=%an"], capture_output=True, text=True, check=True).stdout.strip()
        msg = subprocess.run(["git", "log", "-1", "--format=%s"], capture_output=True, text=True, check=True).stdout.strip()
        files = subprocess.run(["git", "diff", "--name-only", "HEAD~1", "HEAD"], capture_output=True, text=True, check=True).stdout.strip().split("\n")
        stat = subprocess.run(["git", "diff", "--stat", "HEAD~1", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        pass
    return author, msg, [f for f in files if f], stat


def _build(now):
    """加载数据并组装 push 通知正文。返回 (html, commit_info)。"""
    author, commit_msg, files, stat = get_git_info()
    data = load_data()
    errors, warnings = validate_data(data)

    commit_info = {
        "author": author,
        "message": commit_msg,
        "files": [f for f in files if f],
    }

    html = build_html_digest(data, warnings, generated_at=now, commit_info=commit_info)
    return html, commit_info


def send():
    print("=" * 50)
    print("📧 双色球项目更新推送")
    print("=" * 50)

    subject = f"[双色球] 项目更新 · {beijing_time()[5:]}"
    send_digest(subject, _build)


if __name__ == "__main__":
    send()