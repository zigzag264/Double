/**
 * 主应用逻辑 - 新UI版本
 */

// 全局状态
let appData = {
    lotteryHistory: null,
    aiPredictions: null,
    predictionsHistory: null,
    tokenUsage: { records: [] }
};

// 各 Tab 渲染标记（懒渲染：首次进入某 Tab 时才构建；更新数据后重置）
const renderedTabs = { prediction: true };

// 次要数据（Tab2 历史分析 / Tab3 模型排行 用）懒加载状态
// 首屏只加载 lotteryHistory + aiPredictions；进入 Tab2/3 时再拉取 predictionsHistory + tokenUsage
let secondaryLoaded = false;
let secondaryLoading = null;

// 初始化应用
async function initApp() {
    try {
        // 加载数据
        await loadAllData();

        // 初始渲染默认 Tab（预测页）；其余 Tab 进入时懒渲染
        renderHeroBanner();
        renderModelsGrid();

        // 设置事件监听
        setupEventListeners();

        // 隐藏加载屏幕
        hideLoadingScreen();
    } catch (error) {
        console.error('初始化失败:', error);
        // 无论成功失败都隐藏加载屏幕，避免页面卡在加载中
        hideLoadingScreen();
        alert('数据加载失败，请刷新页面重试');
    }
}

// 加载首屏数据（仅 Tab1 所需：历史开奖 + 当前预测，体积小、首屏必需）
async function loadAllData() {
    try {
        const [lotteryHistory, aiPredictions] = await Promise.all([
            DataLoader.loadLotteryHistory(),
            DataLoader.loadPredictions()
        ]);

        appData.lotteryHistory = lotteryHistory;
        appData.aiPredictions = aiPredictions;
    } catch (error) {
        console.error('数据加载失败:', error);
        throw error;
    }
}

// 懒加载次要数据（Tab2/3 所需：历史预测对比 + token 用量）
// 首次进入任一次要 Tab 时触发，并发去重，仅拉取一次
async function loadSecondaryData() {
    if (secondaryLoaded) return;
    if (!secondaryLoading) {
        secondaryLoading = (async () => {
            try {
                const [predictionsHistory, tokenUsage] = await Promise.all([
                    DataLoader.loadPredictionsHistory(),
                    DataLoader.loadTokenUsage()
                ]);
                appData.predictionsHistory = predictionsHistory;
                appData.tokenUsage = tokenUsage;
            } catch (error) {
                console.error('次要数据加载失败:', error);
                // 降级：保证后续渲染函数拿到安全空结构而非 null
                if (!appData.predictionsHistory) {
                    appData.predictionsHistory = { predictions_history: [] };
                }
                if (!appData.tokenUsage) {
                    appData.tokenUsage = { records: [] };
                }
            } finally {
                secondaryLoaded = true;
                secondaryLoading = null;
            }
        })();
    }
    await secondaryLoading;
}

// 渲染Hero Banner
function renderHeroBanner() {
    if (!appData.lotteryHistory || !appData.aiPredictions) return;

    const nextDraw = appData.lotteryHistory.next_draw;

    // 更新期号
    const heroPeriodEl = document.getElementById('heroPeriod');
    if (heroPeriodEl) heroPeriodEl.textContent = nextDraw.next_period;

    // 更新日期显示
    const heroDateDisplayEl = document.getElementById('heroDateDisplay');
    if (heroDateDisplayEl) heroDateDisplayEl.textContent = nextDraw.next_date_display;

    // 更新开奖时间
    const heroDrawTimeEl = document.getElementById('heroDrawTime');
    if (heroDrawTimeEl) heroDrawTimeEl.textContent = `${nextDraw.draw_time} 开奖`;

    // 更新预测日期
    const heroPredictionDateEl = document.getElementById('heroPredictionDate');
    if (heroPredictionDateEl) heroPredictionDateEl.textContent = appData.aiPredictions.prediction_date;

    // 倒计时 (可选功能)
    const heroCountdownEl = document.getElementById('heroCountdown');
    if (heroCountdownEl) {
        const daysUntil = calculateDaysUntil(nextDraw.next_date);
        heroCountdownEl.textContent = daysUntil > 0 ? `距离开奖仅剩 ${daysUntil} 天` : '即将开奖';
    }
}

