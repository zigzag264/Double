# 双色球开奖与 AI 预测数据展示系统

> 在线访问：[https://double-color-ball-ai.vercel.app](https://double-color-ball-ai.vercel.app)

<img src="images/image1.jpg" width="70%">

一个现代化的双色球数据展示系统，支持历史开奖数据查看和多模型 AI 预测展示。

## ✨ 主要特性

- 🎨 现代化 UI 设计，支持亮色/暗色主题切换
- 📊 历史开奖数据展示
- 🤖 多 AI 模型预测结果对比
- 🎯 自动计算预测命中情况
- 📱 完全响应式设计，支持移动端
- ⚡ 优雅的动画效果和交互体验

<details>
<summary><h2>🚀 快速开始</h2></summary>

### 方法一：使用启动脚本（推荐）

#### macOS/Linux:
```bash
# 进入项目目录
cd Double-Color-Ball-AI

# 运行启动脚本
./start_server.sh
```

#### Windows:
```cmd
# 双击运行 start_server.bat
# 或在命令行中运行
start_server.bat
```

然后在浏览器中打开：http://localhost:8000

### 方法二：手动启动服务器

```bash
# 使用 Python 启动 HTTP 服务器
python3 -m http.server 8000

# 或使用 Python 2
python -m SimpleHTTPServer 8000
```

然后在浏览器中打开：http://localhost:8000


</details>

## 🔮 AI 预测策略

每个 AI 模型会生成 5 组预测，分别采用不同策略：

| 策略 | 说明 |
|------|------|
| 热号追随者 | 选择最近 30 期高频号码，追踪热门趋势 |
| 冷号逆向者 | 选择最近 30 期低频号码，期待均值回归 |
| 平衡策略师 | 综合奇偶比、大小比、和值、连号等多维度平衡 |
| 周期理论家 | 选择短期频率上穿长期频率的号码 |
| 综合决策者 | 融合以上所有策略的综合方案 |

## 📁 项目结构

```
Double-Color-Ball-AI/
├── index.html                     # 主页面
├── css/
│   └── style.css                  # 样式文件
├── js/
│   ├── app.js                     # 主应用逻辑
│   ├── data-loader.js             # 数据加载模块
│   └── components.js              # UI 组件
├── data/
│   ├── lottery_history.json       # 历史开奖数据
│   └── ai_predictions.json        # AI 预测数据
├── fetch_history/
│   ├── fetch_lottery_history.py   # 数据爬取脚本
│   └── lottery_data.json          # 原始爬取数据
├── doc/
│   └── prompt.md                  # AI 预测 Prompt 模板
├── generate_ai_prediction.py      # 🆕 AI 预测自动生成脚本
├── add_gpt5_prediction.py         # 辅助脚本：添加历史预测
├── start_server.sh                # 启动脚本 (macOS/Linux)
├── start_server.bat               # 启动脚本 (Windows)
├── AI_PREDICTION_GUIDE.md         # 🆕 AI 预测自动化指南
└── README.md                      # 项目说明
```

## 🔄 更新数据

### 更新历史开奖数据

```bash
cd fetch_history
python3 fetch_lottery_history.py
```

脚本会：
- 自动从 500 彩票网爬取最新数据
- 与现有数据合并（去重）
- 创建带时间戳的备份文件
- **自动同步到 `data/lottery_history.json`**
- **自动计算下期开奖信息**

### 自动生成 AI 预测数据（新功能！）

**一键生成多模型预测**：

```bash
python3 generate_ai_prediction.py
```

脚本功能：
- 🤖 自动调用 4 个 AI 模型（GPT-5, Claude 4.5, Gemini 2.5, DeepSeek R1）
- 📊 基于历史数据生成 5 种策略预测
- ✅ 自动验证预测数据格式
- 💾 自动备份现有预测
- 🎯 自动获取下期期号和日期

**首次使用需配置 API**：

1. 安装依赖：
```bash
pip install openai
```

2. 设置环境变量：
```bash
export AI_API_KEY="your-api-key"
export AI_BASE_URL="https://your-api-endpoint.com/v1"  # 可选，有默认值
```

或创建 `.env` 文件（参考 `.env.example`）。

3. 如使用 GitHub Actions 自动运行，需在仓库 Settings > Secrets and variables > Actions 中添加：
   - `AI_API_KEY` — 你的 API Key
   - `AI_BASE_URL` — API 端点地址（可选）

详细说明：[AI_PREDICTION_GUIDE.md](./AI_PREDICTION_GUIDE.md)

### 手动更新 AI 预测数据

如果需要手动编辑，可以直接修改 `data/ai_predictions.json` 文件，格式如下：

```json
{
  "prediction_date": "2025-10-21",
  "target_period": "25121",
  "models": [
    {
      "model_id": "model-id",
      "model_name": "模型名称",
      "predictions": [
        {
          "group_id": 1,
          "strategy": "策略名称",
          "red_balls": ["01", "02", "03", "04", "05", "06"],
          "blue_ball": "07",
          "description": "策略描述"
        }
      ]
    }
  ]
}
```

## 🎨 主题切换

点击右上角的主题切换按钮（太阳/月亮图标）可以在亮色和暗色主题之间切换。主题偏好会自动保存到浏览器本地存储。

## 📝 数据格式说明

### lottery_history.json
```json
{
  "last_updated": "2025-10-21T10:00:00Z",
  "data": [
    {
      "period": "25120",
      "date": "2025-10-19",
      "red_balls": ["01", "02", "04", "07", "13", "32"],
      "blue_ball": "07"
    }
  ]
}
```

### ai_predictions.json
```json
{
  "prediction_date": "2025-10-21",
  "target_period": "25121",
  "models": [...]
}
```

## ⚠️ 重要提示

**浏览器安全限制**:
- ❌ 不能直接双击 `index.html` 打开（会遇到 CORS 错误）
- ✅ 必须通过 HTTP 服务器访问

这是因为浏览器的同源策略限制，使用 `file://` 协议无法加载本地 JSON 文件。

## 🛠️ 技术栈

- **前端**: 纯 JavaScript (ES6+)
- **样式**: 现代 CSS (CSS Variables, Flexbox, Grid)
- **数据爬取**: Python 3 + BeautifulSoup
- **设计风格**: shadcn/ui inspired

## 📄 免责声明

本网站展示的 AI 预测数据仅供参考和研究使用，不构成任何购彩建议。彩票开奖结果具有随机性，任何预测都无法保证中奖。请理性购彩，量力而行。

## 🌐 部署到 Vercel

本项目已配置好 Vercel 部署，详细步骤请查看 [DEPLOYMENT.md](./DEPLOYMENT.md)

### 快速部署

1. 安装 Vercel CLI: `npm install -g vercel`
2. 登录: `vercel login`
3. 部署: `vercel`

**不会有跨域问题！** Vercel 提供标准的 HTTP 服务，所有资源都从同一域名加载。

### 特性

- ✅ 免费部署
- ✅ 自动 HTTPS
- ✅ 全球 CDN 加速
- ✅ 自动部署（连接 GitHub）
- ✅ 支持自定义域名

详细说明: [DEPLOYMENT.md](./DEPLOYMENT.md)

## 📧 反馈与支持

如有问题或建议，欢迎提交 Issue 或 Pull Request。
