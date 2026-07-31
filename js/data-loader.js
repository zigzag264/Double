/**
 * 数据加载模块
 * 负责从 JSON 文件加载历史开奖数据和 AI 预测数据
 */

const DataLoader = {
    /**
     * 加载历史开奖数据
     * @returns {Promise<Object>} 历史数据对象
     */
    async loadLotteryHistory() {
        try {
            const response = await fetch('./data/lottery_history.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('历史开奖数据加载成功', data);
            return data;
        } catch (error) {
            console.error('加载历史开奖数据失败:', error);
            throw error;
        }
    },

    /**
     * 加载 AI 预测数据
     * @returns {Promise<Object>} AI 预测数据对象
     */
    async loadPredictions() {
        try {
            const response = await fetch('./data/ai_predictions.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('AI 预测数据加载成功', data);
            return data;
        } catch (error) {
            console.error('加载 AI 预测数据失败:', error);
            throw error;
        }
    },

    /**
     * 加载历史预测对比数据
     * @returns {Promise<Object>} 历史预测对比数据对象
     */
    async loadPredictionsHistory() {
        try {
            const response = await fetch('./data/predictions_history.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('历史预测对比数据加载成功', data);
            return data;
        } catch (error) {
            console.error('加载历史预测对比数据失败:', error);
            throw error;
        }
    },

    /**
     * 加载排列三历史开奖数据
     * @returns {Promise<Object>} 排列三历史数据对象
     */
    async loadPailie3History() {
        try {
            const response = await fetch('./data/pailie3_history.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('排列三历史数据加载成功', data);
            return data;
        } catch (error) {
            console.error('加载排列三历史数据失败:', error);
            throw error;
        }
    },

    /**
     * 加载排列三 AI 预测数据
     * @returns {Promise<Object>} 排列三预测数据对象
     */
    async loadPailie3Predictions() {
        try {
            const response = await fetch('./data/pailie3_predictions.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('排列三AI预测数据加载成功', data);
            return data;
        } catch (error) {
            console.error('加载排列三AI预测数据失败:', error);
            throw error;
        }
    },

    /**
     * 加载排列三历史预测对比数据
     * @returns {Promise<Object>} 排列三预测对比数据对象
     */
    async loadPailie3HistoryPredictions() {
        try {
            const response = await fetch('./data/pailie3_predictions_history.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('排列三历史预测对比数据加载成功', data);
            return data;
        } catch (error) {
            console.error('加载排列三历史预测对比数据失败:', error);
            throw error;
        }
    },

    /**
     * 加载所有数据
     * @returns {Promise<Object>} 包含所有数据的对象
     */
    async loadAllData() {
        try {
            const [lotteryData, predictionData, predictionsHistoryData,
                    pailie3HistoryData, pailie3PredictionData, pailie3HistPredData] = await Promise.all([
                this.loadLotteryHistory(),
                this.loadPredictions(),
                this.loadPredictionsHistory(),
                this.loadPailie3History(),
                this.loadPailie3Predictions(),
                this.loadPailie3HistoryPredictions()
            ]);

            return {
                lottery: lotteryData,
                predictions: predictionData,
                predictionsHistory: predictionsHistoryData,
                pailie3History: pailie3HistoryData,
                pailie3Predictions: pailie3PredictionData,
                pailie3HistoryPredictions: pailie3HistPredData
            };
        } catch (error) {
            console.error('加载数据失败:', error);
            throw error;
        }
    }
};

// 导出到全局作用域
window.DataLoader = DataLoader;
