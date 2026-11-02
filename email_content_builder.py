# -*- coding: utf-8 -*-
"""
邮件内容组装模块 — HTML 统一格式
供 email_daily_digest.py 和 email_push_notify.py 共用。

纯函数，无网络 IO：
  1. load_data()        — 读取 3 个 JSON 数据文件
  2. validate_data()    — 校验数据完整性，返回 (errors, warnings)
  3. build_html_digest() — 渲染 HTML 邮件正文（每日汇总）
"""

import html
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE     = os.path.join(BASE_DIR, "data", "lottery_history.json")
PREDICTIONS_FILE = os.path.join(BASE_DIR, "data", "ai_predictions.json")
HIT_HISTORY_FILE = os.path.join(BASE_DIR, "data", "predictions_history.json")


def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_data():
    """加载全部 3 个数据源，各自独立异常隔离。"""
    result = {"lottery_history": None, "ai_predictions": None, "hit_history": None}
    try:
        result["lottery_history"] = _load(HISTORY_FILE)
        print(f"  ✓ 双色球历史加载成功 ({len(result['lottery_history'].get('data', []))} 期)")
    except Exception as e:
        print(f"  ✗ 双色球历史加载失败: {e}")
    try:
        result["ai_predictions"] = _load(PREDICTIONS_FILE)
        print(f"  ✓ 双色球预测加载成功 ({len(result['ai_predictions'].get('models', []))} 个模型)")
    except Exception as e:
        print(f"  ✗ 双色球预测加载失败: {e}")
    try:
        result["hit_history"] = _load(HIT_HISTORY_FILE)
        recs = result["hit_history"].get("predictions_history", []) if result["hit_history"] else []
        print(f"  ✓ 双色球命中历史加载成功 ({len(recs)} 期记录)")
    except Exception as e:
        print(f"  ✗ 双色球命中历史加载失败: {e}")
    return result


def validate_data(data):
    """校验数据完整性。返回 (errors, warnings)"""
    errors, warnings = [], []
    lh = data.get("lottery_history")
    if lh is None:
        errors.append("开奖历史文件加载失败")
    elif not lh.get("data"):
        errors.append("开奖历史数据为空")
    pred = data.get("ai_predictions")
    if pred is None:
        warnings.append("预测文件加载失败，预测栏将显示为空")
    elif not pred.get("models"):
        warnings.append("暂无可用预测数据")
    hist = data.get("hit_history")
    if hist is None:
        warnings.append("命中历史文件加载失败，命中栏将显示为空")
    elif not hist.get("predictions_history"):
        warnings.append("暂无命中历史记录")
    return errors, warnings


# ==================== 共用 HTML 构建 ====================

_SECTION = '<h2 style="font-size:16px;color:#1e293b;border-left:4px solid #3b82f6;padding-left:12px;margin:24px 0 12px">{}</h2>'


def _ball(num, color, size=24):
    bg = "#ef4444" if color == "red" else "#3b82f6"
    font = 12 if size >= 24 else 11
    return (
        f'<span style="display:inline-block;width:{size}px;height:{size}px;line-height:{size}px;'
        f'text-align:center;border-radius:50%;background:{bg};color:#fff;font-size:{font}px;'
        f'font-weight:600;margin:0 1px">{num}</span>'
    )


def _build_latest_draw_html(latest, nd):
    """最新开奖 + 下期预告 HTML"""
    if not latest:
        return '<p style="color:#94a3b8;font-size:13px">(暂无数据)</p>'
    reds = "".join(_ball(b, "red") for b in latest.get("red_balls", []))
    blue = _ball(latest.get("blue_ball", ""), "blue")
    html = f'''
    <table style="width:100%;border-collapse:collapse;background:#f8fafc;border-radius:8px;overflow:hidden">
      <tr><td style="padding:12px 16px">
        <div style="font-size:14px;font-weight:700;color:#1e293b;margin-bottom:8px">
          第{latest.get("period","")}期 · {latest.get("date","")}
        </div>
        <div style="margin-bottom:6px">{reds}</div>
        <div>{blue}</div>
      </td></tr>
    </table>'''
    if nd:
        html += f'''
    <table style="width:100%;border-collapse:collapse;background:#eff6ff;border-radius:8px;overflow:hidden;margin-top:8px">
      <tr><td style="padding:10px 16px">
        <span style="font-size:13px;color:#64748b">下期预告</span>
        <span style="font-size:15px;font-weight:700;color:#1e293b;margin-left:8px">{nd.get("next_period","")}</span>
        <span style="font-size:13px;color:#475569;margin-left:8px">{nd.get("next_date_display","")} {nd.get("weekday","")} {nd.get("draw_time","21:15")}</span>
      </td></tr>
    </table>'''
    return html


