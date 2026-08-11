# 双色球 AI 预测系统

## 项目概述

基于 AI 模型的双色球彩票预测与数据分析展示平台，展示 5 个大模型（DeepSeek V3、DeepSeek V3.2 Exp、Tongyi Analysis Pro、Kimi K2、Qwen 3.7 Flash (07-15)）对双色球开奖号码的预测，并提供图表分析、历史预测命中率对比、每日邮件推送等完整功能。

**核心特性**:
- 🤖 多 AI 模型预测（通过 API 自动生成）
- 📊 数据趋势图表分析（Chart.js 5 类图表）
- 🎯 历史预测命中率回溯
- ⏰ 自动更新开奖数据（GitHub Actions）
- 📧 每日邮件汇总推送
- 🎨 深色/浅色主题切换、响应式设计

**双色球规则**:
- 红球：从 01-33 中选择 6 个号码
- 蓝球：从 01-16 中选择 1 个号码
- 开奖时间：每周二、四、日 21:15
- 线上地址：`https://double-color-ball-ai.vercel.app`

---

## 项目结构

```
double/
├── index.html                        # 主页面（3 个 Tab）
├── css/
│   └── style.css                     # 样式（深色/浅色 CSS 变量）
├── js/
│   ├── app.js                        # 主应用逻辑 + 图表渲染（Chart.js）
│   ├── components.js                 # UI 组件（号码球、卡片、对比）
│   └── data-loader.js                # 数据加载模块（fetch JSON）
├── data/                             # 前端数据文件
│   ├── lottery_history.json          # 历史开奖数据 + 下期开奖信息
│   ├── lottery_data.json             # （历史文件，爬虫原始数据副本）
│   ├── ai_predictions.json           # 当前 AI 预测（未开奖期号）
│   ├── predictions_history.json      # 历史预测对比（已开奖期号）
│   ├── token_usage.json              # 各模型每次调用的 token 用量统计
│   └── archive/                      # 备份归档（git 忽略）
│       ├── ai_predictions_backup_*.json
│       ├── predictions_history_backup_*.json
│       └── fetch/lottery_data_backup_*.json
├── fetch_history/                    # 数据爬取脚本
│   ├── fetch_lottery_history.py      # 爬虫脚本（同步到 data/lottery_history.json）
│   └── lottery_data.json             # 爬虫原始数据
├── doc/                              # 文档与 Prompt 模板
│   ├── AI需求文档.md                 # 原始需求文档
│   ├── prompt.md                     # Prompt 模板 v1.0（5 种基础策略）
│   └── prompt2.0.md                  # Prompt 模板 v2.0（ 5 策略，★主用）
├── .github/workflows/
│   ├── update-lottery-data.yml       # 爬虫工作流：每天 UTC 14:00（北京 22:00）
│   ├── generate-ai-prediction.yml    # AI 预测工作流：每周一三五 UTC 00:00
│   └── email-daily-digest.yml        # 邮件推送工作流：每天 UTC 00:30
├── .env.example                      # 环境变量模板
├── .env                              # 本地环境变量（git 忽略）
├── .vercelignore                     # Vercel 构建忽略
├── .gitignore                        # Git 忽略规则
├── generate_ai_prediction.py         # AI 预测自动生成脚本（主入口）
├── email_content_builder.py          # 邮件内容组装模块（纯函数）
├── email_smtp_utils.py               # SMTP 邮件发送工具（共享模块）
├── email_daily_digest.py             # 每日邮件推送主入口
├── email_push_notify.py              # Push 触发邮件通知
├── test_prediction.py                # 预测文件格式测试脚本
├── vercel.json                       # Vercel 部署配置
├── start_server.sh / .bat            # 本地开发服务器
├── AI_PREDICTION_GUIDE.md            # AI 预测自动生成指南
├── AI_Prediction_Analysis_Report.md  # 历史预测分析报告
├── DATA_UPDATE_GUIDE.md              # 数据更新指南
├── DEPLOYMENT.md                     # Vercel 部署指南
├── LICENSE                           # 许可证
└── README.md                         # 项目说明
```

---

## 前端架构

### 三个 Tab 页面

