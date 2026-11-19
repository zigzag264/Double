# -*- coding: utf-8 -*-
"""
邮件内容组装模块 — HTML 统一格式
供 email_daily_digest.py 和 email_push_notify.py 共用。

纯函数，无网络 IO：
  1. load_data()        — 读取 3 个 JSON 数据文件
  2. validate_data()    — 校验数据完整性，返回 (errors, warnings)
  3. build_html_digest() — 渲染 HTML 邮件正文（定时汇总）
"""

import html
import os
import json
from datetime import datetime, time as dtime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE     = os.path.join(BASE_DIR, "data", "lottery_history.json")
PREDICTIONS_FILE = os.path.join(BASE_DIR, "data", "ai_predictions.json")
HIT_HISTORY_FILE = os.path.join(BASE_DIR, "data", "predictions_history.json")

# 双色球开奖：每周二/四/日 21:15（北京时间）
BEIJING_TZ = timezone(timedelta(hours=8))
DRAW_TIME = dtime(21, 15)


def _beijing_now():
    return datetime.now(BEIJING_TZ)


def _parse_draw_datetime(date_str):
    """把 'YYYY-MM-DD' 解析为当天 21:15 的北京时间；格式非法返回 None。"""
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None
    return datetime.combine(day, DRAW_TIME, BEIJING_TZ)


def next_draw_passed(nd, now=None):
    """下期预告的开奖时间已过 → 开奖数据未更新（爬虫滞后）。"""
    draw_dt = _parse_draw_datetime((nd or {}).get("next_date", ""))
    return bool(draw_dt) and (now or _beijing_now()) >= draw_dt


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


def _build_latest_draw_html(latest, nd, data_stale=False):
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
        stale_note = (
            '<div style="font-size:12px;color:#b45309;margin-top:6px">'
            '⚠️ 该开奖时间已过但仍未获取到开奖结果，开奖数据可能尚未更新'
            '</div>'
        ) if data_stale else ""
        html += f'''
    <table style="width:100%;border-collapse:collapse;background:#eff6ff;border-radius:8px;overflow:hidden;margin-top:8px">
      <tr><td style="padding:10px 16px">
        <span style="font-size:13px;color:#64748b">下期预告</span>
        <span style="font-size:15px;font-weight:700;color:#1e293b;margin-left:8px">{nd.get("next_period","")}</span>
        <span style="font-size:13px;color:#475569;margin-left:8px">{nd.get("next_date_display","")} {nd.get("weekday","")} {nd.get("draw_time","21:15")}</span>
        {stale_note}
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


def _build_predictions_html(pred, latest_period="", next_period="", top_by_model=None, data_stale=False):
    """模型推荐 HTML（含过期检测；每个模型只展示历史准确率前 3 种策略）。"""
    if not pred or not pred.get("models"):
        return '<p style="color:#94a3b8;font-size:13px">(暂无预测数据)</p>'

    target = pred.get("target_period", "")
    # 检测预测是否已过期：目标期号 ≤ 最新开奖期号，或下期预告已过开奖时间（数据未更新）
    try:
        target_drawn = bool(target and latest_period) and int(target) <= int(latest_period)
    except (TypeError, ValueError):
        target_drawn = False
    stale = data_stale or target_drawn
    if stale:
        # 过期预测不再展示号码，避免把已开奖期号的推荐再次推送出去
        return f'''
        <div style="background:#fef3c7;border:1px solid #fde68a;border-radius:8px;padding:10px 14px;margin-bottom:12px;font-size:13px;color:#92400e">
          ⚠️ 当前预测目标为<b>第{target or "?"}期</b>，该期已开奖或开奖数据尚未更新（最新开奖为第{latest_period}期），预测已过期，过期号码已隐藏。<br>
          下一期未开奖：<b>第{next_period}期</b>，待预测更新后将自动显示。
        </div>'''

    models = pred["models"]
    total_groups = 0

    cards = ""
    for m in models:
        predictions = _filter_model_predictions(m, top_by_model, TOP_STRATEGIES_PER_MODEL)
        total_groups += len(predictions)
        groups = ""
        for idx, g in enumerate(predictions, 1):
            reds = "".join(_ball(b, "red") for b in g.get("red_balls", []))
            blue = _ball(g.get("blue_ball", ""), "blue")
            desc = g.get("description", "")
            desc_html = f'<div style="font-size:11px;color:#94a3b8;margin-top:4px">{desc}</div>' if desc else ""
            groups += f'''
            <div style="padding:8px 12px;border-bottom:1px solid #f1f5f9">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                <span style="font-size:11px;font-weight:700;color:#3b82f6;background:#eff6ff;padding:2px 8px;border-radius:4px">G{idx}</span>
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
    <div style="font-size:13px;color:#64748b;margin-bottom:12px">
      目标期号: {pred.get("target_period","")} · 预测日期: {pred.get("prediction_date","")} · 模型数: {len(models)} · 每组策略: {TOP_STRATEGIES_PER_MODEL} · 共 {total_groups} 组
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


