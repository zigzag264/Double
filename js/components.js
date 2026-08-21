/**
 * UI 组件模块 - 新UI版本
 * 负责生成和渲染各种 UI 组件
 */

const Components = {
    /**
     * 创建号码球元素
     * @param {string} number - 号码
     * @param {string} color - 颜色 ('red' 或 'blue')
     * @param {string} size - 大小 ('sm', 'md', 'lg')
     * @param {boolean} isHit - 是否命中
     * @returns {HTMLElement} 号码球元素
     */
    createLotteryBall(number, color, size = 'md', isHit = false) {
        const ball = document.createElement('div');
        ball.className = `lottery-ball ${color} size-${size}${isHit ? ' hit' : ''}`;
        ball.innerHTML = `<span>${number}</span>`;
        return ball;
    },

    /**
     * 创建球分隔符
     * @returns {HTMLElement} 分隔符元素
     */
    createBallDivider() {
        const divider = document.createElement('div');
        divider.className = 'ball-divider';
        return divider;
    },

    /**
     * 获取模型头部样式类名（按 model_id 精确映射，避免中文名子串误判）
     * @param {string} modelId - 模型 ID
     * @returns {string} CSS 类名
     */
    getModelHeaderClass(modelId) {
        const map = {
            'markov-chain': 'markov',
            'bayesian': 'bayes',
            'normal-distribution': 'normal',
            'poisson': 'poisson',
            'monte-carlo': 'monte',
            'frequency-hot': 'hot',
            'cold-miss': 'cold',
            'ewma': 'ewma',
            'apriori': 'apriori',
            'ensemble': 'ensemble',
        };
        return `model-header-${map[modelId] || 'markov'}`;
    },

    /**
     * 创建模型预测卡片
     * @param {Object} model - 模型数据
     * @param {Object} actualResult - 实际开奖结果（可选）
     * @returns {HTMLElement} 模型卡片元素
     */
    createModelCard(model, actualResult = null) {
        const card = document.createElement('div');
        card.className = 'model-card';

        const headerClass = this.getModelHeaderClass(model.model_id);

        // 清理 model_id 以生成有效的 DOM ID（移除特殊字符）
        const safeModelId = model.model_id.replace(/[^a-zA-Z0-9-_]/g, '-');

        // 单次遍历：预计算每组命中结果 + 找最佳命中（避免重复 compareNumbers）
        let bestHitCount = 0;
        let bestGroupId = null;
        const hitResults = model.predictions.map(prediction => {
            const hitResult = actualResult ? this.compareNumbers(prediction, actualResult) : null;
            if (hitResult && hitResult.totalHits > bestHitCount) {
                bestHitCount = hitResult.totalHits;
                bestGroupId = prediction.group_id;
            }
            return hitResult;
        });

        card.innerHTML = `
            <div class="model-card-header ${headerClass}">
                <div class="model-card-header-left">
                    <div class="model-icon-box">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/><path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"/><path d="M17.599 6.5a3 3 0 0 0 .399-1.375"/><path d="M6.003 5.125A3 3 0 0 0 6.401 6.5"/><path d="M3.477 10.896a4 4 0 0 1 .585-.396"/><path d="M19.938 10.5a4 4 0 0 1 .585.396"/><path d="M6 18a4 4 0 0 1-1.967-.516"/><path d="M19.967 17.484A4 4 0 0 1 18 18"/>
                        </svg>
                    </div>
                    <div class="model-name-wrapper">
                        <h3>${model.model_name}</h3>
                        <div class="model-id">
                            <span class="model-id-dot"></span>
                            <span>Model: ${model.model_id}</span>
                        </div>
                    </div>
                </div>
                <div class="model-card-header-right">
                    ${actualResult && bestHitCount > 0 ? `
                        <div class="model-best-hit-badge">
                            <svg viewBox="0 0 24 24" fill="currentColor">
                                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                            </svg>
                            <span>最佳 ${bestHitCount} 中</span>
                        </div>
                    ` : ''}
                    <div class="model-card-ticket-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M13 5v2"/><path d="M13 17v2"/><path d="M13 11v2"/>
                        </svg>
                    </div>
                </div>
            </div>
            <div class="model-card-content">
                <div class="strategy-group" id="strategies-${safeModelId}"></div>
            </div>
        `;

        // 添加策略行（命中结果已在上一步预计算，直接传入避免重复计算）
        const strategiesContainer = card.querySelector(`#strategies-${safeModelId}`);
        model.predictions.forEach((prediction, index) => {
            const isBest = actualResult && prediction.group_id === bestGroupId;
            strategiesContainer.appendChild(this.createStrategyRow(prediction, index === model.predictions.length - 1, hitResults[index], isBest));
        });

        return card;
    },

    /**
     * 创建策略行
     * @param {Object} prediction - 预测数据
     * @param {boolean} isLast - 是否是最后一个
     * @param {Object|null} hitResult - 预计算的命中结果（已开奖时非 null）
     * @param {boolean} isBest - 是否是最佳预测组
     * @returns {HTMLElement} 策略行元素
     */
    createStrategyRow(prediction, isLast = false, hitResult = null, isBest = false) {
        const row = document.createElement('div');
        row.className = 'strategy-row';

        // 创建头部
        const header = document.createElement('div');
        header.className = 'strategy-header';
        header.innerHTML = `
            <div class="strategy-label-row">
                <div class="strategy-group-badge${isBest ? ' best' : ''}">${isBest ? '★ ' : ''}G-${prediction.group_id}</div>
                <span class="strategy-name">${prediction.strategy}</span>
                ${hitResult ? `
                    <div class="strategy-hit-stats">
                        <span class="hit-stat red">${hitResult.redHitCount}红</span>
                        <span class="hit-stat ${hitResult.blueHit ? 'blue' : 'miss'}">${hitResult.blueHit ? '1' : '0'}蓝</span>
                    </div>
                ` : ''}
            </div>
        `;
        row.appendChild(header);

        // 创建球容器
        const ballsContainer = document.createElement('div');
        ballsContainer.className = 'strategy-balls';

        prediction.red_balls.forEach(num => {
            const isHit = hitResult?.redHits?.includes(num);
            ballsContainer.appendChild(this.createLotteryBall(num, 'red', 'md', isHit));
        });

        ballsContainer.appendChild(this.createBallDivider());

        const blueHit = hitResult?.blueHit || false;
        ballsContainer.appendChild(this.createLotteryBall(prediction.blue_ball, 'blue', 'md', blueHit));

        row.appendChild(ballsContainer);

        // 创建描述
        const desc = document.createElement('p');
        desc.className = 'strategy-description';
        desc.textContent = prediction.description;
        row.appendChild(desc);

        // 添加分隔符 (最后一个除外)
        if (!isLast) {
            const separator = document.createElement('div');
            separator.className = 'strategy-separator';
            row.appendChild(separator);
        }

        return row;
    },

    /**
     * 创建命中记录紧凑摘要行（期号 + 开奖号码 + 最佳命中）
     * @param {Object} record - 历史记录（predictions_history 项）
     * @returns {HTMLElement} 摘要行元素
     */
    createAccuracySummaryRow(record) {
        const result = record.actual_result || {};
        const row = document.createElement('div');
        row.className = 'accuracy-summary-row';

        const period = document.createElement('span');
        period.className = 'accuracy-summary-period';
        period.textContent = `第 ${result.period || '—'} 期`;
        row.appendChild(period);

        if (result.date) {
            const date = document.createElement('span');
            date.className = 'accuracy-summary-date';
            date.textContent = result.date;
            row.appendChild(date);
        }

        const balls = document.createElement('span');
        balls.className = 'accuracy-summary-balls';
        (result.red_balls || []).forEach(n => balls.appendChild(this.createLotteryBall(n, 'red', 'sm')));
        if (result.blue_ball) balls.appendChild(this.createLotteryBall(result.blue_ball, 'blue', 'sm'));
        row.appendChild(balls);

        // 最佳命中：取各模型 best_hit_count 最高者
        let best = { name: '—', hits: 0, group: null };
        (record.models || []).forEach(m => {
            if ((m.best_hit_count || 0) > best.hits) {
                best = { name: m.model_name, hits: m.best_hit_count || 0, group: m.best_group };
            }
        });
        const bestEl = document.createElement('span');
        bestEl.className = 'accuracy-summary-best';
        bestEl.innerHTML = `最佳 <span class="accuracy-summary-hits">${best.hits} 球</span> · ${best.name}${best.group ? `（G${best.group}）` : ''}`;
        row.appendChild(bestEl);

        return row;
    },

    /**
     * 创建历史表格行
     * @param {Object} draw - 开奖数据
     * @returns {HTMLElement} 表格行元素
     */
    createHistoryTableRow(draw) {
        const row = document.createElement('tr');

        // 期号
        const periodCell = document.createElement('td');
        periodCell.className = 'period-cell';
        periodCell.textContent = draw.period;
        row.appendChild(periodCell);

        // 日期
        const dateCell = document.createElement('td');
        dateCell.className = 'date-cell';
        dateCell.textContent = draw.date;
        row.appendChild(dateCell);

        // 开奖号码
        const ballsCell = document.createElement('td');
        const ballsContainer = document.createElement('div');
        ballsContainer.className = 'balls-cell';

        draw.red_balls.forEach(num => {
            ballsContainer.appendChild(this.createLotteryBall(num, 'red', 'sm'));
        });

        const divider = document.createElement('div');
        divider.style.width = '8px';
        ballsContainer.appendChild(divider);

        ballsContainer.appendChild(this.createLotteryBall(draw.blue_ball, 'blue', 'sm'));

        ballsCell.appendChild(ballsContainer);
        row.appendChild(ballsCell);

        return row;
    },

    /**
     * 比较预测号码与实际开奖结果
     * @param {Object} prediction - 预测数据
     * @param {Object} actualResult - 实际开奖结果
     * @returns {Object} 命中信息
     */
    compareNumbers(prediction, actualResult) {
        if (!actualResult) {
            return null;
        }

        const redHits = prediction.red_balls.filter(ball =>
            actualResult.red_balls.includes(ball)
        );

        const blueHit = prediction.blue_ball === actualResult.blue_ball;

        return {
            redHits: redHits,
            redHitCount: redHits.length,
            blueHit: blueHit,
            totalHits: redHits.length + (blueHit ? 1 : 0)
        };
    }
};