| Tab | 内容 |
|-----|------|
| **最新预测** | Hero Banner（下期期号/日期/倒计时）、策略说明、5 个模型卡片（各 4 组预测）、免责声明 |
| **图表分析** | 中奖规则卡片、4 个统计卡（数据样本/最热红球/最热蓝球/平均和值）、5 张 Chart.js 图表 |
| **历史回溯** | AI 命中表现折线图、详细命中记录卡片、历史开奖号码表格 |

### 图表（Chart.js 4.4.0，CDN 引入）

位于 `app.js`，在"图表分析"和"历史回溯"Tab 中渲染：

1. **红球热度分布**（柱状图）— 01-33 各号码出现频次
2. **蓝球出现频率**（柱状图）— 01-16 各号码出现频次
3. **奇偶比例分布**（环形图）— 红球奇偶比（0:6 ~ 6:0）
4. **红球和值走势**（折线图）— 最近 30 期和值 + 平均线
5. **区间分布统计**（柱状图）— 01-11 / 12-22 / 23-33 分布
6. **AI 命中表现趋势**（折线图）— 各模型每期最佳命中数

### 页面组件（`components.js`）

- `createLotteryBall()` — 号码球元素（红/蓝、sm/md/lg、命中高亮）
- `createModelCard()` — AI 模型卡片（含模型头部、策略行、最佳命中徽章）
- `createStrategyRow()` — 策略预测行（含命中统计）
- `createAccuracyCard()` — 历史命中记录卡片
- `createPredictionGroupRow()` — 预测组行（含红/蓝命中数）
- `createHistoryTableRow()` — 历史开奖表格行
- `compareNumbers()` — 命中计算逻辑

### 主题切换

CSS 变量实现深色/浅色模式，偏好保存至 localStorage。

### 启动方式

```bash
# Windows
start_server.bat

# macOS/Linux
./start_server.sh

# 手动
python3 -m http.server 8000
```

访问 `http://localhost:8000`。**不能直接双击 `index.html`（CORS 限制）**。

---

## 核心数据文件

### 1. `data/lottery_history.json`

```json
{
  "last_updated": "2025-10-22T20:39:53Z",
  "data": [{
    "period": "25121",
    "date": "2025-10-21",
    "red_balls": ["06", "08", "10", "25", "29", "30"],
    "blue_ball": "08"
  }],
  "next_draw": {
    "next_period": "25122",
    "next_date": "2025-10-23",
    "next_date_display": "2025年10月23日",
    "weekday": "周四",
    "draw_time": "21:15"
  }
}
```

### 2. `data/ai_predictions.json`

```json
{
  "prediction_date": "2025-10-27",
  "target_period": "25124",
  "models": [{
    "prediction_date": "2025-10-27",
    "target_period": "25124",
    "model_id": "SSB-Team-001",
    "model_name": "GPT-5",
    "predictions": [
      {
        "group_id": 1,
        "strategy": "热号追随者",
        "red_balls": ["09", "16", "17", "24", "25", "31"],
        "blue_ball": "13",
        "description": "基于5期加权频率..."
      }
    ]
  }]
}
```

### 3. `data/predictions_history.json`

```json
{
  "predictions_history": [{
    "prediction_date": "2025-10-21",
    "target_period": "25121",
    "actual_result": { "period": "25121", ... },
    "models": [{
      "model_id": "SSB-Team-001",
      "model_name": "GPT-5",
      "predictions": [{ "...", "hit_result": {
        "red_hits": ["25"],
        "red_hit_count": 1,
        "blue_hit": false,
        "total_hits": 1
      }}],
      "best_group": 2,
      "best_hit_count": 2
    }]
  }]
}
```

---

## GitHub Actions 自动化（3 个工作流）

### 1. `update-lottery-data.yml` — 爬取开奖数据
- **触发**: 每天 UTC 14:00（北京时间 22:00）+ 手动
- **执行**: `fetch_history/fetch_lottery_history.py`
- **依赖**: `requests`, `beautifulsoup4`
- **推送**: `data/lottery_history.json`, `fetch_history/lottery_data.json`

### 2. `generate-ai-prediction.yml` — 生成 AI 预测
- **触发**: 每周一三五 UTC 00:00（北京时间 08:00）+ 手动
- **执行**: `python3 generate_ai_prediction.py`
- **Secrets**: `AI_API_KEY`, `AI_BASE_URL`
- **推送**: `data/ai_predictions.json`, `data/predictions_history.json`（归档）