# 模型淡彩（与 Web 端一致）：model_id → (背景色, 文字色)。用于邮件内的模型卡片头部。
_TINTS = {
    "markov-chain": ("#eef0ff", "#3730a3"),
    "bayesian": ("#ecfeff", "#155e75"),
    "normal-distribution": ("#eff6ff", "#1e40af"),
    "poisson": ("#f0f9ff", "#0e7490"),
    "monte-carlo": ("#faf5ff", "#6b21a8"),
    "frequency-hot": ("#fff7ed", "#9a3412"),
    "cold-miss": ("#fff1f2", "#9f1239"),
    "ewma": ("#fffbeb", "#92400e"),
    "apriori": ("#f7fee7", "#3f6212"),
    "ensemble": ("#f8fafc", "#334155"),
}


def _tint(model_id):
    return _TINTS.get(model_id, ("#f8fafc", "#334155"))


def _build_predictions_html(pred, latest_period="", next_period=""):
    """模型预测 HTML（含过期检测）"""
    if not pred or not pred.get("models"):
        return '<p style="color:#94a3b8;font-size:13px">(暂无预测数据)</p>'

    target = pred.get("target_period", "")
    # 检测预测是否已过期（目标期号 ≤ 最新开奖期号）
    stale = bool(target and latest_period) and int(target) <= int(latest_period)
    if stale:
        warn = f'''
        <div style="background:#fef3c7;border:1px solid #fde68a;border-radius:8px;padding:10px 14px;margin-bottom:12px;font-size:13px;color:#92400e">
          ⚠️ 当前预测目标为<b>第{target}期</b>，该期已开奖（最新开奖为第{latest_period}期），预测已过期。<br>
          下一期未开奖：<b>第{next_period}期</b>，待预测更新后将自动显示。
        </div>'''
    else:
        warn = ""

    models = pred["models"]

    cards = ""
    for m in models:
        groups = ""
        for g in m.get("predictions", []):
            reds = "".join(_ball(b, "red") for b in g.get("red_balls", []))
            blue = _ball(g.get("blue_ball", ""), "blue")
            desc = g.get("description", "")
            desc_html = f'<div style="font-size:11px;color:#94a3b8;margin-top:4px">{desc}</div>' if desc else ""
            groups += f'''
            <div style="padding:8px 12px;border-bottom:1px solid #f1f5f9">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                <span style="font-size:11px;font-weight:700;color:#3b82f6;background:#eff6ff;padding:2px 8px;border-radius:4px">G{g["group_id"]}</span>
                <span style="font-size:13px;font-weight:600;color:#1e293b">{g["strategy"]}</span>
              </div>
              <div style="margin-top:6px;display:flex;align-items:center;flex-wrap:wrap;gap:2px">{reds}<span style="color:#94a3b8;margin:0 4px">|</span>{blue}</div>
              {desc_html}
            </div>'''
        bg, fg = _tint(m.get("model_id", ""))
        cards += f'''
        <div style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;margin-bottom:12px">
          <div style="background:{bg};padding:10px 14px;border-bottom:1px solid #e2e8f0">
            <span style="font-size:14px;font-weight:700;color:{fg}">{m["model_name"]}</span>
          </div>
          {groups}
        </div>'''
    return f'''
    {warn}
    <div style="font-size:13px;color:#64748b;margin-bottom:12px">
      目标期号: {pred.get("target_period","")} · 预测日期: {pred.get("prediction_date","")} · 模型数: {len(models)}
    </div>
    {cards}'''


