# -*- coding: utf-8 -*-
"""
双色球 统计/概率/机器学习 数学模型预测模块

基于历史开奖数据，用纯 Python 标准库（random/math/statistics/collections/itertools）
实现 10 种数学模型，每种输出 4 组参数变体预测，输出结构与预测模型完全一致，
可被 generate_ai_prediction.py 集成并统一进入归档/排行/邮件/前端。

特性:
  - 确定性：除蒙特卡洛模拟（固定种子）外全部纯计算，结果可复现
  - 零依赖：不消耗 API / token，无需 pip 安装新包
  - 独立 CLI：`python3 stats_models.py --output stats_test.json` 可单独验证

模型清单（10 种 × 4 变体）:
  1. markov-chain            马尔可夫链       （转移矩阵 + 平稳分布）
  2. bayesian                贝叶斯推断       （Beta 收缩估计）
  3. normal-distribution     正态分布(Z-score)（标准化偏离 + 和值正态约束）
  4. poisson                 泊松分布         （出现次数 ~ Poisson，P(出现) 评分）
  5. monte-carlo             蒙特卡洛模拟     （加权抽样 + 约束筛选，固定种子）
  6. frequency-hot           频率热号         （多窗口加权频率）
  7. cold-miss               遗漏回补         （当前遗漏 vs 平均遗漏）
  8. ewma                    指数平滑(EWMA)   （0/1 序列指数加权）
  9. apriori                 关联规则         （共现置信度 / 提升度）
  10. ensemble               集成投票         （前 9 模型评分融合）
"""

import itertools
import json
import math
import os
import random
import statistics

RED_POOL = [f"{i:02d}" for i in range(1, 34)]
BLUE_POOL = [f"{i:02d}" for i in range(1, 17)]


# ==================== 共享工具 ====================

def _chrono(history):
    """转为时间正序（旧→新）。lottery_history.data 为降序（最新在前）。"""
    return list(reversed(list(history)))


def _recent(chrono, n):
    """最近 n 期，最新在前。"""
    return list(reversed(chrono))[:n]


def _red_counts(draws):
    c = {r: 0 for r in RED_POOL}
    for d in draws:
        for r in d.get("red_balls", []):
            if r in c:
                c[r] += 1
    return c


def _blue_counts(draws):
    c = {b: 0 for b in BLUE_POOL}
    for d in draws:
        b = d.get("blue_ball")
        if b in c:
            c[b] += 1
    return c


def _zones(n):
    """区间: 1-11 → 0, 12-22 → 1, 23-33 → 2"""
    if n <= 11:
        return 0
    if n <= 22:
        return 1
    return 2


def _sort_reds(reds):
    "去重、排序、取前 6，返回两位字符串列表"
    out = sorted({r for r in reds if r in RED_POOL}, key=int)
    return out[:6]


def _normalize(d):
    """min-max 归一化到 [0,1]"""
    vals = list(d.values())
    mn, mx = min(vals), max(vals)
    if mx - mn < 1e-12:
        return {k: 0.5 for k in d}
    return {k: (v - mn) / (mx - mn) for k, v in d.items()}


def _pick_reds(score, avoid=set()):
    """按分数降序取 6 个红球"""
    ranked = sorted(score, key=lambda n: score[n], reverse=True)
    picked = []
    for n in ranked:
        if n in avoid:
            continue
        picked.append(n)
        if len(picked) == 6:
            break
    return _sort_reds(picked)


def _pick_blue(score, avoid=""):
    """按分数取蓝球"""
    ranked = sorted(score, key=lambda n: score[n], reverse=True)
    for n in ranked:
        if n != avoid:
            return n
    return ranked[0] if ranked else "01"


def _zone_balanced_reds(score):
    """每个区间取分数最高前 2，共 6 个"""
    picked = []
    for zone in (0, 1, 2):
        cand = [r for r in RED_POOL if _zones(int(r)) == zone]
        top = sorted(cand, key=lambda n: score.get(n, 0), reverse=True)[:2]
        picked.extend(top)
    return _sort_reds(picked)


def _top_score_subset(score, pool_size=12, pick=6, lo=95, hi=115):
    """Top-pool_size 中枚举 C(pool,6) 组合，选和值在 [lo,hi] 且总分数最高者"""
    tops = sorted(score, key=lambda n: score[n], reverse=True)[:pool_size]
    best, best_v = [], -1.0
    for comb in itertools.combinations(tops, pick):
        s = sum(int(n) for n in comb)
        if lo <= s <= hi:
            v = sum(score[n] for n in comb)
            if v > best_v:
                best_v, best = v, comb
    return _sort_reds(best) if best else _sort_reds(tops[:pick])