// 渲染模型网格
function renderModelsGrid() {
    if (!appData.aiPredictions) return;

    const modelsGridEl = document.getElementById('modelsGrid');
    if (!modelsGridEl) return;

    // 清空现有内容
    modelsGridEl.innerHTML = '';

    // 检测预测期号是否已开奖
    const targetPeriod = appData.aiPredictions.target_period;
    const latestDraw = appData.lotteryHistory?.data?.[0];
    let actualResult = null;

    if (latestDraw && parseInt(targetPeriod) <= parseInt(latestDraw.period)) {
        // 预测期号已开奖，查找对应的开奖结果
        actualResult = appData.lotteryHistory.data.find(draw => draw.period === targetPeriod);

        if (actualResult) {
            // 在网格前添加状态提示
            const statusBanner = createDrawnStatusBanner(actualResult);
            modelsGridEl.appendChild(statusBanner);
        }
    }

    // 按模型类型分区渲染（AI 模型 / 统计数学模型），同网格、不同分区标题
    const models = appData.aiPredictions.models || [];
    const aiModels = models.filter(m => (m.model_type || 'ai') !== 'stats');
    const statsModels = models.filter(m => m.model_type === 'stats');

    const renderSection = (title, list) => {
        if (!list.length) return;
        const header = document.createElement('div');
        header.className = 'models-section-title';
        header.innerHTML = `${title} <span class="models-section-count">${list.length}</span>`;
        modelsGridEl.appendChild(header);
        list.forEach(model => {
            modelsGridEl.appendChild(Components.createModelCard(model, actualResult));
        });
    };

    renderSection('🤖 AI 模型预测', aiModels);
    renderSection('📊 统计数学模型预测', statsModels);
}

// 创建已开奖状态横幅
function createDrawnStatusBanner(actualResult) {
    const banner = document.createElement('div');
    banner.className = 'drawn-status-banner';
    banner.innerHTML = `
        <div class="drawn-status-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
        </div>
        <div class="drawn-status-content">
            <h3 class="drawn-status-title">第 ${actualResult.period} 期已开奖</h3>
            <p class="drawn-status-subtitle">以下为预测命中情况对比</p>
        </div>
        <div class="drawn-status-balls">
            ${actualResult.red_balls.map(num => `<span class="mini-result-ball red">${num}</span>`).join('')}
            <span class="mini-result-ball blue">${actualResult.blue_ball}</span>
        </div>
    `;
    return banner;
}

// 渲染历史标签页
function renderRankingTab() {
    renderHitRankings();
    renderGroupedRankings();
    renderTokenUsage();
    renderAccuracyCards();
}

// 渲染模型 Token 用量排行表
function renderTokenUsage() {
    const container = document.getElementById('tokenUsageContainer');
    if (!container) return;

    const records = (appData.tokenUsage && appData.tokenUsage.records) || [];
    if (!records.length) {
        container.innerHTML = '<div class="ranking-empty"><p>暂无 Token 用量数据</p></div>';
        return;
    }

    // 按模型聚合
    const stats = {};
    records.forEach(r => {
        const key = r.model_id || r.model_name;
        const entry = stats[key] || {
            modelName: r.model_name,
            modelId: r.model_id,
            promptTokens: 0,
            completionTokens: 0,
            totalTokens: 0,
            elapsed: 0,
            calls: 0,
        };
        entry.promptTokens += r.prompt_tokens || 0;
        entry.completionTokens += r.completion_tokens || 0;
        entry.totalTokens += r.total_tokens || 0;
        entry.elapsed += r.elapsed_seconds || 0;
        entry.calls += 1;
        stats[key] = entry;
    });

    const arr = Object.values(stats).sort((a, b) => b.totalTokens - a.totalTokens);

    const fmt = (n) => n.toLocaleString('zh-CN');

    let rows = arr.map(m => `
        <tr>
            <td class="token-model">${m.modelName}</td>
            <td>${fmt(m.promptTokens)}</td>
            <td>${fmt(m.completionTokens)}</td>
            <td class="token-total">${fmt(m.totalTokens)}</td>
            <td>${m.elapsed.toFixed(1)}s</td>
            <td>${m.calls}</td>
            <td>${fmt(Math.round(m.totalTokens / m.calls))}</td>
        </tr>
    `).join('');

    const totalElapsed = arr.reduce((s, m) => s + m.elapsed, 0);

    container.innerHTML = `
        <div class="ranking-panel">
            <div class="ranking-header">
                <span class="ranking-title">Token 用量排行</span>
                <span class="ranking-sub">累计 ${records.length} 次调用 · 总耗时 ${totalElapsed.toFixed(1)}s</span>
            </div>
            <div class="token-table-wrap">
                <table class="ranking-table token-table">
                    <thead>
                        <tr>
                            <th>模型</th>
                            <th>总Prompt输入</th>
                            <th>总输出</th>
                            <th>总每次总计</th>
                            <th>总耗时</th>
                            <th>调用次数</th>
                            <th>平均token</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>`;
}