TOP_STRATEGIES_PER_MODEL = 3


def _top_strategies_by_model(hist, limit=TOP_STRATEGIES_PER_MODEL):
    """每个模型按历史准确率取前 limit 种策略，返回 {model_id: {strategy, ...}}。

    准确率 = 累计命中球数 / (期数 × 7)；并列时依次看累计命中、累计蓝球。
    """
    records = hist.get("predictions_history", []) if hist else []
    agg = {}
    for rec in records:
        period = (rec.get("actual_result") or {}).get("period", "")
        for m in rec.get("models", []):
            model_id = m.get("model_id") or m.get("model_name", "")
            for pred in m.get("predictions", []):
                hr = pred.get("hit_result")
                if not hr:
                    continue
                strategy = pred.get("strategy", "—")
                e = agg.get((model_id, strategy))
                if e is None:
                    e = agg[(model_id, strategy)] = {"total": 0, "blue": 0, "periods": set()}
                e["total"] += hr.get("total_hits", 0)
                e["blue"] += 1 if hr.get("blue_hit") else 0
                if period:
                    e["periods"].add(period)

    grouped = {}
    for (model_id, strategy), e in agg.items():
        games = len(e["periods"]) or 1
        grouped.setdefault(model_id, []).append({
            "strategy": strategy,
            "accuracy": e["total"] / (games * 7),
            "total": e["total"],
            "blue": e["blue"],
        })

    result = {}
    for model_id, items in grouped.items():
        items.sort(key=lambda x: (-x["accuracy"], -x["total"], -x["blue"], x["strategy"]))
        result[model_id] = {x["strategy"] for x in items[:limit]}
    return result


def _filter_model_predictions(model, top_by_model, limit=TOP_STRATEGIES_PER_MODEL):
    """过滤模型当前预测，只保留历史准确率前 limit 的策略。

    若历史可判定策略不足 limit 种，按原有顺序补齐，保证最多展示 limit 组。
    """
    preds = model.get("predictions", [])
    model_id = model.get("model_id") or model.get("model_name", "")
    allowed = (top_by_model or {}).get(model_id)
    if not allowed:
        return preds

    kept = [p for p in preds if p.get("strategy", "—") in allowed]
    if len(kept) < limit:
        seen = {p.get("strategy", "—") for p in kept}
        for p in preds:
            strategy = p.get("strategy", "—")
            if strategy in seen:
                continue
            kept.append(p)
            seen.add(strategy)
            if len(kept) >= limit:
                break

    order = {p.get("strategy", "—"): i for i, p in enumerate(preds)}
    kept.sort(key=lambda p: order.get(p.get("strategy", "—"), len(preds)))
    return kept[:limit]