def _make_group(gid, strategy, reds, blue, extra):
    """构建单组预测 dict，自动生成描述（总和/奇偶/蓝球）"""
    reds = _sort_reds(reds)
    total = sum(int(r) for r in reds) if reds else 0
    odd = sum(1 for r in reds if int(r) % 2 == 1)
    return {
        "group_id": gid,
        "strategy": strategy,
        "red_balls": reds,
        "blue_ball": blue,
        "description": f"总和{total}；奇偶{odd}:{6 - odd}；蓝{blue}；{extra}",
    }


def _describe(reds, blue, extra):
    reds = _sort_reds(reds)
    total = sum(int(r) for r in reds) if reds else 0
    odd = sum(1 for r in reds if int(r) % 2 == 1)
    return f"总和{total}；奇偶{odd}:{6 - odd}；蓝{blue}；{extra}"


def _regroup(group, reds, blue):
    """在保持策略与算法文案不变的前提下，按新号码重建该组（重算总和/奇偶）"""
    desc = group.get("description", "")
    extra = desc.split("；", 3)[-1] if desc.count("；") >= 3 else ""
    return {
        "group_id": group.get("group_id"),
        "strategy": group.get("strategy"),
        "red_balls": _sort_reds(reds),
        "blue_ball": blue,
        "description": _describe(reds, blue, extra),
    }


def _dedup_groups(groups, red_score, blue_score):
    """保证一个模型内 4 组 (红球,蓝球) 组合互不相同。
    某变体与既有组相同时，用评分表替换组内最低分号码 / 换蓝球，重建该组。"""
    seen = set()
    out = []
    for g in groups:
        key = (tuple(g["red_balls"]), g["blue_ball"])
        reds, blue = list(g["red_balls"]), g["blue_ball"]
        guard = 0
        while key in seen and guard < 64:
            guard += 1
            used = set(reds)
            ranked_pool = sorted(RED_POOL, key=lambda r: red_score.get(r, 0), reverse=True)
            repl = next((r for r in ranked_pool if r not in used), None)
            if repl is not None:
                low = min(reds, key=lambda r: red_score.get(r, 0))
                reds = [repl if r == low else r for r in reds]
                reds = _sort_reds(reds)
            key = (tuple(reds), blue)
            if key in seen:
                ranked_blue = sorted(BLUE_POOL, key=lambda b: blue_score.get(b, 0), reverse=True)
                nxt = next((b for b in ranked_blue if b != blue), None)
                if nxt is not None:
                    blue = nxt
                key = (tuple(reds), blue)
        if key not in seen:
            out.append(_regroup(g, reds, blue))
            seen.add(key)

    # 极端情况下补足到 4 组（上一个 template 变体）
    while len(out) < 4 and len(out) > 0:
        tpl = out[-1]
        reds = list(tpl["red_balls"])
        used = set(reds)
        ranked_pool = sorted(RED_POOL, key=lambda r: red_score.get(r, 0), reverse=True)
        repl = next((r for r in ranked_pool if r not in used), None)
        if repl is not None:
            low = min(reds, key=lambda r: red_score.get(r, 0))
            reds = [repl if r == low else r for r in reds]
            reds = _sort_reds(reds)
        blue = tpl["blue_ball"]
        key = (tuple(reds), blue)
        if key in seen:
            ranked_blue = sorted(BLUE_POOL, key=lambda b: blue_score.get(b, 0), reverse=True)
            blue = next((b for b in ranked_blue if b != blue), "01")
            key = (tuple(reds), blue)
        if key not in seen:
            widened = {"group_id": len(out) + 1, "strategy": tpl["strategy"], "red_balls": reds,
                       "blue_ball": blue, "description": _describe(reds, blue, "自动补足变体")}
            out.append(widened)
            seen.add(key)
        else:
            break

    # 重新编号 1..4
    for i, g in enumerate(out, start=1):
        g["group_id"] = i
    return out


# ==================== 模型 1: 马尔可夫链 ====================