def _render_table(headers, rows):
    """渲染统一风格的邮件数据表格。

    headers: 列标题列表（首个居中、其余左对齐）
    rows: 已拼好的 <tr> 字符串列表
    """
    head_cells = "".join(
        f'<th style="padding:6px 8px;text-align:{"center" if i==0 else "left"};'
        f'color:#64748b;font-size:11px;white-space:nowrap">{h}</th>'
        for i, h in enumerate(headers)
    )
    return f'''
    <table style="width:100%;border-collapse:collapse;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;font-size:14px">
      <thead><tr style="background:#f1f5f9">{head_cells}</tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>'''


def _row(rank, cells):
    """构建单行：0-2 名奖牌 + 交替底色（浅灰/白）"""
    medal = {0: "🥇", 1: "🥈", 2: "🥉"}.get(rank, str(rank + 1))
    bg = "#f8fafc" if rank % 2 == 0 else "#ffffff"
    return (
        f'<tr style="background:{bg}">'
        f'<td style="padding:6px 8px;text-align:center;font-weight:700;font-size:13px">{medal}</td>'
        f'{cells}'
        f'</tr>'
    )


def _collect_strategy_stats(hist):
    """按「模型+策略」聚合全部历史命中。

    返回 (stats_by_key, latest_record)。每个条目的字段：
      model_id / model / strategy / total / redTotal / blueTotal / best /
      current / redHits / blueHit / games / accuracy
    其中 games 按期号去重，accuracy = 累计命中球数 / (期数 × 7)。
    """
    records = hist.get("predictions_history", []) if hist else []
    if not records:
        return {}, None

    latest_record = records[0]
    stats = {}
    for rec in records:
        is_latest = rec is latest_record
        period = (rec.get("actual_result") or {}).get("period", "")
        for m in rec.get("models", []):
            model_id = m.get("model_id") or m.get("model_name", "")
            for pred in m.get("predictions", []):
                hr = pred.get("hit_result")
                if not hr:
                    continue
                strategy = pred.get("strategy", "—")
                key = f"{model_id}|{strategy}"
                e = stats.get(key)
                if e is None:
                    e = stats[key] = {
                        "model_id": model_id,
                        "model": m.get("model_name", "—"),
                        "strategy": strategy,
                        "total": 0, "redTotal": 0, "blueTotal": 0, "best": 0,
                        "current": 0, "redHits": "—", "blueHit": False,
                        "games": 0, "periods": set(),
                    }
                t = hr.get("total_hits", 0)
                e["total"] += t
                e["redTotal"] += hr.get("red_hit_count", 0)
                e["blueTotal"] += 1 if hr.get("blue_hit") else 0
                if t > e["best"]:
                    e["best"] = t
                if period:
                    e["periods"].add(period)
                if is_latest:
                    e["current"] = t
                    rh = hr.get("red_hits", [])
                    e["redHits"] = " ".join(rh) if rh else "—"
                    e["blueHit"] = bool(hr.get("blue_hit", False))

    for e in stats.values():
        e["games"] = len(e["periods"]) or 1
        e["accuracy"] = e["total"] / (e["games"] * 7) * 100
    return stats, latest_record


def _rank_by_accuracy(stats, limit):
    """按准确率降序（并列时看累计命中、累计蓝球）。"""
    arr = sorted(
        stats.values(),
        key=lambda x: (x["accuracy"], x["total"], x["blueTotal"]),
        reverse=True,
    )
    return arr[:limit]