### 3. `email-daily-digest.yml` — 每日邮件推送
- **触发**: 每天 UTC 00:30（北京时间 08:30）+ 手动
- **执行**: `python3 email_daily_digest.py`
- **Secrets**: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_RECIPIENT`
- **注意**: 在 AI 预测生成之后运行，确保邮件含最新预测

> ⚠️ 工作流需启用写入权限：Settings > Actions > General > Workflow permissions → **Read and write permissions**

---

## 关键脚本

### `generate_ai_prediction.py` — AI 预测自动生成（主入口）

**功能**:
1. 加载 Prompt 模板（`doc/prompt2.0.md`）
2. 加载历史数据（`data/lottery_history.json`，取最近 30 期）
3. **自动归档**：检测旧预测是否已开奖 → 计算命中 → 写入 `predictions_history.json`
4. 逐个调用 5 个 AI 模型生成预测
5. 验证数据格式（4 组、6 红球已排序、蓝球非空）
6. 创建备份并保存

**模型配置**（内置）:
```python
MODELS = [
    {"id": "deepseek-v3", "name": "DeepSeek V3", "model_id": "deepseek-v3"},
    {"id": "deepseek-v3.2-exp", "name": "DeepSeek V3.2 Exp", "model_id": "deepseek-v3.2-exp"},
    {"id": "tongyi-xiaomi-analysis-pro", "name": "Tongyi Analysis Pro", "model_id": "tongyi-xiaomi-analysis-pro"},
    {"id": "Moonshot-Kimi-K2-Instruct", "name": "Kimi K2", "model_id": "Moonshot-Kimi-K2-Instruct"},
    {"id": "qwen3.7-flash-2026-07-15", "name": "Qwen 3.7 Flash (07-15)", "model_id": "qwen3.7-flash-2026-07-15"},
]
```

**环境变量**:
- `AI_API_KEY`（必填）
- `AI_BASE_URL`（可选，默认 `https://aihubmix.com/v1`）

```bash
pip install openai
python3 generate_ai_prediction.py
```

### `email_daily_digest.py` / `email_content_builder.py` — 每日邮件

`email_content_builder.py`（纯函数模块）:
- `load_data()` — 加载 3 个 JSON 数据源（独立异常隔离）
- `validate_data()` — 返回 `(errors, warnings)`
- `build_email_content()` — 渲染纯文本邮件正文（4 栏：最新开奖 / 下期预告 / AI 预测 / 命中情况）

`email_daily_digest.py`（主入口）:
- 读取环境变量（SMTP 配置）
- 加载 → 校验 → 组装 → 发送
- 支持 `EMAIL_DRY_RUN=true` 仅打印不发送

**环境变量**（详见 `.env.example`）:
```
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your-qq-number@qq.com
SMTP_PASSWORD=your-qq-auth-code
EMAIL_RECIPIENT=recipient@example.com
EMAIL_DRY_RUN=true
```

### 其他脚本

| 脚本 | 用途 |
|------|------|
| `test_prediction.py` | 验证 `ai_predictions.json` 格式 |
| `email_smtp_utils.py` | SMTP 配置/校验/发送共享模块（两个邮件脚本共用） |

---

## AI 预测策略（Prompt v2.0）

Prompt 模板位于 `doc/prompt2.0.md`，每个 AI 模型生成 4 组预测：

| 策略 | 核心逻辑 |
|------|---------|
| **热号追随者** | 多周期加权频率（5期×5 + 10期×3 + 30期×2），衰减因子，三区间平衡 |
| **平衡策略师** | 历史分布拟合，精细约束（AC 值 8-14，总和 100-120），区间分布 |
| **周期理论家** | 三周期频率交叉，趋势强度评分，周期转折点识别 |
| **综合决策者** | 加权投票（热30%+冷25%+平衡20%+周期25%），多样性保证 |

> v1.0 模板在 `doc/prompt.md`（5 种基础策略），当前生成脚本使用 v2.0。

---

## 数据更新工作流

### 自动流程（推荐）

```
开奖 (周二/四/日 21:15)
  ↓ 北京时间 22:00
[update-lottery-data.yml] 爬虫 → 更新 lottery_history.json
  ↓ 周一/三/五 北京 08:00
[generate-ai-prediction.yml] 归档旧预测 + 生成新预测
  ↓ 北京 08:30
[email-daily-digest.yml] 发送每日汇总邮件
  ↓
Vercel 自动重新部署
```