def _model_markov(chrono, history):
    n = len(chrono)
    trans = {x: {y: 0.0 for y in RED_POOL} for x in RED_POOL}
    appear = {x: 0.0 for x in RED_POOL}
    btrans = {x: {y: 0.0 for y in BLUE_POOL} for x in BLUE_POOL}
    bappear = {x: 0.0 for x in BLUE_POOL}
    for i in range(n - 1):
        cur, nxt = chrono[i], chrono[i + 1]
        for x in cur.get("red_balls", []):
            if x not in RED_POOL:
                continue
            appear[x] += 1.0
            for y in nxt.get("red_balls", []):
                if y in RED_POOL:
                    trans[x][y] += 1.0
        b0, b1 = cur.get("blue_ball"), nxt.get("blue_ball")
        if b0 in BLUE_POOL and b1 in BLUE_POOL:
            bappear[b0] += 1.0
            btrans[b0][b1] += 1.0

    def prob_rows():
        rows = {}
        for x in RED_POOL:
            if appear[x] > 0:
                rows[x] = {y: trans[x][y] / appear[x] for y in RED_POOL}
            else:
                rows[x] = {y: 1.0 / len(RED_POOL) for y in RED_POOL}
        return rows

    def stationary():
        rows = prob_rows()
        pi = {s: 1.0 / len(RED_POOL) for s in RED_POOL}
        for _ in range(100):
            nxt = {s: 0.0 for s in RED_POOL}
            for x in RED_POOL:
                for y in RED_POOL:
                    nxt[y] += pi[x] * rows[x][y]
            pi = nxt
        return pi

    def trans_from_seeds(seeds, weights):
        score = {y: 0.0 for y in RED_POOL}
        for x, w in zip(seeds, weights):
            if x not in RED_POOL or appear[x] <= 0:
                continue
            for y in RED_POOL:
                score[y] += w * trans[x][y] / appear[x]
        return score

    def blue_seed(seeds, weights):
        score = {b: 0.0 for b in BLUE_POOL}
        for x, w in zip(seeds, weights):
            if x not in BLUE_POOL or bappear[x] <= 0:
                continue
            for b in BLUE_POOL:
                score[b] += w * btrans[x][b] / bappear[x]
        return score

    last = chrono[-1]
    lr = last.get("red_balls", [])
    lb = last.get("blue_ball", "")
    prev = chrono[-2] if n >= 2 else None

    # G1 一阶
    g1r = trans_from_seeds(lr, [1.0] * len(lr))
    g1b = blue_seed([lb] if lb else [], [1.0]) if lb else {b: 1.0 for b in BLUE_POOL}
    g1 = _make_group(1, "一阶马尔可夫", _pick_reds(g1r), _pick_blue(g1b),
                     "相邻期红→红转移矩阵；从上期6红出发转移概率加和取Top6；蓝球一阶转移")

    # G2 二阶
    seeds2, w2 = [], []
    if prev:
        seeds2 += prev.get("red_balls", [])
        w2 += [0.6] * len(prev.get("red_balls", []))
    seeds2 += lr
    w2 += [1.0] * len(lr)
    g2r = trans_from_seeds(seeds2, w2)
    bseeds2, bw2 = [], []
    if prev:
        bseeds2.append(prev.get("blue_ball") or "")
        bw2.append(0.6)
    if lb:
        bseeds2.append(lb)
        bw2.append(1.0)
    g2b = blue_seed(bseeds2, bw2) if bseeds2 else {b: 1.0 for b in BLUE_POOL}
    g2 = _make_group(2, "二阶马尔可夫", _pick_reds(g2r), _pick_blue(g2b),
                     "上两期种子按权重0.6:1.0的转移；蓝球二阶")

    # G3 平稳分布 × 一阶
    st = stationary()
    g3r = {y: 0.5 * _normalize(st)[y] + 0.5 * _normalize(g1r)[y] for y in RED_POOL}
    g3 = _make_group(3, "平稳分布融合", _pick_reds(g3r), _pick_blue(g1b),
                     "马尔可夫平稳分布与一阶转移各50%融合")

    # G4 最近 7 期滑动（5→7：回测整体命中略升、蓝球命中率持平）
    start = max(0, n - 7)
    seeds4, w4 = [], []
    bseeds4, bw4 = [], []
    for k, d in enumerate(chrono[start:n]):
        wt = 0.2 + 0.8 * k / max(1, len(chrono[start:n]) - 1)
        for x in d.get("red_balls", []):
            if x in RED_POOL:
                seeds4.append(x)
                w4.append(wt)
        b4 = d.get("blue_ball")
        if b4 in BLUE_POOL:
            bseeds4.append(b4)
            bw4.append(wt)
    g4r = trans_from_seeds(seeds4, w4)
    g4b = blue_seed(bseeds4, bw4) if bseeds4 else {b: 1.0 for b in BLUE_POOL}
    g4 = _make_group(4, "滑动多期马尔可夫", _pick_reds(g4r), _pick_blue(g4b),
                     "最近7期种子衰减加权(0.2→1.0)的转移概率")

    return [g1, g2, g3, g4], g1r, g1b


# ==================== 模型 2: 贝叶斯推断 ====================