def _build_ranking_html(hist, limit=8):
    """命中排行 HTML — 两段式：最新一期 Top 8 + 历史累计 Top 8（按准确率）。"""
    stats, _ = _collect_strategy_stats(hist)
    if not stats:
        return '<p style="color:#94a3b8;font-size:13px;padding:12px">(暂无命中记录)</p>'

    # === 最新一期排行：按 蓝球✓ → 本期命中数 排序 ===
    latest_arr = [s for s in stats.values() if s["current"] > 0]
    latest_arr.sort(key=lambda x: (1 if x["blueHit"] else 0, x["current"]), reverse=True)
    latest_top = latest_arr[:limit]

    # === 历史累计排行：按历史准确率排序 ===
    hist_top = _rank_by_accuracy(stats, limit)

    # --- 最新一期表格 ---
    rows1 = []
    for i, r in enumerate(latest_top):
        blue_mark = "✓" if r["blueHit"] else "—"
        cells = (
            f'<td style="padding:6px 8px;font-weight:600;color:#1e293b;font-size:12px">{r["model"]}</td>'
            f'<td style="padding:6px 8px;color:#475569;font-size:11px">{r["strategy"]}</td>'
            f'<td style="padding:6px 8px;text-align:center;font-weight:700;color:#ef4444;font-size:13px">{r["current"]}球</td>'
            f'<td style="padding:6px 8px;color:#2563eb;font-size:11px;font-family:monospace">{r["redHits"]}</td>'
            f'<td style="padding:6px 8px;text-align:center;font-weight:700;color:#3b82f6;font-size:13px">{blue_mark}</td>'
        )
        rows1.append(_row(i, cells))
    table1 = (
        '<div style="font-size:13px;font-weight:700;color:#1e293b;margin:12px 0 6px">🏆 最新一期 Top 8</div>'
        + _render_table(["#", "模型", "策略", "本期命中", "命中红球", "蓝球"], rows1)
    )

    # --- 历史累计排行表格（新增「准确率」列）---
    rows2 = []
    for i, r in enumerate(hist_top):
        cells = (
            f'<td style="padding:6px 8px;font-weight:600;color:#1e293b;font-size:12px">{r["model"]}</td>'
            f'<td style="padding:6px 8px;color:#475569;font-size:11px">{r["strategy"]}</td>'
            f'<td style="padding:6px 8px;text-align:center;color:#2563eb;font-weight:700;font-size:12px">{r["accuracy"]:.1f}%</td>'
            f'<td style="padding:6px 8px;text-align:center;color:#475569;font-size:12px">{r["best"]}球</td>'
            f'<td style="padding:6px 8px;text-align:center;color:#475569;font-size:12px">{r["redTotal"]}球</td>'
            f'<td style="padding:6px 8px;text-align:center;color:#3b82f6;font-weight:600;font-size:12px">{r["blueTotal"]}球</td>'
            f'<td style="padding:6px 8px;text-align:center;color:#475569;font-size:12px">{r["games"]}期</td>'
        )
        rows2.append(_row(i, cells))
    table2 = (
        '<div style="font-size:13px;font-weight:700;color:#1e293b;margin:12px 0 6px">📊 历史累计排行 Top 8（按准确率）</div>'
        + _render_table(["#", "模型", "策略", "准确率", "历史最多", "累计红球", "累计蓝球", "期数"], rows2)
    )

    return table1 + table2