### 手动触发

1. **立即更新开奖数据**: GitHub Actions → Update Lottery Data → Run workflow
2. **手动生成预测**: `python3 generate_ai_prediction.py`
3. **测试邮件**: 设置 `EMAIL_DRY_RUN=true` 后运行 `python3 email_daily_digest.py`

### 数据更新检查清单

- [ ] `lottery_history.json` 含最新开奖
- [ ] `ai_predictions.json` 的 `target_period` 是未开奖期号
- [ ] 旧预测已归档至 `predictions_history.json` 并含 `hit_result`
- [ ] 每个模型标记了 `best_group`

---

## 环境变量配置

见 `.env.example`，所有凭证通过环境变量注入，**绝不硬编码**：

| 变量 | 用途 | 使用方 |
|------|------|--------|
| `AI_API_KEY` | AI 模型调用凭证（DeepSeek/Tongyi/Kimi） | `generate_ai_prediction.py` |
| `AI_BASE_URL` | AI API 端点（默认 aihubmix.com） | `generate_ai_prediction.py` |
| `SMTP_SERVER` | SMTP 服务器（默认 smtp.qq.com） | `email_daily_digest.py` |
| `SMTP_PORT` | SMTP 端口（默认 465） | `email_daily_digest.py` |
| `SMTP_USER` | 邮箱地址 | `email_daily_digest.py` |
| `SMTP_PASSWORD` | 邮箱授权码 | `email_daily_digest.py` |
| `EMAIL_RECIPIENT` | 收件人 | `email_daily_digest.py` |
| `EMAIL_DRY_RUN` | `true` 仅打印不发送 | `email_daily_digest.py` |

> GitHub Actions secrets 需同步配置同名字段。

---

## 部署

### Vercel（主要部署方式）

项目配置 `vercel.json`：数据文件 `max-age=0` 不缓存，含安全响应头。

```bash
npm install -g vercel
vercel login
vercel --prod      # 生产部署
```

从 GitHub 导入后每次 push 自动部署。

详细指南见 [DEPLOYMENT.md](./DEPLOYMENT.md)。

### 本地开发

```bash
# 安装 Python 依赖
pip install openai requests beautifulsoup4

# 启动服务器
./start_server.sh    # macOS/Linux
start_server.bat     # Windows
```

---

## 技术栈

- **前端**: HTML5, CSS3（CSS Variables, Grid, Flexbox）, Vanilla JS（ES6+）
- **图表**: Chart.js 4.4.0（CDN）
- **字体**: Inter（Google Fonts）
- **Python**: requests + BeautifulSoup4（爬虫）, openai（AI 调用）
- **自动化**: GitHub Actions（3 个工作流）
- **部署**: Vercel（自动部署 + CDN）
- **邮件**: smtplib（SMTP_SSL，QQ 邮箱）

---

## 文件编码与格式

- JSON 文件：UTF-8，`ensure_ascii=False`，`indent=2`
- Python 文件：UTF-8，`# -*- coding: utf-8 -*-`
- HTML/CSS/JS：UTF-8

---

## Git 规则

### 提交信息格式
- `feat:` 新功能 / `fix:` 修复 bug / `chore:` 杂项 / `docs:` 文档 / `style:` 格式

### `.gitignore` 关键规则
```
# 备份文件（本地保留，不提交）
*_backup_*.json
# Python 缓存
__pycache__/
*.py[cod]
# 本地环境变量
.env
# 系统文件
.DS_Store
```

---

## 免责声明

本项目仅供学习交流使用，不构成任何投资建议。彩票具有随机性，AI 预测仅为技术演示，不保证准确性。双色球开奖为随机事件，任何预测均无法保证命中。

---

## 相关文档索引

- [AI_PREDICTION_GUIDE.md](./AI_PREDICTION_GUIDE.md) — AI 预测自动生成详细指南
- [AI_Prediction_Analysis_Report.md](./AI_Prediction_Analysis_Report.md) — 历史预测命中率分析报告
- [DATA_UPDATE_GUIDE.md](./DATA_UPDATE_GUIDE.md) — 数据更新操作指南
- [DEPLOYMENT.md](./DEPLOYMENT.md) — Vercel 部署指南
- [README.md](./README.md) — 项目对外说明