def _shrink(chrono, window, w, pool):
    """收缩估计: score = (w*先验 + n*似然) / (w + n)，先验=全史频率"""
    slots = 6 if len(pool) == 33 else 1  # 红球每期6槽，蓝球每期1槽
    full = _red_counts(chrono) if len(pool) == 33 else _blue_counts(chrono)
    rec = _red_counts(_recent(chrono, window)) if len(pool) == 33 else _blue_counts(_recent(chrono, window))
    ntotal = len(chrono) * slots
    rec_draws = len(_recent(chrono, window))
    nrec = rec_draws * slots
    prior = {x: full[x] / max(1, ntotal) for x in pool}
    recp = {x: rec[x] / max(1, nrec) for x in pool}
    return {x: (w * prior[x] + nrec * recp[x]) / (w + nrec) for x in pool}


def _model_bayes(chrono, history):
    def blue_shrink(window, w):
        full = _blue_counts(chrono)
        rec = _blue_counts(_recent(chrono, window))
        ntotal = len(chrono)
        nrec = min(window, len(chrono))
        prior = {b: full[b] / max(1, ntotal) for b in BLUE_POOL}
        recp = {b: rec[b] / max(1, nrec) for b in BLUE_POOL}
        return {b: (w * prior[b] + nrec * recp[b]) / (w + nrec) for b in BLUE_POOL}

    # G1 强先验
    r1 = _shrink(chrono, 30, 12, RED_POOL)
    g1 = _make_group(1, "贝叶斯·强先验", _pick_reds(r1), _pick_blue(blue_shrink(30, 12)),
                     "Beta收缩，先验强度w=12（保守，向全史频率回归）")
    # G2 弱先验
    r2 = _shrink(chrono, 30, 2, RED_POOL)
    g2 = _make_group(2, "贝叶斯·弱先验", _pick_reds(r2), _pick_blue(blue_shrink(30, 2)),
                     "Beta收缩，先验强度w=2（跟随近期）")
    # G3 三窗加权似然（5:3:2→4:3:3：提升30期占比，回测全sw稳定改善 total/all）
    p5 = _normalize(_shrink(chrono, 5, 4, RED_POOL))
    p10 = _normalize(_shrink(chrono, 10, 4, RED_POOL))
    p30 = _normalize(_shrink(chrono, 30, 4, RED_POOL))
    r3 = {x: 0.4 * p5[x] + 0.3 * p10[x] + 0.3 * p30[x] for x in RED_POOL}
    b5 = _normalize(blue_shrink(5, 4))
    b10 = _normalize(blue_shrink(10, 4))
    b30 = _normalize(blue_shrink(30, 4))
    b3 = {b: 0.4 * b5[b] + 0.3 * b10[b] + 0.3 * b30[b] for b in BLUE_POOL}
    g3 = _make_group(3, "贝叶斯·三窗后验", _pick_reds(r3), _pick_blue(b3),
                     "5/10/30期似然加权(4:3:3)，先验强度w=4")
    # G4 全历史后验
    r4 = _shrink(chrono, len(chrono), 6, RED_POOL)
    g4 = _make_group(4, "贝叶斯·全史后验", _pick_reds(r4), _pick_blue(blue_shrink(len(chrono), 6)),
                     "以全部历史频率为似然的后验估计")

    return [g1, g2, g3, g4], r1, blue_shrink(30, 12)


# ==================== 模型 3: 正态分布 Z-score ====================

def _zscore(chrono, window, pool):
    """近期出现率 vs 全史出现率的标准化 z-score"""
    N = len(chrono)
    rec_draws = len(_recent(chrono, window))
    full = _red_counts(chrono) if len(pool) == 33 else _blue_counts(chrono)
    rec = _red_counts(_recent(chrono, window)) if len(pool) == 33 else _blue_counts(_recent(chrono, window))
    # 红球每期 6 个槽位，蓝球每期 1 个槽位
    nfull = N * (6 if len(pool) == 33 else 1)
    nrec = rec_draws * (6 if len(pool) == 33 else 1)
    z = {}
    for x in pool:
        p = full[x] / max(1, nfull)
        pr = rec[x] / max(1, nrec)
        sd = math.sqrt(p * (1 - p) / max(1, nrec)) if 0 < p < 1 else 0.5 / max(1, nrec)
        z[x] = (pr - p) / sd if sd > 0 else 0.0
    return z