// 命中排行：按时间窗口（最新一期 / 最近一月 / 最近一年）分组取 Top10
function renderHitRankings() {
    const container = document.getElementById('rankingContainer');
    if (!container || !appData.predictionsHistory) return;
    container.innerHTML = '';

    const records = appData.predictionsHistory.predictions_history || [];
    if (!records.length) {
        container.innerHTML = '<div class="ranking-empty"><p>暂无命中回溯数据</p></div>';
        return;
    }

    // 时间窗口
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const last30Start = new Date(today);
    last30Start.setDate(today.getDate() - 30);
    const last365Start = new Date(today);
    last365Start.setDate(today.getDate() - 365);

    // 取最新一期的开奖日期（用作"最新一期"窗口）
    const latestDate = records[0]?.actual_result?.date || null;

    const windows = [
        { key: 'latest', label: '最新一期', sub: latestDate || '—', filter: (d) => d === latestDate },
        { key: 'month',  label: '最近一月', sub: '最近30天', filter: (d) => { const x = new Date(d); return x >= last30Start && x <= today; } },
        { key: 'year',   label: '最近一年', sub: '最近365天', filter: (d) => { const x = new Date(d); return x >= last365Start && x <= today; } },
    ];

    windows.forEach(win => {
        const panel = buildRankingPanel(win.label, win.sub, records, win.filter, win.key === 'latest');
        container.appendChild(panel);
    });
}