def _collect_strategy_stats(hist, top_by_model=None):
    """按「模型+策略」聚合全部历史命中。

    返回 (stats_by_key, latest_record)。每个条目的字段：
      model_id / model / strategy / total / redTotal / blueTotal / best /
      current / redHits / blueHit / games / accuracy
    其中 games 按期号去重，accuracy = 累计命中球数 / (期数 × 7)。
    传入 top_by_model 时只统计各模型历史准确率前 3 的策略。
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
            allowed = (top_by_model or {}).get(model_id)
            for pred in m.get("predictions", []):
                hr = pred.get("hit_result")
                if not hr:
                    continue
                strategy = pred.get("strategy", "—")
                if allowed is not None and strategy not in allowed:
                    continue
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


def _build_ranking_parts(hist, limit=8, top_by_model=None):
    """命中排行 HTML — 拆分为 (最新一期表格, 历史累计表格)，便于邮件排序。"""
    stats, _ = _collect_strategy_stats(hist, top_by_model)
    if not stats:
        return '<p style="color:#94a3b8;font-size:13px;padding:12px">(暂无命中记录)</p>', ''

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
    table1 = _render_table(["#", "模型", "策略", "本期命中", "命中红球", "蓝球"], rows1)

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
    table2 = _render_table(
        ["#", "模型", "策略", "准确率", "历史最多", "累计红球", "累计蓝球", "期数"], rows2
    )

    return table1, table2


def _build_single_ball_hits_html(hist, latest, top_by_model=None):
    """单球命中 — 最新一期 7 个开奖球分别被哪些模型命中；0 命中留空。"""
    records = hist.get("predictions_history", []) if hist else []
    if not records or not latest:
        return '<p style="color:#94a3b8;font-size:13px;padding:12px">(暂无命中数据)</p>'

    record = records[0]
    if latest.get("period") and record.get("target_period") and \
            latest["period"] != record["target_period"]:
        return '<p style="color:#94a3b8;font-size:13px;padding:12px">(最新一期暂无命中数据)</p>'

    red_balls = latest.get("red_balls", [])
    blue_ball = latest.get("blue_ball", "")
    red_models = {ball: [] for ball in red_balls}
    seen_red = {ball: set() for ball in red_balls}
    blue_models = []
    seen_blue = set()

    # 只统计各模型保留的前 3 种策略；同一模型命中多个球只记一次
    for m in record.get("models", []):
        model_id = m.get("model_id") or m.get("model_name", "")
        allowed = (top_by_model or {}).get(model_id)
        model_name = m.get("model_name", "—")
        for pred in m.get("predictions", []):
            if allowed is not None and pred.get("strategy", "—") not in allowed:
                continue
            hr = pred.get("hit_result") or {}
            for ball in hr.get("red_hits", []):
                if ball in red_models and model_name not in seen_red[ball]:
                    seen_red[ball].add(model_name)
                    red_models[ball].append(model_name)
            if hr.get("blue_hit") and model_name not in seen_blue:
                seen_blue.add(model_name)
                blue_models.append(model_name)

    rows = []
    ordered = [(ball, "red") for ball in red_balls] + [(blue_ball, "blue")]
    for i, (ball, color) in enumerate(ordered):
        if color == "red":
            names = red_models.get(ball, [])
        else:
            names = blue_models
        model_text = "、".join(html.escape(str(n)) for n in names) or "&nbsp;"
        bg = "#f8fafc" if i % 2 == 0 else "#ffffff"
        rows.append(
            f'<tr style="background:{bg}">'
            f'<td style="padding:6px 8px;text-align:center;width:64px">{_ball(ball, color, size=20)}</td>'
            f'<td style="padding:6px 8px;color:#475569;font-size:12px;line-height:1.6">{model_text}</td>'
            f'</tr>'
        )

    note = (
        f'<div style="font-size:12px;color:#64748b;margin-bottom:6px">'
        f'第{latest.get("period","")}期 · 按每个模型保留的前 3 种策略统计；未命中留空</div>'
    )
    return note + _render_table(["开奖球", "命中模型"], rows)


# 邮件「最佳组合」内的名称精简：模型名 → 短名；策略名 → 去掉模型前缀后的差异部分
_SHORT_MODEL = {
    "马尔可夫链": "马尔可夫",
    "贝叶斯推断": "贝叶斯",
    "正态分布(Z-score)": "正态Z",
    "泊松分布": "泊松",
    "蒙特卡洛模拟": "蒙特卡洛",
    "频率热号": "热号",
    "遗漏回补": "遗漏",
    "指数平滑(EWMA)": "EWMA",
    "关联规则": "关联",
    "集成投票": "集成",
}

_SHORT_STRATEGY = {
    "平稳分布融合": "平稳融合",
    "贝叶斯·三窗后验": "三窗后验",
    "贝叶斯·全史后验": "全史后验",
    "Z高分热选": "高分热选",
    "Z低分回补": "低分回补",
    "和值约束Z选": "和值Z",
    "三区间Z平衡": "区间Z",
    "强遗漏回补": "强回补",
    "期望回补": "期望",
    "集成+频率融合": "频率融合",
    "关联规则·上期红球种子": "上期红球",
    "关联规则·热号种子": "热号种子",
    "关联规则·热号种子·提升度": "热号提升",
    "关联规则·近20期上期种子": "近20上期",
}


def _short_model_name(name):
    name = str(name or "—")
    return _SHORT_MODEL.get(name, name.split("(")[0][:6])


def _short_strategy_name(strategy):
    """策略名精简：优先查表，其次去掉「模型·」前缀与冗余后缀。"""
    strategy = str(strategy or "—")
    if strategy in _SHORT_STRATEGY:
        return _SHORT_STRATEGY[strategy]
    s = strategy.split("·", 1)[1] if "·" in strategy else strategy
    for suffix in ("马尔可夫", "投票", "约束", "回补"):
        if s.endswith(suffix) and len(s) - len(suffix) >= 2:
            return s[: -len(suffix)]
    return s


def _build_best_combinations_html(hist, ai_pred=None, latest_period="", top_by_model=None,
                                  limit=10, min_red_hits=4, data_stale=False):
    """最佳组合 — 两两组合不同的「模型+策略」，统计同一期红球去重后 ≥4 球的次数，
    按该次数与最高命中排序；同时展示该组合对下期未开奖期号的预测号码。"""
    records = hist.get("predictions_history", []) if hist else []
    if not records:
        return '<p style="color:#94a3b8;font-size:13px;padding:12px">(暂无命中记录)</p>'

    pair_stats = {}
    for rec in records:
        entries = []
        seen = set()
        for m in rec.get("models", []):
            model_id = m.get("model_id") or m.get("model_name", "")
            allowed = (top_by_model or {}).get(model_id)
            model_name = m.get("model_name", "—")
            for pred in m.get("predictions", []):
                strategy = pred.get("strategy", "—")
                if allowed is not None and strategy not in allowed:
                    continue
                hr = pred.get("hit_result")
                if not hr:
                    continue
                key = (model_id, strategy)
                if key in seen:
                    continue
                seen.add(key)
                hits = set(hr.get("red_hits", []))
                if hr.get("blue_hit"):
                    hits.add("__blue__")
                entries.append((
                    key,
                    _short_model_name(model_name),
                    _short_strategy_name(strategy),
                    hits,
                ))

        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                k1, n1, s1, h1 = entries[i]
                k2, n2, s2, h2 = entries[j]
                pair_key = tuple(sorted([k1, k2]))
                e = pair_stats.get(pair_key)
                if e is None:
                    if k1 <= k2:
                        names = (n1, s1, n2, s2)
                        keys = (k1, k2)
                    else:
                        names = (n2, s2, n1, s1)
                        keys = (k2, k1)
                    e = pair_stats[pair_key] = {
                        "names": names, "keys": keys,
                        "red4": 0, "periods": 0, "max": 0, "sum": 0,
                    }
                total = len(h1 | h2)
                red_total = len({h for h in (h1 | h2) if h != "__blue__"})
                e["periods"] += 1
                e["sum"] += total
                if total > e["max"]:
                    e["max"] = total
                if red_total >= min_red_hits:
                    e["red4"] += 1

    arr = [e for e in pair_stats.values() if e["red4"] > 0]
    if not arr:
        return f'<p style="color:#94a3b8;font-size:13px;padding:12px">(暂无单期 ≥{min_red_hits} 红球的组合)</p>'

    arr.sort(key=lambda x: (
        -x["red4"], -x["max"], -(x["sum"] / x["periods"]), x["names"]
    ))
    arr = arr[:limit]
    stat_periods = max(e["periods"] for e in pair_stats.values())

    # 下期未开奖预测索引：{(model_id, strategy): prediction}
    pred_map = {}
    target_period = str(ai_pred.get("target_period", "")) if ai_pred else ""
    pred_valid = False
    try:
        pred_valid = bool(target_period) and int(target_period) > int(latest_period)
    except (TypeError, ValueError):
        pred_valid = bool(target_period) and target_period != latest_period
    if data_stale:
        pred_valid = False
    if pred_valid:
        for model in ai_pred.get("models", []):
            model_id = model.get("model_id") or model.get("model_name", "")
            for p in model.get("predictions", []):
                pred_map[(model_id, p.get("strategy", ""))] = p

    def _combo_line(label, color, name, strategy, key):
        head = (
            f'<div style="font-size:12px;color:#1e293b;line-height:1.45">'
            f'<span style="color:{color};font-weight:700">{label}</span> '
            f'{html.escape(str(name))} · {html.escape(str(strategy))}</div>'
        )
        p = pred_map.get(key)
        if p and p.get("red_balls") and p.get("blue_ball"):
            reds = " ".join(html.escape(str(x)) for x in p["red_balls"])
            blue = html.escape(str(p["blue_ball"]))
            nums = (
                f'<div style="font-size:11px;font-family:Consolas,Menlo,monospace;'
                f'color:#dc2626;letter-spacing:.4px;margin:1px 0 3px 17px">'
                f'{reds} <span style="color:#2563eb;font-weight:700">+{blue}</span></div>'
            )
        else:
            msg = "（下期无该策略预测）" if pred_valid else "（当前预测已过期）"
            nums = f'<div style="font-size:10px;color:#94a3b8;margin:1px 0 3px 17px">{msg}</div>'
        return head + nums

    rows = []
    for i, e in enumerate(arr):
        n1, s1, n2, s2 = e["names"]
        k1, k2 = e["keys"]
        combo = (
            _combo_line("A", "#2563eb", n1, s1, k1)
            + _combo_line("B", "#3b82f6", n2, s2, k2)
        )
        cells = (
            f'<td style="padding:6px 8px">{combo}</td>'
            f'<td style="padding:6px 8px;text-align:center;font-weight:700;color:#dc2626;font-size:12px">{e["red4"]} 次</td>'
            f'<td style="padding:6px 8px;text-align:center;font-weight:700;color:#ef4444;font-size:12px">{e["max"]} 球</td>'
        )
        rows.append(_row(i, cells))

    pred_note = (
        f'；红字为第 {html.escape(target_period)} 期（未开奖）预测号码'
        if pred_valid else "；当前预测目标期已开奖，暂无下期预测号码"
    )
    note = (
        f'<div style="font-size:12px;color:#64748b;margin-bottom:6px">'
        f'两两组合不同「模型+策略」，同一期命中红球去重后 ≥{min_red_hits} 球计 1 次；'
        f'按 ≥{min_red_hits} 红球次数、最高命中排序；'
        f'共统计 {stat_periods} 期，展示前 {len(arr)} 名{pred_note}</div>'
    )
    return note + _render_table(
        ["#", "最佳组合（模型+策略）与下期预测", "≥4红球次数", "最高命中"], rows
    )


def _build_recommendations_html(hist, pred, latest_period="", limit=8, top_by_model=None,
                                data_stale=False):
    """本期预测推荐 — 取历史准确率 Top N 的「模型+策略」，附上其对当前期号的预测。"""
    stats, _ = _collect_strategy_stats(hist, top_by_model)
    if not stats:
        return '<p style="color:#94a3b8;font-size:13px;padding:12px">(暂无命中记录)</p>'
    if not pred or not pred.get("models"):
        return '<p style="color:#94a3b8;font-size:13px;padding:12px">(暂无预测数据)</p>'

    target = pred.get("target_period", "")
    try:
        stale = bool(target and latest_period) and int(target) <= int(latest_period)
    except (TypeError, ValueError):
        stale = False
    if stale or data_stale:
        return (
            f'<p style="color:#92400e;font-size:13px;padding:12px;background:#fef3c7;'
            f'border-radius:8px">⚠️ 当前预测目标第{target}期已开奖或开奖数据尚未更新，'
            f'暂无有效本期预测。</p>'
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


def _build_grouped_stats_html(hist, limit=8, top_by_model=None):
    """模型分组统计 HTML — 按模型聚合历史命中（仅统计各模型前 3 策略，期数按期去重）。

    limit 默认 8（邮件只展示前 8 名）；传 None 或 0 显示全部模型。"""
    records = hist.get("predictions_history", []) if hist else []
    if not records:
        return '<p style="color:#94a3b8;font-size:13px;padding:12px">(暂无命中记录)</p>'

    stats = {}
    for rec in records:
        period = (rec.get("actual_result") or {}).get("period")
        for m in rec.get("models", []):
            model_id = m.get("model_id") or m.get("model_name", "")
            allowed = (top_by_model or {}).get(model_id)
            for pred in (m.get("predictions") or []):
                hr = pred.get("hit_result")
                if not hr:
                    continue
                if allowed is not None and pred.get("strategy", "—") not in allowed:
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

    # 开奖数据是否已过期：下期预告的开奖时间已过但仍无最新结果
    # （爬虫滞后时，预测仍是上一期的，不能当作“本期预测”推送）
    data_stale = next_draw_passed(nd, _beijing_now())
    warnings = list(warnings)
    if data_stale:
        warnings.append(
            f"开奖数据未更新：下期预告第{next_period}期（{nd.get('next_date', '')}）"
            f"已过开奖时间，请等待下一次数据更新"
        )
    pred_target = pred.get("target_period", "")
    if not data_stale and pred_target and next_period and pred_target != next_period:
        warnings.append(
            f"当前预测目标为第{pred_target}期，与下期预告第{next_period}期不一致"
        )

    # 邮件类型（决定 subtitle 和 footer）
    is_push = commit_info is not None
    subtitle = "项目更新通知" if is_push else "定时汇总"

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

    # 每个模型按历史准确率只保留前 3 种策略（排行、分组统计、推荐均按此过滤）
    top_by_model = _top_strategies_by_model(hist)

    # 排行拆分为最新一期 / 历史累计两部分，便于按新顺序排版
    latest_rank_html, history_rank_html = _build_ranking_parts(
        hist, limit=8, top_by_model=top_by_model
    )

    # 单球命中（紧随最新一期）
    single_ball_html = _build_single_ball_hits_html(hist, latest, top_by_model=top_by_model)

    # 最佳组合（历史两两组合统计 + 下期预测号码）
    best_combo_html = _build_best_combinations_html(
        hist, pred, latest_period, top_by_model=top_by_model, limit=10,
        data_stale=data_stale,
    )

    # 模型分组统计（全部历史）— 只展示前 8 名
    grouped_html = (
        f'{_SECTION.format("📦 模型分组统计 Top 8（全部历史）")}'
        f'{_build_grouped_stats_html(hist, limit=8, top_by_model=top_by_model)}'
    )

    # Footer
    footer_text = (
        '本邮件由 GitHub Actions 自动推送'
        if is_push else
        '本邮件由自动系统生成 · 彩票预测仅供娱乐参考，不构成投资建议'
    )

    # 邮件板块顺序：
    # 最新一期 → 单球命中 → 本期命中 Top 8 → 历史排行 Top 8
    # → 模型分组统计 Top 8 → 本期预测推荐 Top 10 → 最佳组合 Top 10 → 模型推荐
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
        {_SECTION.format("🏆 最新一期")}
        {_build_latest_draw_html(latest, nd, data_stale=data_stale)}
        {_SECTION.format("🔍 单球命中")}
        {single_ball_html}
        {_SECTION.format("🎯 本期命中 Top 8")}
        {latest_rank_html}
        {_SECTION.format("📊 历史排行 Top 8（按准确率）")}
        {history_rank_html}
        {grouped_html}
        {_SECTION.format("🎯 本期预测推荐 Top 10")}
        {_build_recommendations_html(hist, pred, latest_period, limit=10, top_by_model=top_by_model, data_stale=data_stale)}
        {_SECTION.format("🏅 最佳组合 Top 10（单期 ≥4 红球 · 含下期预测）")}
        {best_combo_html}
        {_SECTION.format("🔮 模型推荐（前 3 策略 · 30 组）")}
        {_build_predictions_html(pred, latest_period, next_period, top_by_model=top_by_model, data_stale=data_stale)}
      </div>
      <div style="background:#f8fafc;padding:16px 24px;text-align:center;border-top:1px solid #e2e8f0;border-radius:0 0 12px 12px">
        <p style="font-size:12px;color:#94a3b8;margin:0">
          {footer_text}<br>
          <a href="https://github.com/zhens/double-color-ball" style="color:#3b82f6;text-decoration:none">double-color-ball</a>
        </p>
      </div>
    </div>'''
    return html