def _model_normal(chrono, history):
    zr = _zscore(chrono, 30, RED_POOL)
    zb = _zscore(chrono, 30, BLUE_POOL)

    g1 = _make_group(1, "Z高分热选", _pick_reds(zr), _pick_blue(zb),
                     "近30期出现率相对全史的标准化偏离最大Top6（统计显著的热号）")
    zlo = {r: -zr[r] for r in RED_POOL}
    bzlo = {b: -zb[b] for b in BLUE_POOL}
    g2 = _make_group(2, "Z低分回补", _pick_reds(zlo), _pick_blue(bzlo),
                     "均值回归：偏离期望出现率最负的6个号")
    g3 = _make_group(3, "和值约束Z选", _top_score_subset(zr, pool_size=12, lo=95, hi=115),
                     _pick_blue(zb),
                     "Top12候选内枚举组合，满足和值[95,115]且总z最大（正态和值约束）")
    g4 = _make_group(4, "三区间Z平衡", _zone_balanced_reds(zr), _pick_blue(zb),
                     "每个区间(1-11/12-22/23-33)取z前2，均衡覆盖")

    return [g1, g2, g3, g4], zr, zb


# ==================== 模型 4: 泊松分布 ====================

def _poisson_score(chrono, window):
    draws = _recent(chrono, min(window, len(chrono)))
    lam = _red_counts(draws)
    return {r: 1 - math.exp(-lam[r]) for r in RED_POOL}  # P(至少出现1次) ≈ 1 - e^{-λ}


def _poisson_blue(chrono, window):
    draws = _recent(chrono, min(window, len(chrono)))
    lam = _blue_counts(draws)
    return {b: 1 - math.exp(-lam[b]) for b in BLUE_POOL}


def _model_poisson(chrono, history):
    wins = [10, 20, 30, 50]
    labels = ["10期", "20期", "30期", "50期"]
    groups = []
    for i, (w, lab) in enumerate(zip(wins, labels), start=1):
        r = _poisson_score(chrono, w)
        b = _poisson_blue(chrono, w)
        groups.append(_make_group(i, f"泊松·{lab}", _pick_reds(r), _pick_blue(b),
                                  f"窗口{w}期计数 ~ Poisson(λ)，P(出现)≈1−e^{{−λ}} 取Top6"))
    return groups, _poisson_score(chrono, 30), _poisson_blue(chrono, 30)


# ==================== 模型 5: 蒙特卡洛模拟 ====================

def _montecarlo_model(chrono, history):
    full = _red_counts(chrono)
    red_w = [full[r] + 0.5 for r in RED_POOL]
    blue_w = [_blue_counts(chrono)[b] + 0.5 for b in BLUE_POOL]
    params = [
        (20260813, (80, 130), (2, 4), True,  "标准约束"),
        (42,       (70, 140), (1, 5), False, "宽松约束"),
        (777,      (80, 130), (2, 4), True,  "热号加强"),
        (1024,     (60, 150), (0, 6), False, "无约束"),
    ]
    groups = []
    canonical = None
    for i, (seed, (lo, hi), (olo, ohi), zone_req, tag) in enumerate(params, start=1):
        rng = random.Random(seed)
        red_count = {r: 0 for r in RED_POOL}
        blue_count = {b: 0 for b in BLUE_POOL}
        done, attempts = 0, 0
        while done < 10000 and attempts < 300000:
            attempts += 1
            reds = set()
            guard = 0
            while len(reds) < 6 and guard < 60:
                guard += 1
                reds = set(rng.choices(RED_POOL, weights=red_w, k=6))
            if len(reds) < 6:
                continue
            s = sum(int(r) for r in reds)
            if not (lo <= s <= hi):
                continue
            odds = sum(1 for r in reds if int(r) % 2 == 1)
            if not (olo <= odds <= ohi):
                continue
            if zone_req:
                zc = [0, 0, 0]
                for r in reds:
                    zc[_zones(int(r))] += 1
                if any(c == 0 for c in zc):
                    continue
            blue = rng.choices(BLUE_POOL, weights=blue_w, k=1)[0]
            for r in reds:
                red_count[r] += 1
            blue_count[blue] += 1
            done += 1

        if i == 1:
            canonical = (red_count, blue_count)
        groups.append(_make_group(i, f"蒙特卡洛·{tag}", _pick_reds(red_count), _pick_blue(blue_count),
                                  f"种子{seed}；10,000次加权抽样，和值[{lo},{hi}]、奇偶[{olo},{ohi}]、" +
                                  ("三区间全覆盖" if zone_req else "无区间约束") + "；按选中率取Top6"))

    g1r = {}
    g1b = {}
    if canonical:
        g1r, g1b = canonical
    return groups, g1r, g1b


# ==================== 模型 6: 频率热号 ====================

