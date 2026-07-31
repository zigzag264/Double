# -*- coding: utf-8 -*-
"""
每日邮件内容组装模块

纯函数，无网络 IO：
  1. load_data()        — 读取 3 个 JSON 数据文件
  2. validate_data()    — 校验数据完整性，返回 (errors, warnings)
  3. build_email_content() — 渲染纯文本邮件正文
"""

import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE           = os.path.join(BASE_DIR, "data", "lottery_history.json")
PREDICTIONS_FILE       = os.path.join(BASE_DIR, "data", "ai_predictions.json")
HIT_HISTORY_FILE       = os.path.join(BASE_DIR, "data", "predictions_history.json")
PAILIE3_HISTORY_FILE   = os.path.join(BASE_DIR, "data", "pailie3_history.json")
PAILIE3_PREDICTIONS    = os.path.join(BASE_DIR, "data", "pailie3_predictions.json")
PAILIE3_HIT_HISTORY    = os.path.join(BASE_DIR, "data", "pailie3_predictions_history.json")

_SEPARATOR = "━" * 34


def _load(path):
    """加载单个 JSON 文件"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_data():
    """
    加载全部 3 个数据源，各自独立异常隔离。

    某个文件损坏只影响对应字段，不影响其他两个数据源。
    """
    result = {
        "lottery_history": None,
        "ai_predictions": None,
        "hit_history": None,
        "pailie3_history": None,
        "pailie3_predictions": None,
        "pailie3_hit_history": None,
    }

    try:
        result["lottery_history"] = _load(HISTORY_FILE)
        print(f"  ✓ 双色球历史加载成功 ({len(result['lottery_history'].get('data', []))} 期)")
    except Exception as e:
        print(f"  ✗ 双色球历史加载失败: {e}")

    try:
        result["ai_predictions"] = _load(PREDICTIONS_FILE)
        print(f"  ✓ 双色球AI预测加载成功 ({len(result['ai_predictions'].get('models', []))} 个模型)")
    except Exception as e:
        print(f"  ✗ 双色球AI预测加载失败: {e}")

    try:
        result["hit_history"] = _load(HIT_HISTORY_FILE)
        recs = result["hit_history"].get("predictions_history", []) if result["hit_history"] else []
        print(f"  ✓ 双色球命中历史加载成功 ({len(recs)} 期记录)")
    except Exception as e:
        print(f"  ✗ 双色球命中历史加载失败: {e}")

    try:
        result["pailie3_history"] = _load(PAILIE3_HISTORY_FILE)
        print(f"  ✓ 排列三历史加载成功 ({len(result['pailie3_history'].get('data', []))} 期)")
    except Exception as e:
        print(f"  ✗ 排列三历史加载失败: {e}")

    try:
        result["pailie3_predictions"] = _load(PAILIE3_PREDICTIONS)
        print(f"  ✓ 排列三AI预测加载成功 ({len(result['pailie3_predictions'].get('models', []))} 个模型)")
    except Exception as e:
        print(f"  ✗ 排列三AI预测加载失败: {e}")

    try:
        result["pailie3_hit_history"] = _load(PAILIE3_HIT_HISTORY)
        recs = result["pailie3_hit_history"].get("predictions_history", []) if result["pailie3_hit_history"] else []
        print(f"  ✓ 排列三命中历史加载成功 ({len(recs)} 期记录)")
    except Exception as e:
        print(f"  ✗ 排列三命中历史加载失败: {e}")

    return result


def validate_data(data):
    """
    校验数据完整性。

    Returns:
        (errors, warnings): errors 非空则不发送邮件，warnings 仅提示
    """
    errors = []
    warnings = []

    # 开奖历史 — 必须存在且不为空
    lh = data.get("lottery_history")
    if lh is None:
        errors.append("开奖历史文件加载失败")
    elif not lh.get("data"):
        errors.append("开奖历史数据为空")

    # AI 预测 — 允许缺失（仅 warning）
    pred = data.get("ai_predictions")
    if pred is None:
        warnings.append("AI 预测文件加载失败，预测栏将显示为空")
    elif not pred.get("models"):
        warnings.append("暂无可用 AI 预测数据（可能尚未到预测日）")

    # 命中历史 — 允许缺失（仅 warning）
    hist = data.get("hit_history")
    if hist is None:
        warnings.append("双色球命中历史文件加载失败，命中栏将显示为空")
    elif not hist.get("predictions_history"):
        warnings.append("暂无双色球命中历史记录")

    # 排列三历史 — 允许缺失（仅 warning）
    p3hist = data.get("pailie3_history")
    if p3hist is None:
        warnings.append("排列三历史文件加载失败，排列三栏将显示为空")
    elif not p3hist.get("data"):
        warnings.append("排列三历史数据为空")

    # 排列三 AI 预测 — 允许缺失（仅 warning）
    p3pred = data.get("pailie3_predictions")
    if p3pred is None:
        warnings.append("排列三AI预测文件加载失败，排列三预测栏将显示为空")
    elif not p3pred.get("models"):
        warnings.append("暂无排列三AI预测数据（可能尚未到预测日）")

    # 排列三命中历史 — 允许缺失（仅 warning）
    p3hit = data.get("pailie3_hit_history")
    if p3hit is None:
        warnings.append("排列三命中历史文件加载失败，命中栏将显示为空")
    elif not p3hit.get("predictions_history"):
        warnings.append("暂无排列三命中历史记录")

    return errors, warnings


def build_email_content(data, warnings, generated_at):
    """
    渲染纯文本邮件正文。

    Args:
        data: load_data() 返回的数据 dict
        warnings: validate_data() 返回的警告列表
        generated_at: 生成时间字符串 (UTC)

    Returns:
        纯文本邮件正文
    """
    lh = data.get("lottery_history") or {}
    pred = data.get("ai_predictions") or {}
    hist = data.get("hit_history") or {}

    lines = []
    sep = _SEPARATOR

    # ===== 头部 =====
    lines.append(sep)
    lines.append("  双色球 AI 预测 · 每日汇总")
    lines.append(f"  生成时间: {generated_at}")
    lines.append(sep)
    lines.append("")

    # ===== 【一、最新开奖】 =====
    lines.append("【一、最新开奖】")
    if lh and lh.get("data"):
        latest = lh["data"][0]
        lines.append(f"  期号  : {latest['period']}")
        lines.append(f"  日期  : {latest.get('date', '—')}")
        lines.append(f"  红球  : {' '.join(latest['red_balls'])}")
        lines.append(f"  蓝球  : {latest['blue_ball']}")
    else:
        lines.append("  (暂无开奖数据)")
    lines.append("")

    # ===== 【二、下期预告】 =====
    lines.append("【二、下期预告】")
    nxt = lh.get("next_draw", {}) if lh else {}
    if nxt:
        next_period = nxt.get("next_period", "—")
        next_display = nxt.get("next_date_display", "")
        weekday = nxt.get("weekday", "")
        draw_time = nxt.get("draw_time", "21:15")
        lines.append(f"  期号  : {next_period}")
        lines.append(f"  开奖  : {next_display} {weekday} {draw_time}")
    else:
        lines.append("  (暂无下期信息)")
    lines.append("")

    # ===== 【三、AI 模型预测】 =====
    lines.append("【三、AI 模型预测】")
    if pred.get("models"):
        lines.append(f"  目标期 : {pred.get('target_period', '—')}  "
                      f"预测日期: {pred.get('prediction_date', '—')}")
        for m in pred["models"]:
            lines.append("")
            lines.append(f"  ── {m['model_name']} ──")
            for g in m.get("predictions", []):
                rb = " ".join(g.get("red_balls", []))
                line = f"    [{g['group_id']}] {g.get('strategy', '')}   "
                line += f"红:{rb}  蓝:{g.get('blue_ball', '')}"
                lines.append(line)
                desc = g.get("description")
                if desc:
                    lines.append(f"        {desc}")
    else:
        lines.append("  (本期暂无 AI 预测，请在预测日后查看)")
    lines.append("")

    # ===== 【四、近期命中情况 (最近 3 期已开奖)】 =====
    lines.append("【四、近期命中情况 (最近 3 期已开奖)】")
    recs = hist.get("predictions_history", [])[:3]
    if recs:
        for rec in recs:
            ar = rec.get("actual_result", {})
            target = rec.get("target_period", "?")
            date = ar.get("date", "?")
            lines.append(f"  期号 {target} ({date}):")
            reds = " ".join(ar.get("red_balls", []))
            blue = ar.get("blue_ball", "")
            lines.append(f"    开奖: {reds} + {blue}")
            for m in rec.get("models", []):
                best = m.get("best_group", 0)
                bhc = m.get("best_hit_count", 0)
                bp = next((p for p in m["predictions"]
                           if p.get("group_id") == best), None)
                hr = bp.get("hit_result", {}) if bp else {}
                blue_txt = "是" if hr.get("blue_hit") else "否"
                rhc = hr.get("red_hit_count", 0)
                lines.append(
                    f"    {m.get('model_name', '?'):<12s} 最佳组[{best}] "
                    f"命中 红{rhc} 蓝{blue_txt} = {bhc}球"
                )
            lines.append("")
    else:
        lines.append("  (暂无命中记录)")
        lines.append("")

    # ===== 【系统提示】 =====
    if warnings:
        lines.append("【系统提示】")
        for w in warnings:
            lines.append(f"  ⚠️ {w}")
        lines.append("")

    # ===== 排列三 =====
    p3hist = data.get("pailie3_history") or {}
    p3pred = data.get("pailie3_predictions") or {}
    p3hit  = data.get("pailie3_hit_history") or {}

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("  排列三")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # 【排列三 最新开奖】
    lines.append("【最新开奖】")
    if p3hist and p3hist.get("data"):
        latest = p3hist["data"][0]
        lines.append(f"  期号  : {latest['period']}")
        lines.append(f"  日期  : {latest.get('date', '—')}")
        lines.append(f"  开奖: {latest.get('result', '—')}")
    else:
        lines.append("  (暂无开奖数据)")
    lines.append("")

    # 【排列三 下期预告】
    lines.append("【下期预告】")
    nxt = p3hist.get("next_draw", {}) if p3hist else {}
    if nxt:
        next_period = nxt.get("next_period", "—")
        next_display = nxt.get("next_date_display", "")
        weekday = nxt.get("weekday", "")
        draw_time = nxt.get("draw_time", "21:30")
        lines.append(f"  期号  : {next_period}")
        lines.append(f"  开奖  : {next_display} {weekday} {draw_time}")
    else:
        lines.append("  (暂无下期信息)")
    lines.append("")

    # 【排列三 AI 模型预测】
    lines.append("【AI 模型预测】")
    if p3pred.get("models"):
        lines.append(f"  目标期 : {p3pred.get('target_period', '—')}  "
                      f"预测日期: {p3pred.get('prediction_date', '—')}")
        for m in p3pred["models"]:
            lines.append("")
            lines.append(f"  ── {m['model_name']} ──")
            for g in m.get("predictions", []):
                line = f"    [{g['group_id']}] {g.get('strategy', '')}   "
                line += f"号码: {g.get('result', '—')}"
                lines.append(line)
                desc = g.get("description")
                if desc:
                    lines.append(f"        {desc}")
    else:
        lines.append("  (本期暂无 AI 预测，请在预测日后查看)")
    lines.append("")

    # 【排列三 近期命中情况】
    lines.append("【近期命中情况 (最近 3 期已开奖)】")
    recs = p3hit.get("predictions_history", [])[:3]
    if recs:
        for rec in recs:
            ar = rec.get("actual_result", {})
            target = rec.get("target_period", "?")
            date = ar.get("date", "?")
            lines.append(f"  期号 {target} ({date}):")
            lines.append(f"    开奖: {ar.get('result', '—')}")
            for m in rec.get("models", []):
                best = m.get("best_group", 0)
                bhc = m.get("best_hit_count", 0)
                bp = next((p for p in m["predictions"]
                           if p.get("group_id") == best), None)
                hr = bp.get("hit_result", {}) if bp else {}
                exact = "是" if hr.get("exact_match") else "否"
                phits = hr.get("position_hits", 0)
                lines.append(
                    f"    {m.get('model_name', '?'):<20s} 最佳组[{best}] "
                    f"直选命中: {exact}  位置命中: {phits}"
                )
            lines.append("")
    else:
        lines.append("  (暂无命中记录)")
        lines.append("")

    # ===== 免责声明 =====
    lines.append(sep)
    lines.append("  本邮件由自动系统生成，彩票预测仅供娱乐参考，不构成投资建议。")
    lines.append("  双色球/排列三为随机事件，任何预测均无法保证命中。")
    lines.append(sep)

    return "\n".join(lines)
