/**
 * 数据加载模块
 * 负责从 JSON 文件加载历史开奖数据和预测数据
 */

const DataLoader = {
    _cacheBust() {
        return '?v=' + Date.now();
    },

    // 统一 fetch 助手：加缓存清除参数、校验状态码、解析 JSON
    async _load(path, label) {
        try {
            const response = await fetch(path + this._cacheBust());
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log(`${label}加载成功`, data);
            return data;
        } catch (error) {
            console.error(`${label}加载失败:`, error);
            throw error;
        }
    },

    /**
     * 加载历史开奖数据
     * @returns {Promise<Object>} 历史数据对象
     */
    loadLotteryHistory() {
        return this._load('./data/lottery_history.json', '历史开奖数据');
    },

    /**
     * 加载预测数据
     * @returns {Promise<Object>} 预测数据对象
     */
    loadPredictions() {
        return this._load('./data/ai_predictions.json', '预测数据');
    },

    /**
     * 加载历史预测对比数据
     * @returns {Promise<Object>} 历史预测对比数据对象
     */
    loadPredictionsHistory() {
        return this._load('./data/predictions_history.json', '历史预测对比数据');
    }
};

// 导出到全局作用域
window.DataLoader = DataLoader;