def _hot_score(chrono, wa, wb, wc, pool):
    n5 = min(5, len(chrono))
    n10 = min(10, len(chrono))
    n30 = min(30, len(chrono))
    if len(pool) == 33:
        f5 = _red_counts(_recent(chrono, 5))
        f10 = _red_counts(_recent(chrono, 10))
        f30 = _red_counts(_recent(chrono, 30))
    else:
        f5 = _blue_counts(_recent(chrono, 5))
        f10 = _blue_counts(_recent(chrono, 10))
        f30 = _blue_counts(_recent(chrono, 30))
    return {x: wa * f5[x] / n5 + wb * f10[x] / n10 + wc * f30[x] / n30 for x in pool}


def _model_freq(chrono, history):
    schemes = [
        (5, 3, 2, "5:3:2"), (3, 2, 1, "3:2:1"), (1, 1, 1, "1:1:1"), (2, 1, 0.5, "2:1:0.5"),
    ]
    groups = []
    canonical = None
    for i, (wa, wb, wc, lab) in enumerate(schemes, start=1):
        r = _hot_score(chrono, wa, wb, wc, RED_POOL)
        b = _hot_score(chrono, wa, wb, wc, BLUE_POOL)
        if i == 1:
            canonical = (r, b)
        reds = _zone_balanced_reds(r) if i <= 2 else _pick_reds(r)
        groups.append(_make_group(i, f"热号加权·{lab}", reds, _pick_blue(b),
                                  f"5期×{wa} + 10期×{wb} + 30期×{wc} 加权频率"))
    g1r, g1b = canonical if canonical else ({}, {})
    return groups, g1r, g1b


# ==================== 模型 7: 遗漏回补 ====================

def _gap_stats(chrono, extract):
    """当前遗漏 & 平均遗漏。extract(draw) -> [numbers]"""
    idx_of = {}
    n = len(chrono)
    for i, d in enumerate(chrono):
        for x in extract(d):
            idx_of[x] = i
    counts = {x: 0 for x in idx_of}
    for d in chrono:
        for x in extract(d):
            if x in counts:
                counts[x] += 1
    gaps, mean = {}, {}
    for x in idx_of:
        mean[x] = (n - 1) / counts[x] if counts[x] > 0 else n
        gaps[x] = (n - 1) - idx_of[x]
    return gaps, mean


def _model_cold(chrono, history):
    rg, rm = _gap_stats(chrono, lambda d: d.get("red_balls", []))
    bg, bm = _gap_stats(chrono, lambda d: [d.get("blue_ball")] if d.get("blue_ball") else [])
    n = len(chrono)

    # G1 纯遗漏
    r_g1 = {x: rg.get(x, 0) for x in RED_POOL}
    b_g1 = {x: bg.get(x, 0) for x in BLUE_POOL}
    g1 = _make_group(1, "强遗漏回补", _pick_reds(r_g1), _pick_blue(b_g1),
                     "当前遗漏最大Top6（冷号极端）")
    # G2 期望回补（遗漏 − 平均遗漏）
    r2 = {x: rg.get(x, 0) - rm.get(x, n) for x in RED_POOL}
    b2 = {x: bg.get(x, 0) - bm.get(x, n) for x in BLUE_POOL}
    g2 = _make_group(2, "期望回补", _pick_reds(r2), _pick_blue(b2),
                     "遗漏 − 平均遗漏 差值最大Top6")
    # G3 冷热折中（0.6:0.4→0.5:0.5：回测两时段稳定提升命中，蓝球命中率翻倍）
    hot_r = _hot_score(chrono, 5, 3, 2, RED_POOL)
    hot_b = _hot_score(chrono, 5, 3, 2, BLUE_POOL)
    r3n = _normalize(r2)
    hot_rn = _normalize(hot_r)
    r3 = {x: 0.5 * r3n[x] + 0.5 * hot_rn[x] for x in RED_POOL}
    b3 = {b: 0.5 * _normalize(b2)[b] + 0.5 * _normalize(hot_b)[b] for b in BLUE_POOL}
    g3 = _make_group(3, "冷热折中", _pick_reds(r3), _pick_blue(b3),
                     "50%期望回补 + 50%频率热号")
    # G4 和值约束 + 蓝球强遗漏（[90,120]→[95,125]：更贴合均值区间）
    g4 = _make_group(4, "遗漏+和值约束", _top_score_subset(r2, pool_size=12, lo=95, hi=125),
                     _pick_blue(bg),
                     "期望回补Top12内枚举和值[95,125]；蓝球取最强遗漏")

    return [g1, g2, g3, g4], r2, b2


# ==================== 模型 8: 指数平滑 EWMA ====================

def _ewma(chrono, alpha, pool):
    v = {x: 0.0 for x in pool}
    for d in chrono:
        present = set(d.get("red_balls", [])) if len(pool) == 33 else {d.get("blue_ball")}
        for x in pool:
            v[x] = v[x] + alpha * ((1.0 if x in present else 0.0) - v[x])
    return v