def _build_recommendations_html(hist, pred, latest_period="", limit=8):
    """本期预测推荐 — 取历史准确率 Top 8 的「模型+策略」，附上其对当前期号的预测。"""
    stats, _ = _collect_strategy_stats(hist)
    if not stats:
        return '<p style="color:#94a3b8;font-size:13px;padding:12px">(暂无命中记录)</p>'
    if not pred or not pred.get("models"):
        return '<p style="color:#94a3b8;font-size:13px;padding:12px">(暂无预测数据)</p>'

    target = pred.get("target_period", "")
    try:
        stale = bool(target and latest_period) and int(target) <= int(latest_period)
    except (TypeError, ValueError):
        stale = False
    if stale:
        return (
            f'<p style="color:#92400e;font-size:13px;padding:12px;background:#fef3c7;'
            f'border-radius:8px">⚠️ 当前预测目标第{target}期已开奖，暂无有效本期预测。</p>'
        )

    current = {}
    for m in pred.get("models", []):
        model_id = m.get("model_id") or m.get("model_name", "")
        for p in m.get("predictions", []):
            current[(model_id, p.get("strategy", "—"))] = p

    rows = []
    for i, r in enumerate(_rank_by_accuracy(stats, limit)):
        p = current.get((r["model_id"], r["strategy"]))
        if p:
            reds = "".join(_ball(b, "red", size=20) for b in p.get("red_balls", []))
            blue = _ball(p.get("blue_ball", ""), "blue", size=20)
            pred_html = (
                f'<div style="white-space:nowrap">{reds}'
                f'<span style="color:#cbd5e1;margin:0 3px">|</span>{blue}</div>'
            )
        else:
            pred_html = '<span style="color:#94a3b8">—</span>'
        cells = (
            f'<td style="padding:6px 8px;font-weight:600;color:#1e293b;font-size:12px;white-space:nowrap">{r["model"]}</td>'
            f'<td style="padding:6px 8px;color:#475569;font-size:11px;white-space:nowrap">{r["strategy"]}</td>'
            f'<td style="padding:6px 8px;text-align:center;color:#2563eb;font-weight:700;font-size:12px">{r["accuracy"]:.1f}%</td>'
            f'<td style="padding:6px 8px;text-align:center;color:#475569;font-size:12px;white-space:nowrap">{r["total"]}球</td>'
            f'<td style="padding:6px 8px;text-align:center">{pred_html}</td>'
        )
        rows.append(_row(i, cells))

    note = (
        f'<div style="font-size:12px;color:#64748b;margin-bottom:6px">'
        f'目标期号 {target} · 按历史累计准确率选取前 {limit} 组「模型+策略」</div>'
    )
    return note + _render_table(
        ["#", "模型", "策略", "准确率", "累计命中", "本期预测"], rows
    )


def _build_grouped_stats_html(hist, limit=8):
    """模型分组统计 HTML — 按模型聚合全部历史命中（每期 4 组求和，期数按期去重）。

    limit 默认 8（邮件只展示前 8 名）；传 None 或 0 显示全部模型。"""
    records = hist.get("predictions_history", []) if hist else []
    if not records:
        return '<p style="color:#94a3b8;font-size:13px;padding:12px">(暂无命中记录)</p>'

    stats = {}
    for rec in records:
        period = (rec.get("actual_result") or {}).get("period")
        for m in rec.get("models", []):
            for pred in (m.get("predictions") or []):
                hr = pred.get("hit_result")
                if not hr:
                    continue
                name = m.get("model_name", "—")
                e = stats.get(name)
                if e is None:
                    e = stats[name] = {"name": name, "maxHits": 0, "redTotal": 0,
                                       "blueTotal": 0, "total": 0, "periods": set()}
                t = hr.get("total_hits", 0)
                e["redTotal"] += hr.get("red_hit_count", 0)
                e["blueTotal"] += 1 if hr.get("blue_hit") else 0
                e["total"] += t
                if t > e["maxHits"]:
                    e["maxHits"] = t
                if period:
                    e["periods"].add(period)
    for e in stats.values():
        e["games"] = len(e["periods"])

    arr = sorted(stats.values(), key=lambda x: (x["total"], x["blueTotal"]), reverse=True)
    if limit:
        arr = arr[:limit]

    rows = []
    for i, r in enumerate(arr):
        name = html.escape(str(r["name"]))
        cells = (
            f'<td style="padding:6px 8px;font-weight:600;color:#1e293b;font-size:12px">{name}</td>'
            f'<td style="padding:6px 8px;text-align:center;color:#475569;font-size:12px">{r["maxHits"]}球</td>'
            f'<td style="padding:6px 8px;text-align:center;color:#475569;font-size:12px">{r["redTotal"]}球</td>'
            f'<td style="padding:6px 8px;text-align:center;color:#3b82f6;font-weight:600;font-size:12px">{r["blueTotal"]}球</td>'
            f'<td style="padding:6px 8px;text-align:center;color:#475569;font-size:12px">{r["total"]}球</td>'
            f'<td style="padding:6px 8px;text-align:center;color:#475569;font-size:12px">{r["games"]}期</td>'
        )
        rows.append(_row(i, cells))

    return _render_table(["#", "模型", "历史最大单期", "总红数", "总蓝球", "总球数", "期数"], rows)


