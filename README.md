# 🎯 双色球 AI 预测

> 在线访问：[https://double-color-ball-ai.vercel.app](https://double-color-ball-ai.vercel.app)

<div align="center">

![GitHub last commit](https://img.shields.io/github/last-commit/zhens/double-color-ball?color=3b82f6)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/zhens?color=3b82f6&label=commits)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-3%20workflows-3b82f6)
![Site](https://img.shields.io/badge/deploy-Vercel-3b82f6)

</div>

基于 **4 个 AI 大模型** 的双色球彩票预测与数据分析展示平台，提供多模型预测对比、5 类 Chart.js 图表分析、历史命中率回溯，以及每日邮件推送。

---

## 📊 实时数据

| 指标 | 数据 |
|------|------|
| 最新开奖 | **26090** 期 (2026-08-06) — `02 04 15 23 25 27` + `03` |
| 下期预告 | **26091** 期 · 2026-08-09（周日）21:15 |
| 历史数据 | 151 期 |
| AI 模型数 | 4 个 |
| 已归档预测 | 3 期 (平均命中 2.1~2.6 红球/期，最佳 3 红球) |

---

## ✨ 核心特性

- 🤖 **多 AI 模型预测** — 4 个前沿大模型（DeepSeek / Kimi / Tongyi 等）各用 4 种策略生成 4 组预测，结果对比展示
- 📊 **图表分析** — 5 类 Chart.js 图表：红球热度分布、蓝球频率、奇偶比例、和值走势、区间分布
- 🎯 **命中排行** — 最新一期 Top 10 + 历史累计排行，按模型+策略聚合，红球/蓝球命中明细
- 📋 **历史回溯** — 所有已开奖期号的 AI 预测命中记录，折叠式开奖号码表
- ⏰ **自动数据更新** — GitHub Actions 每天爬取开奖数据 + 每周一三五生成 AI 预测
- 📧 **每日邮件推送** — 自动发送 HTML 格式汇总邮件，含最新开奖 / AI 预测 / 命中排行
- 🔔 **Push 通知** — 代码推送后自动发送更新摘要邮件
- 🎨 **深色/浅色主题** — CSS 变量实现，偏好保存至 localStorage

---

## 🏗 项目结构

```
double/
├── index.html                       # 主页面（3 个 Tab）
├── css/
│   └── style.css                    # 完整样式（深色/浅色 CSS 变量）
├── js/
│   ├── app.js                       # 主应用逻辑 + Chart.js 图表渲染
│   ├── components.js                # UI 组件（号码球、卡片、对比）
│   └── data-loader.js               # 数据加载模块（fetch JSON）
├── data/                            # 前端数据文件
│   ├── lottery_history.json         # 历史开奖数据 + 下期预告
│   ├── ai_predictions.json          # 当前 AI 预测（未开奖期号）
│   └── predictions_history.json     # 历史预测对比（已开奖期号，含命中）
├── fetch_history/                   # 数据爬取
│   ├── fetch_lottery_history.py     # 爬虫脚本
│   └── lottery_data.json            # 爬虫原始数据
├── doc/                             # 文档与 Prompt 模板
│   ├── prompt.md                    # Prompt v1.0（5 种基础策略）
│   └── prompt2.0.md                 # Prompt v2.0（4 策略，★主用）
├── .github/workflows/               # CI/CD 工作流
│   ├── update-lottery-data.yml      # 爬虫：每天 UTC 14:00
│   ├── generate-ai-prediction.yml   # AI 预测：每周一三五 UTC 00:00
│   ├── email-daily-digest.yml       # 邮件推送：每天 UTC 00:30
│   └── push-notify.yml              # Push 通知：每次 push 到 master
├── generate_ai_prediction.py        # AI 预测自动生成（★ 主入口）
├── email_content_builder.py         # 邮件内容组装（纯函数模块）
├── email_daily_digest.py            # 每日邮件推送（主入口）
├── email_push_notify.py             # Push 触发邮件通知
├── test_prediction.py               # 预测文件格式测试
├── test_single_model.py             # 单模型 API 调用测试
├── diagnose.js                      # 前端命中逻辑调试
├── deploy.sh / start_server.*       # 部署与本地开发启动脚本
├── vercel.json                      # Vercel 部署配置
├── AI_PREDICTION_GUIDE.md           # AI 预测自动生成指南
├── AI_Prediction_Analysis_Report.md # 历史预测分析报告
├── DATA_UPDATE_GUIDE.md             # 数据更新操作指南
├── DEPLOYMENT.md                    # 部署指南
├── LICENSE                          # 许可证
└── README.md                        # 本文件
```

---

## 🚀 快速开始

### 本地启动

```bash
# Windows
start_server.bat

# macOS/Linux
./start_server.sh

# 或手动
python3 -m http.server 8000
```

访问 `http://localhost:8000`

> ⚠️ **不能直接双击 `index.html`** — 浏览器 CORS 限制会阻止加载本地 JSON 文件，必须通过 HTTP 服务器访问。

### 安装 Python 依赖

```bash
pip install openai requests beautifulsoup4
```

---

## 🤖 AI 预测生成

### 一键生成

```bash
# 设置环境变量
export AI_API_KEY="your-api-key"
export AI_BASE_URL="your-api-endpoint"

# 运行
python3 generate_ai_prediction.py
```

脚本自动完成：
1. 加载 Prompt 模板（`doc/prompt2.0.md`）
2. 读取最近 30 期历史数据作为上下文
3. **自动归档** — 检测旧预测是否已开奖 → 计算命中 → 写入 `predictions_history.json`
4. 依次调用 4 个 AI 模型，各生成 4 组预测
5. 自动验证：6 红球已排序、蓝球非空、4 组无重复、无 5+ 红球重合
6. 创建备份并保存

### 模型配置

当前配置 4 个模型（`generate_ai_prediction.py` 的 `MODELS` 数组），支持任意兼容 OpenAI 格式的模型：

| 模型 | ID | 说明 |
|------|----|------|
| DeepSeek V3 | `deepseek-v3` | 通用推理 |
| DeepSeek V3.2 Exp | `deepseek-v3.2-exp` | 实验版推理 |
| Tongyi Analysis Pro | `tongyi-xiaomi-analysis-pro` | 通义分析版 |
| Kimi K2 | `Moonshot-Kimi-K2-Instruct` | Moonshot K2 |

### 预测策略（4 种，v2.0）

每个模型生成 4 组预测，分别采用不同的量化策略：

| 策略 | 核心逻辑 |
|------|---------|
| **热号追随者** | 多周期加权频率（5期×5 + 10期×3 + 30期×2），衰减因子，三区间平衡 |
| **平衡策略师** | 历史分布拟合，精细约束（AC 值 8-14，总和 100-120），区间分布 |
| **周期理论家** | 三周期频率交叉，趋势强度评分，周期转折点识别 |
| **综合决策者** | 加权投票（热30%+冷25%+平衡20%+周期25%），多样性保证 |

> 详细 Prompt 模板见 [doc/prompt2.0.md](./doc/prompt2.0.md)

---

## 🎯 命中排行

在「历史回溯」Tab 中展示，包含：

- **🏆 最新一期 Top 10** — 本期命中数从高到低排序，含命中红球明细和蓝球命中标记
- **📊 历史累计排行** — 跨期累计，按累计红球 → 累计蓝球排序，含最佳单期记录

每个条目按 **模型 + 策略** 聚合，展示红球命中明细和蓝球是否命中。

---

## 🔄 数据更新工作流

### 自动流程

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

在 GitHub Actions 页面点击对应工作流的 **Run workflow**：

| 工作流 | 触发时机 | 手动场景 |
|--------|---------|---------|
| Update Lottery Data | 每天 UTC 14:00 | 开奖后立即更新 |
| Generate AI Prediction | 周一/三/五 UTC 00:00 | 预测过期或新增模型 |
| Email Daily Digest | 每天 UTC 00:30 | 测试邮件格式 |
| Push Notification | 每次 push | 推送更新摘要 |

---

## 📧 邮件推送

系统包含两种邮件推送机制：

### 1. 每日汇总邮件（`email_daily_digest.py`）

每天 08:30 自动发送 HTML 格式邮件，包含：
- 🏆 最新开奖号码
- 📊 命中排行 Top 10（最新一期 + 历史累计）
- 🔮 AI 全部预测（4 个模型 × 4 组）

### 2. Push 通知邮件（`email_push_notify.py`）

每次 push 到 master 时自动发送，额外包含 Git 提交信息。

### 配置

```bash
# SMTP 配置（详见 .env.example）
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your-qq-number@qq.com
SMTP_PASSWORD=your-qq-auth-code
EMAIL_RECIPIENT=recipient@example.com

# 测试（仅打印不发送）
EMAIL_DRY_RUN=true python3 email_daily_digest.py
```

---

## ⚙️ 环境变量

所有凭证通过环境变量注入，绝不硬编码。详见 [.env.example](./.env.example)：

| 变量 | 用途 | 使用方 |
|------|------|--------|
| `AI_API_KEY` | AI 模型调用凭证 | `generate_ai_prediction.py` |
| `AI_BASE_URL` | AI API 端点（默认 `https://aihubmix.com/v1`） | `generate_ai_prediction.py` |
| `SMTP_SERVER` | SMTP 服务器（默认 `smtp.qq.com`） | 邮件脚本 |
| `SMTP_PORT` | SMTP 端口（默认 `465`） | 邮件脚本 |
| `SMTP_USER` | 邮箱地址 | 邮件脚本 |
| `SMTP_PASSWORD` | 邮箱授权码（非登录密码） | 邮件脚本 |
| `EMAIL_RECIPIENT` | 收件人邮箱 | 邮件脚本 |
| `EMAIL_DRY_RUN` | `true` 仅打印不发送 | 邮件脚本 |

> GitHub Actions Secrets 需同步配置同名字段，工作流会自动读取。

---

## 🌐 部署

### Vercel（推荐）

项目已配置 `vercel.json`，数据文件 `max-age=0` 不缓存，含安全响应头。

```bash
npm install -g vercel
vercel login
vercel --prod
```

从 GitHub 导入后每次 push 自动部署。详细指南见 [DEPLOYMENT.md](./DEPLOYMENT.md)。

### 本地开发

```bash
# 启动 HTTP 服务器
./start_server.sh    # macOS/Linux
start_server.bat     # Windows
```

---

## 🛠 技术栈

| 层 | 技术 |
|----|------|
| **前端** | HTML5, CSS3 (CSS Variables, Grid, Flexbox), Vanilla JS (ES6+) |
| **图表** | Chart.js 4.4.0 (CDN) — 5 类图表 |
| **字体** | Inter (Google Fonts) |
| **AI 调用** | OpenAI API 兼容格式 |
| **爬虫** | Python requests + BeautifulSoup4 |
| **自动化** | GitHub Actions (4 个工作流) |
| **部署** | Vercel (自动部署 + CDN) |
| **邮件** | smtplib (SMTP_SSL, QQ 邮箱) |

---

## 📚 相关文档

| 文档 | 内容 |
|------|------|
| [AI_PREDICTION_GUIDE.md](./AI_PREDICTION_GUIDE.md) | AI 预测自动生成详细指南 |
| [AI_Prediction_Analysis_Report.md](./AI_Prediction_Analysis_Report.md) | 历史预测命中率分析报告 |
| [DATA_UPDATE_GUIDE.md](./DATA_UPDATE_GUIDE.md) | 数据更新操作指南 |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Vercel 部署指南 |
| [doc/prompt2.0.md](./doc/prompt2.0.md) | AI 预测 Prompt 模板（4 策略，主用） |
| [doc/prompt.md](./doc/prompt.md) | AI 预测 Prompt 模板 v1.0（5 策略） |

---

## ⚠️ 免责声明

本项目仅供学习交流使用，不构成任何投资建议。彩票具有随机性，AI 预测仅为技术演示，不保证准确性。双色球开奖为随机事件，任何预测均无法保证命中。