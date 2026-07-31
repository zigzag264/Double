# -*- coding: utf-8 -*-
"""
双色球每日邮件汇总 — 主入口

流程：读取环境变量配置 → 加载数据 → 校验 → 组装内容 → 发送邮件

凭证通过环境变量注入，绝不硬编码。支持 dry-run 模式。
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

from email_content_builder import build_email_content, load_data, validate_data

# ==================== 配置（全部环境变量）====================

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.qq.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASSWORD")
RECIPIENT = os.environ.get("EMAIL_RECIPIENT")
DRY_RUN = os.environ.get("EMAIL_DRY_RUN", "").lower() == "true"

# ==================== 启动校验 ====================

REQUIRED = [SMTP_USER, SMTP_PASS, RECIPIENT]
if not all(REQUIRED):
    print("❌ 缺少邮件凭证，请设置以下环境变量：")
    print("   SMTP_USER       — QQ 邮箱地址")
    print("   SMTP_PASSWORD   — QQ 邮箱授权码（非登录密码）")
    print("   EMAIL_RECIPIENT — 收件人邮箱地址")
    sys.exit(1)

if DRY_RUN:
    print("ℹ️  Dry-run 模式：邮件将打印到控制台，不会实际发送\n")


# ==================== 邮件构建 ====================

def build_message(subject, body):
    """构建 MIME 纯文本邮件"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = RECIPIENT
    msg.attach(MIMEText(body, "plain", "utf-8"))
    return msg


def send_email(subject, body):
    """发送或打印邮件"""
    if DRY_RUN:
        print("=" * 60)
        print(f"[DRY-RUN] 收件人: {RECIPIENT}")
        print(f"[DRY-RUN] 主题: {subject}")
        print("=" * 60)
        print(body)
        print("=" * 60)
        print("ℹ️  Dry-run 模式，邮件未实际发送")
        return

    msg = build_message(subject, body)
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [RECIPIENT], msg.as_string())
        print("✅ 邮件发送成功")
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ SMTP 认证失败: {e}")
        print("   请检查：")
        print("   1. QQ 邮箱是否已开启 SMTP 服务")
        print("   2. SMTP_PASSWORD 是否为授权码（而非登录密码）")
        raise
    except smtplib.SMTPException as e:
        print(f"❌ SMTP 错误: {e}")
        raise


# ==================== 主流程 ====================

def main():
    print("=" * 50)
    print("📧 双色球每日邮件汇总")
    print("=" * 50)

    # 1. 加载数据
    print("\n📊 加载数据...")
    data = load_data()

    # 2. 校验
    print("\n🔍 校验数据完整性...")
    errors, warnings = validate_data(data)
    for e in errors:
        print(f"  ❌ {e}")
    for w in warnings:
        print(f"  ⚠️ {w}")

    if errors:
        print("\n❌ 关键字段缺失，跳过本次发送")
        sys.exit(1)

    # 3. 组装内容
    print("\n📝 组装邮件内容...")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = build_email_content(data, warnings, generated_at=now)
    subject = "AI 预测"
    print("  ✓ 内容组装完成")

    # 4. 发送
    print("\n📤 发送邮件...")
    send_email(subject, body)

    print("\n" + "=" * 50)
    print("🎉 邮件汇总完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