def build_html_digest(data, warnings, generated_at, commit_info=None):
    """
    构建 HTML 邮件正文。

    参数:
        data: load_data() 返回的 3 个数据源
        warnings: validate_data() 返回的警告列表
        generated_at: 生成时间字符串
        commit_info: 可选，push 通知的提交信息 dict，含 author / message / files / stat
    """
    lh = data.get("lottery_history") or {}
    pred = data.get("ai_predictions") or {}
    hist = data.get("hit_history") or {}
    latest = lh.get("data", [{}])[0] if lh.get("data") else {}
    nd = lh.get("next_draw", {})
    latest_period = latest.get("period", "")
    next_period = nd.get("next_period", "")

    # 邮件类型（决定 subtitle 和 footer）
    is_push = commit_info is not None
    subtitle = "项目更新通知" if is_push else "每日汇总"

    # 警告
    warn_html = ""
    if warnings:
        items = "".join(f'<li style="font-size:12px;color:#d97706;padding:2px 0">⚠️ {w}</li>' for w in warnings)
        warn_html = f'<div style="background:#fef3c7;border:1px solid #fde68a;border-radius:8px;padding:12px 16px;margin-bottom:16px"><ul style="margin:0;padding-left:20px">{items}</ul></div>'

    # 提交信息（仅 push 通知）
    commit_html = ""
    if is_push:
        author = commit_info.get("author", "unknown")
        msg = commit_info.get("message", "")
        files = commit_info.get("files", [])
        files_html = ""
        if files:
            items = "".join(f'<li style="font-size:13px;color:#475569;padding:2px 0">{f}</li>' for f in files)
            files_html = f'<ul style="margin:8px 0 0;padding-left:20px">{items}</ul>'
        commit_html = f'''
        {_SECTION.format("📦 提交信息")}
        <table style="width:100%;border-collapse:collapse;background:#f8fafc;border-radius:8px;overflow:hidden">
          <tr><td style="padding:12px 16px">
            <div style="font-size:13px;color:#475569;margin-bottom:4px"><span style="color:#94a3b8">作者</span> {author}</div>
            <div style="font-size:14px;font-weight:600;color:#1e293b">{msg}</div>
            {files_html}
          </td></tr>
        </table>'''

    # 模型分组统计（全部历史）— 只展示前 8 名
    grouped_html = (
        f'{_SECTION.format("📦 模型分组统计 Top 8（全部历史）")}'
        f'{_build_grouped_stats_html(hist, limit=8)}'
    )

    # Footer
    footer_text = (
        '本邮件由 GitHub Actions 自动推送'
        if is_push else
        '本邮件由自动系统生成 · 彩票预测仅供娱乐参考，不构成投资建议'
    )

    html = f'''
    <div style="max-width:600px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;background:#ffffff;padding:0;color:#1e293b">
      <div style="border-top:4px solid #3b82f6;padding:24px;text-align:center">
        <div style="font-size:24px;margin-bottom:4px">🎯</div>
        <h1 style="color:#1e293b;font-size:18px;font-weight:800;margin:0">双色球 模型预测</h1>
        <p style="color:#64748b;font-size:12px;margin:4px 0 0">{subtitle} · {generated_at}</p>
      </div>
      <div style="padding:8px 24px 20px">
        {warn_html}
        {commit_html}
        {_SECTION.format("🏆 最新开奖")}
        {_build_latest_draw_html(latest, nd)}
        {_SECTION.format("📊 命中排行 Top 8")}
        {_build_ranking_html(hist, limit=8)}
        {_SECTION.format("🎯 本期预测推荐 · 历史准确率 Top 8")}
        {_build_recommendations_html(hist, pred, latest_period, limit=8)}
        {grouped_html}
        {_SECTION.format("🔮 模型预测（完整 40 组）")}
        {_build_predictions_html(pred, latest_period, next_period)}
      </div>
      <div style="background:#f8fafc;padding:16px 24px;text-align:center;border-top:1px solid #e2e8f0;border-radius:0 0 12px 12px">
        <p style="font-size:12px;color:#94a3b8;margin:0">
          {footer_text}<br>
          <a href="https://github.com/zhens/double-color-ball" style="color:#3b82f6;text-decoration:none">double-color-ball</a>
        </p>
      </div>
    </div>'''
    return html