def _model_ewma(chrono, history):
    alphas = [(0.1, "慢"), (0.3, "中"), (0.5, "较快"), (0.7, "快")]
    groups = []
    canonical = None
    for i, (a, lab) in enumerate(alphas, start=1):
        r = _ewma(chrono, a, RED_POOL)
        b = _ewma(chrono, a, BLUE_POOL)
        if i == 1:
            canonical = (r, b)
        groups.append(_make_group(i, f"EWMA·α={a}", _pick_reds(r), _pick_blue(b),
                                  f"0/1序列指数平滑α={a}（{lab}）"))
    g1r, g1b = canonical if canonical else ({}, {})
    return groups, g1r, g1b


# ==================== 模型 9: 关联规则 ====================

def _apriori_red_score(chrono, seeds, window=None, metric="conf"):
    draws = _recent(chrono, window) if window else chrono
    cnt = {r: 0 for r in RED_POOL}
    co = {x: {y: 0 for y in RED_POOL} for x in RED_POOL}
    for d in draws:
        s = set(d.get("red_balls", []))
        for x in s:
            if x in RED_POOL:
                cnt[x] += 1
        for x in s:
            for y in s:
                if x != y:
                    co[x][y] += 1
    nd = len(draws)

    def conf(x, y):
        return co[x][y] / cnt[x] if cnt[x] else 0.0

    def lift(x, y):
        e = cnt[y] / nd if nd else 0.0
        c = conf(x, y)
        return c / e if e > 0 else c

    score = {y: 0.0 for y in RED_POOL}
    for y in RED_POOL:
        vals = [lift(x, y) if metric == "lift" else conf(x, y) for x in seeds if y != x]
        score[y] = statistics.mean(vals) if vals else 0.0
    return score


def _apriori_blue(chrono, reds_chosen, window=None):
    draws = _recent(chrono, window) if window else chrono
    chosen = set(reds_chosen)
    sc = {b: 0.0 for b in BLUE_POOL}
    for d in draws:
        if len(chosen & set(d.get("red_balls", []))) >= 2:
            b = d.get("blue_ball")
            if b in sc:
                sc[b] += 1
    return sc


def _model_apriori(chrono, history):
    last = chrono[-1]
    lr = last.get("red_balls", [])
    hot6 = _pick_reds(_hot_score(chrono, 5, 3, 2, RED_POOL))
    variants = [
        ("上期红球种子", lr, None, "conf"),
        ("热号种子", hot6, None, "conf"),
        ("热号种子·提升度", hot6, None, "lift"),
        ("近20期上期种子", lr, 20, "conf"),
    ]
    groups = []
    canonical = None
    for i, (lab, seeds, window, metric) in enumerate(variants, start=1):
        r = _apriori_red_score(chrono, seeds, window, metric)
        b = _apriori_blue(chrono, _pick_reds(r), window)
        if i == 1:
            canonical = (r, b)
        groups.append(_make_group(i, f"关联规则·{lab}", _pick_reds(r), _pick_blue(b),
                                  f"与种子号共现的{f'提升度' if metric == 'lift' else '置信度'}平均Top6" +
                                  (f"；近{window}期" if window else "")))
    g1r, g1b = canonical if canonical else ({}, {})
    return groups, g1r, g1b


# ==================== 模型 10: 集成投票 ====================

def _combine(vecs, mode):
    out = {}
    for x in vecs[0].keys():
        vals = [v[x] for v in vecs]
        if mode == "mean":
            out[x] = statistics.mean(vals)
        elif mode == "median":
            out[x] = statistics.median(vals)
        elif mode == "trim":
            out[x] = statistics.mean(sorted(vals)[1:-1]) if len(vals) > 2 else statistics.mean(vals)
        else:  # freq 融合
            out[x] = 0.7 * statistics.mean(vals) + 0.3 * vecs[-1][x]
    return out


def _model_ensemble(chrono, history, canonical):
    red_vecs = [_normalize(v[0]) for v in canonical.values()]
    blue_vecs = [_normalize(v[1]) for v in canonical.values()]
    f30r = _normalize(_red_counts(_recent(chrono, 30)))
    f30b = _normalize(_blue_counts(_recent(chrono, 30)))

    def combine_red(mode):
        return _combine(red_vecs + ([f30r] if mode == "freq" else []), "freq" if mode == "freq" else mode)

    def combine_blue(mode):
        return _combine(blue_vecs + ([f30b] if mode == "freq" else []), "freq" if mode == "freq" else mode)

    modes = ["mean", "median", "trim", "freq"]
    labels = ["均值投票", "中位数投票", "去极值均值", "集成+频率融合"]
    descs = [
        "9个统计模型归一化评分取均值，Top6",
        "9个统计模型评分取中位数（抗离群稳健）",
        "去最高/最低后取均值（稳健策略）",
        "70%集成均值 + 30%近30期频率",
    ]
    groups = []
    for i, (mode, label, desc) in enumerate(zip(modes, labels, descs), start=1):
        r = combine_red(mode)
        b = combine_blue(mode)
        groups.append(_make_group(i, label, _pick_reds(r), _pick_blue(b), desc))
    g1r = combine_red("mean")
    g1b = combine_blue("mean")
    return groups, g1r, g1b