// 构建单个时间窗口排行面板（最新一期 / 最近一月 / 最近一年 共用一套渲染）
function buildRankingPanel(title, sub, records, dateFilter, isLatest) {
    // 收集该窗口内每条记录的 模型+策略 命中
    const stats = {};
    let hasLatest = false;

    records.forEach(rec => {
        const isLatestRec = !hasLatest && records.indexOf(rec) === 0;
        if (isLatestRec) hasLatest = true;
        const adate = rec.actual_result?.date;
        if (!adate || !dateFilter(adate)) return;
        // 每期内同「模型|策略」的期数与本期信息只计首次，避免同策略多组导致期数虚增
        const countedKeys = new Set();
        (rec.models || []).forEach(model => {
            (model.predictions || []).forEach(pred => {
                const hr = pred.hit_result;
                if (!hr) return;
                const key = model.model_name + '|' + (pred.strategy || '—');
                const e = stats[key] || {
                    modelName: model.model_name,
                    strategy: pred.strategy || '—',
                    totalHits: 0, bestHit: 0, games: 0,
                    redTotal: 0, blueHits: 0, currentHits: 0, hitNumbers: '',
                };
                e.totalHits += hr.total_hits || 0;
                e.redTotal += hr.red_hit_count || 0;
                e.blueHits += hr.blue_hit || 0;
                if (hr.total_hits > e.bestHit) e.bestHit = hr.total_hits;
                if (isLatestRec && !countedKeys.has(key)) {
                    e.currentHits = hr.total_hits || 0;
                    const parts = [];
                    if (hr.red_hits?.length) parts.push('红:' + hr.red_hits.join(' '));
                    if (hr.blue_hit) parts.push('蓝✓');
                    e.hitNumbers = parts.join(' ') || '—';
                }
                if (!countedKeys.has(key)) {
                    countedKeys.add(key);
                    e.games += 1;
                }
                stats[key] = e;
            });
        });
    });

    const panel = document.createElement('div');
    panel.className = 'ranking-panel';

    const header = document.createElement('div');
    header.className = 'ranking-header';
    header.innerHTML = `<span class="ranking-title">${title}</span><span class="ranking-sub">${sub}</span>`;
    panel.appendChild(header);

    const arr = Object.values(stats);
    if (!arr.length) {
        const empty = document.createElement('div');
        empty.className = 'ranking-empty';
        empty.innerHTML = '<p>该时段暂无命中数据</p>';
        panel.appendChild(empty);
        return panel;
    }

    // 排序 + Top10：最新一期按 蓝球 → 本期命中；其余按 总球数 → 累计蓝球
    if (isLatest) {
        arr.sort((a, b) =>
            (b.hitNumbers.includes('蓝✓') ? 1 : 0) - (a.hitNumbers.includes('蓝✓') ? 1 : 0) ||
            b.currentHits - a.currentHits);
    } else {
        arr.sort((a, b) => b.totalHits - a.totalHits || b.blueHits - a.blueHits);
    }
    const top10 = arr.slice(0, 10);

    // 两套列配置共用表格构建逻辑
    const headers = isLatest
        ? ['模型', '策略', '本期命中', '命中红球', '蓝球']
        : ['模型', '策略', '历史最多', '累计红球', '累计蓝球', '总球数', '期数'];
    const keys = isLatest
        ? ['model', 'strategy', 'current', 'reds', 'blue']
        : ['model', 'strategy', 'best', 'redTotal', 'blueTotal', 'total', 'games'];

    const cell = {
        model: (e) => `<td class="rank-model">${escHtml(e.modelName)}</td>`,
        strategy: (e) => `<td class="rank-strategy">${escHtml(e.strategy)}</td>`,
        current: (e) => `<td class="rank-current">${e.currentHits} 球</td>`,
        reds: (e) => `<td class="rank-hits">${escHtml(e.hitNumbers.split('蓝✓')[0].replace('红:', '').trim() || '—')}</td>`,
        blue: (e) => `<td class="rank-blue">${e.hitNumbers.includes('蓝✓') ? '✓' : '—'}</td>`,
        best: (e) => `<td class="rank-best ${e.bestHit >= 5 ? 'excellent' : e.bestHit >= 3 ? 'good' : ''}">${e.bestHit} 球</td>`,
        redTotal: (e) => `<td class="rank-total">${e.redTotal} 球</td>`,
        blueTotal: (e) => `<td class="rank-blue">${e.blueHits} 球</td>`,
        total: (e) => `<td class="rank-total">${e.totalHits} 球</td>`,
        games: (e) => `<td class="rank-games">${e.games}</td>`,
    };

    const table = document.createElement('table');
    table.className = 'ranking-table';
    const thead = document.createElement('thead');
    thead.innerHTML = '<tr><th>#</th>' + headers.map(h => `<th>${h}</th>`).join('') + '</tr>';
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    top10.forEach((e, i) => {
        const rankClass = i < 3 ? ' rank-' + (i + 1) : '';
        const tr = document.createElement('tr');
        tr.innerHTML = `<td class="rank-num${rankClass}">${i + 1}</td>` + keys.map(k => cell[k](e)).join('');
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    panel.appendChild(table);

    return panel;
}

// 策略 / 模型 分组统计（新增，不替换原有排行）
function renderGroupedRankings() {
    const container = document.getElementById('groupedRankingContainer');
    if (!container || !appData.predictionsHistory) return;
    container.innerHTML = '';

    const records = appData.predictionsHistory.predictions_history || [];
    if (!records.length) {
        container.innerHTML = '<div class="ranking-empty"><p>暂无命中回溯数据</p></div>';
        return;
    }

    // 收集每个模型的命中汇总（策略分组已移除）
    // 注意：每期每模型有 4 组预测，"期数"须按期去重，否则被组数放大 4 倍
    const stats = {};   // key = 模型名
    records.forEach(rec => {
        const period = rec.actual_result?.period;
        (rec.models || []).forEach(model => {
            (model.predictions || []).forEach(pred => {
                const hr = pred.hit_result;
                if (!hr) return;
                const key = model.model_name || '—';
                const entry = stats[key] || {
                    name: key,
                    maxHits: 0,
                    redTotal: 0,
                    blueHits: 0,
                    totalHits: 0,
                    games: 0,
                    periods: new Set(),
                };
                entry.redTotal += hr.red_hit_count || 0;
                entry.blueHits += hr.blue_hit || 0;
                entry.totalHits += hr.total_hits || 0;
                if (period) entry.periods.add(period);
                if ((hr.total_hits || 0) > entry.maxHits) entry.maxHits = hr.total_hits || 0;
                stats[key] = entry;
            });
        });
    });
    // 期数 = 该模型实际参与的不同期号数（去重）
    Object.values(stats).forEach(e => { e.games = e.periods.size; });

    // 按 总球数 降序排序
    const arr = Object.values(stats).sort((a, b) => b.totalHits - a.totalHits || b.blueHits - a.blueHits);

    const modelPanel = buildGroupedPanel('模型分组', '按模型统计命中（全部历史）', arr);
    if (modelPanel) container.appendChild(modelPanel);
}

// 构建分组统计面板
function buildGroupedPanel(title, sub, entries) {
    const panel = document.createElement('div');
    panel.className = 'ranking-panel';

    const header = document.createElement('div');
    header.className = 'ranking-header';
    header.innerHTML = '<span class="ranking-title">' + title + '</span>'
        + '<span class="ranking-sub">' + sub + '</span>';
    panel.appendChild(header);

    if (!entries.length) {
        const empty = document.createElement('div');
        empty.className = 'ranking-empty';
        empty.innerHTML = '<p>暂无命中数据</p>';
        panel.appendChild(empty);
        return panel;
    }

    const table = document.createElement('table');
    table.className = 'ranking-table';
    const thead = document.createElement('thead');
    thead.innerHTML = '<tr>'
        + '<th>#</th><th>名称</th>'
        + '<th>历史最大单期球数</th><th>历史总红数</th><th>历史总蓝球</th><th>总球数</th>'
        + '<th>期数</th></tr>';
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    entries.forEach((e, i) => {
        const tr = document.createElement('tr');
        const rankClass = i === 0 ? ' rank-1' : i === 1 ? ' rank-2' : i === 2 ? ' rank-3' : '';
        const bestTag = e.maxHits >= 5 ? 'excellent' : e.maxHits >= 3 ? 'good' : '';
        tr.innerHTML =
            '<td class="rank-num' + rankClass + '">' + (i + 1) + '</td>' +
            '<td class="rank-model">' + escHtml(e.name) + '</td>' +
            '<td class="rank-best ' + bestTag + '">' + e.maxHits + ' 球</td>' +
            '<td class="rank-total">' + e.redTotal + ' 球</td>' +
            '<td class="rank-blue">' + e.blueHits + ' 球</td>' +
            '<td class="rank-total">' + e.totalHits + ' 球</td>' +
            '<td class="rank-games">' + e.games + ' 期</td>';
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    panel.appendChild(table);

    return panel;
}

// HTML 转义（避免注入）
function escHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// 渲染命中记录（每期一行紧凑摘要）
function renderAccuracyCards() {
    if (!appData.predictionsHistory) return;

    const containerEl = document.getElementById('accuracyCardsContainer');
    if (!containerEl) return;

    containerEl.innerHTML = '';

    const records = appData.predictionsHistory.predictions_history || [];
    if (!records.length) {
        containerEl.innerHTML = '<div class="ranking-empty"><p>暂无命中记录</p></div>';
        return;
    }

    records.forEach(record => {
        containerEl.appendChild(Components.createAccuracySummaryRow(record));
    });
}

// 渲染历史表格
function renderHistoryTable() {
    if (!appData.lotteryHistory) return;

    const tbodyEl = document.getElementById('historyTableBody');
    if (!tbodyEl) return;
    tbodyEl.innerHTML = '';

    const table = tbodyEl.parentElement;           // <table>
    const scrollWrap = table.parentElement;        // .history-table-scroll
    const container = scrollWrap.parentElement;    // .history-table-container

    // 清除之前渲染的隐藏行和 toggle 按钮，避免重复
    const oldHidden = document.getElementById('historyHiddenRows');
    if (oldHidden) oldHidden.remove();
    const oldToggle = document.getElementById('historyToggle');
    if (oldToggle) oldToggle.remove();

    const allRows = appData.lotteryHistory.data;
    const total = allRows.length;
    const shown = Math.min(3, total);

    for (let i = 0; i < shown; i++) {
        tbodyEl.appendChild(Components.createHistoryTableRow(allRows[i]));
    }

    if (total <= shown) return;

    const remaining = total - shown;

    // 隐藏行：先插入一个 <tbody> 到表格末尾、初始隐藏
    const hiddenTbody = document.createElement('tbody');
    hiddenTbody.id = 'historyHiddenRows';
    hiddenTbody.style.display = 'none';
    for (let i = shown; i < total; i++) {
        hiddenTbody.appendChild(Components.createHistoryTableRow(allRows[i]));
    }
    table.appendChild(hiddenTbody);

    // 展开/折叠按钮：插入到 .history-table-container 中、表格之后
    const toggle = document.createElement('div');
    toggle.id = 'historyToggle';
    toggle.className = 'history-toggle';
    toggle.innerHTML = '<span>展开查看全部 ' + remaining + ' 期</span>'
        + '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>';

    container.appendChild(toggle);

    toggle.addEventListener('click', function () {
        if (hiddenTbody.style.display === 'none') {
            hiddenTbody.style.display = '';
            toggle.innerHTML = '<span>收起</span>'
                + '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>';
        } else {
            hiddenTbody.style.display = 'none';
            toggle.innerHTML = '<span>展开查看全部 ' + remaining + ' 期</span>'
                + '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>';
        }
    });
}

// 渲染统计卡片
function renderStatisticsCards() {
    if (!appData.lotteryHistory) return;

    // 计算红球频率
    const redFrequency = {};
    for (let i = 1; i <= 33; i++) {
        redFrequency[i.toString().padStart(2, '0')] = 0;
    }

    // 计算蓝球频率
    const blueFrequency = {};
    for (let i = 1; i <= 16; i++) {
        blueFrequency[i.toString().padStart(2, '0')] = 0;
    }

    // 计算和值
    let totalSum = 0;

    appData.lotteryHistory.data.forEach(draw => {
        // 红球
        draw.red_balls.forEach(ball => {
            redFrequency[ball] = (redFrequency[ball] || 0) + 1;
        });
        // 蓝球
        blueFrequency[draw.blue_ball] = (blueFrequency[draw.blue_ball] || 0) + 1;
        // 和值
        const sum = draw.red_balls.reduce((acc, ball) => acc + parseInt(ball), 0);
        totalSum += sum;
    });

    // 找出最热红球
    const hottestRed = Object.entries(redFrequency).sort((a, b) => b[1] - a[1])[0];

    // 找出最热蓝球
    const hottestBlue = Object.entries(blueFrequency).sort((a, b) => b[1] - a[1])[0];

    // 平均和值
    const avgSum = Math.round(totalSum / appData.lotteryHistory.data.length);

    // 更新UI
    const totalDrawsEl = document.getElementById('statTotalDraws');
    if (totalDrawsEl) totalDrawsEl.textContent = `${appData.lotteryHistory.data.length} 期`;

    const hottestRedEl = document.getElementById('statHottestRed');
    if (hottestRedEl) hottestRedEl.textContent = `${hottestRed[0]} (${hottestRed[1]}次)`;

    const hottestBlueEl = document.getElementById('statHottestBlue');
    if (hottestBlueEl) hottestBlueEl.textContent = `${hottestBlue[0]} (${hottestBlue[1]}次)`;

    const avgSumEl = document.getElementById('statAvgSum');
    if (avgSumEl) avgSumEl.textContent = avgSum;
}

// 一键更新数据：爬虫更新开奖 + AI 预测 + 刷新页面
async function handleUpdateData() {
    const btn = document.getElementById('updateDataBtn');
    const statusEl = document.getElementById('updateStatus');
    const btnText = document.getElementById('updateBtnText');
    if (!btn || !statusEl) return;

    // 防止重复点击
    if (btn.disabled) return;
    btn.disabled = true;
    btn.classList.add('loading');
    statusEl.className = 'update-status loading';
    statusEl.textContent = '正在更新开奖数据...';
    if (btnText) btnText.textContent = '更新中...';

    try {
        const response = await fetch('/api/update', { method: 'POST' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();

        if (result.success) {
            // 更新成功 → 用新数据刷新页面
            if (result.data) {
                appData.lotteryHistory = result.data.lottery_history || appData.lotteryHistory;
                appData.aiPredictions = result.data.ai_predictions || appData.aiPredictions;
                appData.predictionsHistory = result.data.predictions_history || appData.predictionsHistory;
                appData.tokenUsage = result.data.token_usage || appData.tokenUsage;
                // /api/update 已返回次要数据，标记为已加载，避免进入 Tab2/3 时重复拉取
                secondaryLoaded = true;
            }

            // 重置渲染标记：预测页立即重渲，其余 Tab 下次进入时按新数据懒渲染
            renderedTabs.prediction = true;
            delete renderedTabs.analysis;
            delete renderedTabs.ranking;
            renderHeroBanner();
            renderModelsGrid();

            statusEl.className = 'update-status success';
            statusEl.textContent = '✅ 更新成功！最新开奖与下期预测已同步';
        } else {
            statusEl.className = 'update-status error';
            // 显示错误摘要（取 message 中 ❌ 开头的行）
            const data = appData.lotteryHistory?.data || [];
            const latest = data[0] || {};
            statusEl.textContent = `❌ 更新失败。开奖数据已更新至 ${latest.period || '未知'} 期，但 AI 预测生成失败（请检查 API 凭证）。`;
        }
    } catch (error) {
        console.error('更新数据失败:', error);
        statusEl.className = 'update-status error';
        statusEl.textContent = '❌ 更新失败：无法连接服务器。请确认通过 python server.py 启动服务。';
    } finally {
        btn.disabled = false;
        btn.classList.remove('loading');
        if (btnText) btnText.textContent = '更新数据';
    }
}

// 设置事件监听
function setupEventListeners() {
    // Tab 切换（桌面端 + 移动端统一绑定）
    document.querySelectorAll('.nav-item, .mobile-nav-item').forEach(item => {
        item.addEventListener('click', () => handleTabSwitch(item.dataset.tab));
    });

    // 更新数据按钮
    const updateBtn = document.getElementById('updateDataBtn');
    if (updateBtn) {
        updateBtn.addEventListener('click', handleUpdateData);
    }
}

// 处理 Tab 切换（懒渲染：首次进入某 Tab 时才构建内容）
async function handleTabSwitch(tabName) {
    // 同步导航与内容区状态
    document.querySelectorAll('.nav-item, .mobile-nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.tab === tabName);
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.dataset.tab === tabName);
    });

    // 次要 Tab 需先懒加载次要数据再渲染
    if (tabName === 'analysis' && !renderedTabs.analysis) {
        await loadSecondaryData();
        renderedTabs.analysis = true;
        renderStatisticsCards();
        renderHistoryTable();
        renderAccuracyCards();
    }
    if (tabName === 'ranking' && !renderedTabs.ranking) {
        await loadSecondaryData();
        renderedTabs.ranking = true;
        renderRankingTab();
    }
}

// 隐藏加载屏幕
function hideLoadingScreen() {
    const loadingScreen = document.getElementById('loadingScreen');
    const mainApp = document.getElementById('mainApp');

    if (loadingScreen) {
        loadingScreen.style.display = 'none';
    }

    if (mainApp) {
        mainApp.style.display = 'block';
    }
}

// 计算距离目标日期的天数
function calculateDaysUntil(targetDateStr) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const targetDate = new Date(targetDateStr);
    targetDate.setHours(0, 0, 0, 0);

    const diffTime = targetDate - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    return diffDays;
}

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
