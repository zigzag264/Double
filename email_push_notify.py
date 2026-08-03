# -*- coding: utf-8 -*-
"""
Push 触发邮件通知脚本 — 增强版
在 GitHub Actions 中由 push 事件触发，发送详细更新摘要到邮箱。

内容包含：
  - 提交信息
  - 最新开奖数据
  - AI 全部预测（6 模型 × 5 策略）
  - 优劣排行前十（模型+策略命中率）
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


def _data_path(name):
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", name
    )


# ==================== 数据获取 ====================

def get_git_info():
    """获取最近一次提交的信息"""
    try:
        author = subprocess.run(
            ["git", "log", "-1", "--format=%an"],
            capture_output=True, text=True, check=True
        ).stdout.strip()
        msg = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            capture_output=True, text=True, check=True
        ).stdout.strip()
        files = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True, check=True
        ).stdout.strip().split("\n")
        stat = subprocess.run(
            ["git", "diff", "--stat", "HEAD~1", "HEAD"],
            capture_output=True, text=True, check=True
        ).stdout.strip()
        return author, msg, [f for f in files if f], stat
    except Exception as e:
        return "unknown", "no commit info", [], str(e)


def get_latest_draw():
    """获取最新开奖数据"""
    try:
        with open(_data_path("lottery_history.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        latest = data.get("data", [{}])[0]
        nd = data.get("next_draw", {})
        return latest, nd
    except Exception as e:
        return {}, {}


def get_all_predictions():
    """获取全部 AI 预测详情"""
    try:
        with open(_data_path("ai_predictions.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        return None


def get_hit_rankings():
    """
    获取历史命中排行 Top 10（按模型+策略）。
    每行显示：本期命中球数 / 具体命中号码 / 历史命中总和 / 历史最多命中 / 总期数。
    排序：本期命中球数 → 历史最多命中球数 → 历史命中球数总和。
    """
    try:
        with open(_data_path("predictions_history.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return [], ""

    records = data.get("predictions_history", [])
    if not records:
        return [], "暂无命中记录"

    # 最新一期 = records[0]（按归档顺序，最新在前）
    latest_record = records[0]

    stats = {}
    for rec in records:
        is_latest = (rec is latest_record)
        for m in rec.get("models", []):
            for pred in m.get("predictions", []):
                hr = pred.get("hit_result")
                if not hr:
                    continue
                key = f"{m['model_name']}|{pred.get('strategy','—')}"
                if key not in stats:
                    stats[key] = {
                        "model": m["model_name"],
                        "strategy": pred.get("strategy", "—"),
                        "total": 0,       # 历史命中球数总和
                        "best": 0,         # 历史最多命中球数
                        "games": 0,        # 总预测期数
                        "current": 0,      # 本期命中球数
                        "hits": "",        # 本期具体命中号码
                    }
                t = hr.get("total_hits", 0)
                stats[key]["total"] += t
                stats[key]["games"] += 1
                if t > stats[key]["best"]:
                    stats[key]["best"] = t
                if is_latest:
                    stats[key]["current"] = t
                    # 组装具体命中号码
                    red_hits = hr.get("red_hits", [])
                    blue_hit = hr.get("blue_hit", False)
                    parts = []
                    if red_hits:
                        parts.append("红:" + " ".join(red_hits))
                    if blue_hit:
                        parts.append("蓝✓")
                    stats[key]["hits"] = " ".join(parts) if parts else "—"

    # 排序：本期命中球数 ↓ → 历史最多命中球数 ↓ → 历史命中球数总和 ↓
    sorted_stats = sorted(stats.values(),
                          key=lambda x: (x["current"], x["best"], x["total"]),
                          reverse=True)
    return sorted_stats[:10], ""


# ==================== 邮件内容组装 ====================

S = "━" * 34


def build_latest_draw_section(latest, nd):
    """【最新开奖】"""
    if not latest:
        return "【最新开奖】\n  (暂无数据)\n"
    lines = [
        "【最新开奖】",
        f"  期号  : {latest.get('period', '—')}",
        f"  日期  : {latest.get('date', '—')}",
        f"  红球  : {' '.join(latest.get('red_balls', []))}",
        f"  蓝球  : {latest.get('blue_ball', '')}",
        "",
        "【下期预告】",
        f"  期号  : {nd.get('next_period', '—')}",
        f"  开奖  : {nd.get('next_date_display', '—')} {nd.get('weekday', '')} {nd.get('draw_time', '21:15')}",
        "",
    ]
    return "\n".join(lines)


def build_predictions_section(pred):
    """【AI 全部预测】— 6 模型 × 5 策略"""
    if not pred or not pred.get("models"):
        return "【AI 全部预测】\n  (暂无预测数据)\n"

    lines = [
        "【AI 全部预测】",
        f"  目标期号: {pred.get('target_period', '—')}  "
        f"预测日期: {pred.get('prediction_date', '—')}  "
        f"模型数: {len(pred['models'])}",
        "",
    ]

    for m in pred["models"]:
        lines.append(f"  ── {m['model_name']} ──")
        for g in m.get("predictions", []):
            reds = " ".join(g.get("red_balls", []))
            line = (
                f"    [G{g['group_id']}] {g.get('strategy', '')}\n"
                f"          红球: {reds}  蓝球: {g.get('blue_ball', '')}"
            )
            desc = g.get("description", "")
            if desc:
                line += f"\n          {desc}"
            lines.append(line)
        lines.append("")

    return "\n".join(lines)


def build_ranking_section(rankings, empty_msg):
    """【优劣排行前十】"""
    lines = ["【优劣排行前十】"]
    if not rankings:
        lines.append(f"  ({empty_msg})\n")
        return "\n".join(lines)

    lines.append(f"  {'排名':>3s}  {'模型':<20s} {'策略':<18s} {'本期命中':>6s} {'命中号码':<22s} {'历史总和':>6s} {'历史最多':>6s} {'期数':>3s}")
    lines.append(f"  {'─'*3}  {'─'*20} {'─'*18} {'─'*6} {'─'*22} {'─'*6} {'─'*6} {'─'*3}")
    for i, r in enumerate(rankings):
        lines.append(
            f"  {i+1:>3d}  {r['model']:<20s} {r['strategy']:<18s} "
            f"{r['current']:>3d}球  {r['hits']:<22s} {r['total']:>4d}球  {r['best']:>3d}球  {r['games']:>3d}期"
        )
    lines.append("")
    return "\n".join(lines)


def build_body():
    author, commit_msg, files, stat = get_git_info()
    latest, nd = get_latest_draw()
    pred = get_all_predictions()
    rankings, empty_msg = get_hit_rankings()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    sections = []

    # 头部
    sections.append(S)
    sections.append("  双色球 AI 预测 · 项目更新通知")
    sections.append(f"  推送时间: {now}")
    sections.append(S)
    sections.append("")

    # 提交信息
    sections.append("【提交信息】")
    sections.append(f"  作者: {author}")
    sections.append(f"  提交: {commit_msg}")
    sections.append("")
    if files and files[0]:
        sections.append("  变更文件:")
        for f in files:
            sections.append(f"    - {f}")
    else:
        sections.append("  (首次提交或因 squash 无法获取变更列表)")
    sections.append("")
    if stat:
        sections.append(f"  统计: {stat.split(chr(10))[0] if chr(10) in stat else stat}")
    sections.append("")

    # 最新开奖
    sections.append(build_latest_draw_section(latest, nd))

    # 优劣排行前十
    sections.append(build_ranking_section(rankings, empty_msg))

    # AI 全部预测
    sections.append(build_predictions_section(pred))

    # 尾部
    sections.append(S)
    sections.append("  本邮件由 GitHub Actions 自动推送")
    sections.append("  https://github.com/zhens/double-color-ball")
    sections.append(S)

    return "\n".join(sections)


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