# -*- coding: utf-8 -*-
"""
双色球每日邮件汇总 — 主入口

流程：读取环境变量配置 → 加载数据 → 校验 → 组装内容 → 发送邮件

凭证通过环境变量注入，绝不硬编码。支持 dry-run 模式。
"""

import sys

from email_content_builder import build_html_digest, load_data, validate_data
from email_smtp_utils import beijing_time, send_digest


# ==================== 主流程 ====================

def _build(now):
    """加载数据并组装每日汇总正文。返回 (html, commit_info=None)。"""
    data = load_data()
    errors, warnings = validate_data(data)
    for e in errors:
        print(f"  ❌ {e}")
    for w in warnings:
        print(f"  ⚠️ {w}")

    if errors:
        print("\n❌ 关键字段缺失，跳过本次发送")
        sys.exit(1)

    print("\n📝 组装邮件内容...")
    body = build_html_digest(data, warnings, generated_at=now)
    print("  ✓ 内容组装完成")
    return body, None


def main():
    print("=" * 50)
    print("📧 双色球每日邮件汇总")
    print("=" * 50)

    subject = f"[双色球] 每日汇总 · {beijing_time()[:10]}"
    send_digest(subject, _build)


if __name__ == "__main__":
    main()