# ==================== 生成入口 ====================

_STATS_MODELS = [
    ({"id": "markov-chain", "name": "马尔可夫链"}, _model_markov),
    ({"id": "bayesian", "name": "贝叶斯推断"}, _model_bayes),
    ({"id": "normal-distribution", "name": "正态分布(Z-score)"}, _model_normal),
    ({"id": "poisson", "name": "泊松分布"}, _model_poisson),
    ({"id": "monte-carlo", "name": "蒙特卡洛模拟"}, _montecarlo_model),
    ({"id": "frequency-hot", "name": "频率热号"}, _model_freq),
    ({"id": "cold-miss", "name": "遗漏回补"}, _model_cold),
    ({"id": "ewma", "name": "指数平滑(EWMA)"}, _model_ewma),
    ({"id": "apriori", "name": "关联规则"}, _model_apriori),
    ({"id": "ensemble", "name": "集成投票"}, _model_ensemble),
]


def generate_stats_predictions(target_period, prediction_date, history_data):
    """生成 10 个统计模型预测，返回与预测模型同结构的 model dict 列表。"""
    history = [d for d in history_data
               if isinstance(d, dict) and d.get("red_balls") and d.get("blue_ball")]
    if len(history) < 10:
        return []
    chrono = _chrono(history)

    models = []
    canonical = {}
    for meta, fn in _STATS_MODELS[:9]:  # 前 9 个模型
        groups, red_score, blue_score = fn(chrono, history)
        groups = _dedup_groups(groups, red_score, blue_score)
        models.append({
            "prediction_date": prediction_date,
            "target_period": target_period,
            "model_type": "stats",
            "model_id": meta["id"],
            "model_name": meta["name"],
            "predictions": groups,
        })
        canonical[meta["id"]] = (red_score, blue_score)

    # 第 10 个: 集成投票（依赖前 9 模型评分）
    groups, red_score, blue_score = _model_ensemble(chrono, history, canonical)
    groups = _dedup_groups(groups, red_score, blue_score)
    models.append({
        "prediction_date": prediction_date,
        "target_period": target_period,
        "model_type": "stats",
        "model_id": "ensemble",
        "model_name": "集成投票",
        "predictions": groups,
    })
    return models


# ==================== CLI ====================

def main():
    import argparse

    ap = argparse.ArgumentParser(description="生成 10 个双色球统计/概率/ML 模型预测（本地、纯标准库）")
    ap.add_argument("--output", default="", help="写入 JSON 文件路径（可选，仅测试用）")
    ap.add_argument("--target-period", default="", help="目标期号（默认取 next_draw）")
    ap.add_argument("--prediction-date", default="", help="预测日期 YYYY-MM-DD（默认取 last_updated）")
    args = ap.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "data", "lottery_history.json"), encoding="utf-8") as f:
        lh = json.load(f)
    history = lh.get("data", [])
    nd = lh.get("next_draw", {})
    target = args.target_period or nd.get("next_period", "")
    pdate = args.prediction_date or lh.get("last_updated", "")[:10]

    models = generate_stats_predictions(target, pdate, history)
    print(f"生成 {len(models)} 个统计模型预测 | 目标期 {target} | 预测日 {pdate}")
    ok_all = True
    for m in models:
        gs = m["predictions"]
        ok = (len(gs) == 4 and all(
            len(g["red_balls"]) == 6 and sorted(g["red_balls"]) == g["red_balls"]
            and g["blue_ball"] and 1 <= int(g["blue_ball"]) <= 16 for g in gs))
        ok_all = ok_all and ok
        groups_txt = " / ".join(f"G{g['group_id']} {' '.join(g['red_balls'])}+{g['blue_ball']}" for g in gs)
        print(f"  [{'✓' if ok else '✗'}] {m['model_name']:<16s} {groups_txt}")

    print("\n" + ("✅ 所有统计模型格式正确" if ok_all else "❌ 存在格式问题"))
    if args.output:
        payload = {"prediction_date": pdate, "target_period": target, "models": models}
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"  已写入: {args.output}")


if __name__ == "__main__":
    main()