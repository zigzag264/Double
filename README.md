# 🎯 双色球 AI 预测

> 在线访问：[https://double-color-ball-ai.vercel.app](https://double-color-ball-ai.vercel.app)

<div align="center">

![GitHub last commit](https://img.shields.io/github/last-commit/zhens/double-color-ball?color=3b82f6)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/zhens?color=3b82f6&label=commits)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-4%20workflows-3b82f6)
![Site](https://img.shields.io/badge/deploy-Vercel-3b82f6)

</div>

基于 **6 个 AI 大模型 + 10 个统计/概率/机器学习模型** 的双色球彩票预测与数据分析展示平台。多模型预测对比、5 类 Chart.js 图表分析、历史命中率回溯，以及每日邮件推送。

> **AI 模型**: DeepSeek V3、Tongyi Analysis Pro、Kimi K2、Qwen 3.7 Flash (07-15)、DeepSeek V4 Flash、GLM 5.2
> **统计/概率/ML 模型**: 马尔可夫链、贝叶斯推断、正态分布(Z-score)、泊松分布、蒙特卡洛模拟、频率热号、遗漏回补、指数平滑(EWMA)、关联规则、集成投票（本地纯标准库计算，确定性输出，不消耗 token）

---

## 📊 实时数据

| 指标 | 当前值 |
|------|--------|
| 最新开奖 | **26091** 期 (2026-08-09) — `02 13 14 16 20 24` + `05` |
| 下期预告 | **26092** 期 · 2026年08月11日（周二）21:15 |
| 历史数据 | 152 期 |
| 预测模型数 | 15 个（5 AI + 10 统计/概率/ML） |
| 已归档预测 | 4 期（最佳单期 4 红球，平均 2.0~2.6 红球/期） |

---

## 🏗 系统架构

```
┌─ GitHub Actions ───────────────────────────────────────────────┐
│ 爬虫 (UTC 14:00) → AI 预测 (UTC 00:00) → 邮件推送 (UTC 00:30)  │
└──────────────────────────┬─────────────────────────────────────┘
                           │ git push
┌─ Git 仓库 = 数据层 ──────┴─────────────────────────────────────┐
│  lottery_history.json  │  ai_predictions.json  │  token_usage  │
│  predictions_history.json  │  archive/ 备份                     │
└──────────────────────────┬─────────────────────────────────────┘
                           │ Vercel 自动部署
┌─ 浏览器端 ───────────────┴─────────────────────────────────────┐
│  data-loader.js → components.js → app.js → 3 个 Tab 页面       │
└─────────────────────────────────────────────────────────────────┘
```

**核心设计**: 无后端服务器。Git 即数据库，GitHub Actions 定时写入 JSON，Vercel 静态托管，前端直接 fetch JSON。

---

## 📁 项目结构

```
double/
├── index.html                       # 主页面（3 个 Tab）
├── css/
│   └── style.css                    # 深色/浅色主题样式
├── js/
│   ├── data-loader.js               # 加载 4 个 JSON 数据源
│   ├── components.js                # UI 组件（号码球、卡片、命中对比）
│   └── app.js                       # 编排层（Tab 渲染、排行统计）
├── stats_models.py                  # 10 个统计/概率/ML 模型（本地、纯标准库）
├── data/                            # ★ 核心数据（版本控制）
│   ├── lottery_history.json         # 152 期历史开奖 + 下期信息
│   ├── ai_predictions.json          # 当前预测（5 AI + 10 统计 = 15 模型 × 4 组）
│   ├── predictions_history.json     # 历史预测命中记录（含 hit_result）
│   ├── token_usage.json             # 各模型 API token 用量统计
│   └── archive/                     # 备份归档（git 忽略）
├── fetch_history/                   # 爬虫模块
│   ├── fetch_lottery_history.py     # 500.com 爬虫（BeautifulSoup）
│   └── lottery_data.json            # 爬虫原始数据
├── doc/                             # Prompt 模板
│   └── prompt2.0.md                 # Prompt v2.0（4 策略，★主用）
├── .github/workflows/               # 4 个自动化工作流
├── generate_ai_prediction.py        # ★ 预测生成主入口（5 AI + 集成 10 统计模型）
├── stats_models.py                  # 10 个统计/概率/ML 模型（本地纯标准库）
├── email_content_builder.py         # 邮件 HTML 构建（纯函数模块）
├── email_smtp_utils.py              # SMTP 配置/发送（共享模块）
├── email_daily_digest.py            # 每日邮件推送
├── email_push_notify.py             # Push 触发邮件通知
├── test_prediction.py               # 预测数据格式验证
├── vercel.json                      # Vercel 部署配置
├── start_server.*                   # 本地开发启动脚本
├── .env.example                     # 环境变量模板
└── README.md                        # 本文件
```

---

## 🚀 快速开始

### 本地开发

```bash
# 启动 HTTP 服务器（必须，否则 CORS 限制会阻止加载 JSON）
start_server.bat     # Windows
./start_server.sh    # macOS/Linux
python3 -m http.server 8000    # 或手动

# 安装 Python 依赖
pip install openai requests beautifulsoup4
```

访问 `http://localhost:8000`

### 生成 AI 预测

```bash
# 设置 API 凭证
export AI_API_KEY="your-api-key"
export AI_BASE_URL="your-api-endpoint"

# 一键生成
python3 generate_ai_prediction.py
```

---

## 🤖 AI 预测引擎

### 生成流程

`generate_ai_prediction.py` 自动完成：

```
加载 Prompt 模板 (doc/prompt2.0.md)
  ↓
加载最近 30 期历史数据
  ↓
检测旧预测是否已开奖 → 计算命中 → 归档到 predictions_history.json
  ↓
依次调用 6 个 AI 模型 → 各生成 4 组预测
  ↓
后处理：去重 / 防复读 / 补齐 / 验证
  ↓
记录 token 用量 → 创建备份 → 保存
```

### 当前模型

| 模型 | ID | 类型 | 调用成本 |
|------|----|------|---------|
| **DeepSeek V3** | `deepseek-v3` | 通用 | ~500 tokens/次, ~10s |
| **Tongyi Analysis Pro** | `tongyi-xiaomi-analysis-pro` | 分析型 | ~500 tokens/次, ~12s |
| **Kimi K2** | `Moonshot-Kimi-K2-Instruct` | 通用 | ~400 tokens/次, ~15s |
| **Qwen 3.7 Flash (07-15)** | `qwen3.7-flash-2026-07-15` | 推理型 | ~5,500 tokens/次, ~30s |

所有模型通过统一 API 端点调用，共享 `AI_API_KEY`。

### 预测策略

每个模型生成 4 组预测，采用不同量化策略：

| 策略 | 核心逻辑 |
|------|---------|
| **热号追随者** | 多周期加权频率，衰减因子，三区间平衡 |
| **平衡策略师** | 历史分布拟合，AC 值 8-14，总和 100-120 |
| **周期理论家** | 三周期频率交叉，趋势强度评分，转折点识别 |
| **综合决策者** | 加权投票（热号 30%+冷号 25%+平衡 20%+周期 25%） |

> 详细 Prompt 模板见 [doc/prompt2.0.md](./doc/prompt2.0.md)

---

## 🎯 命中排行

### 历史记录

| 期号 | 模型数 | 最佳命中 | 平均命中 |
|------|--------|---------|---------|
| 26091 | 6 | 4 红球 (Kimi K2) | 2.2 球 |
| 26090 | 6 | 3 红球 (DeepSeek V3) | 2.0 球 |
| 26089 | 5 | 3 红球 (3 模型并列) | 2.6 球 |
| 26088 | 5 | 3 红球 (2 模型并列) | 2.6 球 |

### 排行榜

在前端「历史回溯」Tab 展示：

- **🏆 最新一期 Top 10** — 按命中数排序，含红球明细和蓝球命中标记
- **📊 历史累计排行** — 按模型+策略聚合，跨期累计

---

## 🔄 自动化工作流

### 时序

```
开奖 (周二/四/日 21:15)
  ↓ 北京 22:00 (UTC 14:00)
[update-lottery-data.yml] 爬虫 → 更新 lottery_history.json
  ↓ 周一/三/五 北京 08:00 (UTC 00:00)
[generate-ai-prediction.yml] 归档旧预测 + 生成新预测
  ↓ 北京 08:30 (UTC 00:30)
[email-daily-digest.yml] 发送每日汇总邮件
  ↓
Vercel 自动重新部署
```

### 工作流一览

| 工作流 | 触发 | 执行 | 手动场景 |
|--------|------|------|---------|
| **Update Lottery Data** | 每天 UTC 14:00 | 爬取最新开奖数据 | 开奖后立即更新 |
| **Generate AI Prediction** | 周一/三/五 UTC 00:00 | 调用 6 个模型生成预测 | 预测过期/新增模型 |
| **Email Daily Digest** | 每天 UTC 00:30 | 发送每日汇总邮件 | 测试邮件格式 |
| **Push Notification** | 每次 push 到 master | 发送更新摘要邮件 | 推送更新通知 |

> ⚠️ 需启用写入权限：Settings → Actions → General → Workflow permissions → **Read and write permissions**

---

## 📧 邮件推送

两种推送机制，共用 `email_content_builder.py` 统一 HTML 构建，`email_smtp_utils.py` 共享 SMTP 发送：

| 类型 | 脚本 | 触发 | 内容 |
|------|------|------|------|
| **每日汇总** | `email_daily_digest.py` | 每天 UTC 00:30 | 最新开奖 + 命中排行 + AI 预测 |
| **Push 通知** | `email_push_notify.py` | 每次 push 到 master | 每日汇总 + Git 提交信息 |

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

| 变量 | 用途 | 使用方 |
|------|------|--------|
| `AI_API_KEY` | AI 模型调用凭证 | `generate_ai_prediction.py` |
| `AI_BASE_URL` | AI API 端点 | `generate_ai_prediction.py` |
| `SMTP_SERVER` | SMTP 服务器（默认 `smtp.qq.com`） | 邮件脚本 |
| `SMTP_PORT` | SMTP 端口（默认 `465`） | 邮件脚本 |
| `SMTP_USER` | 邮箱地址 | 邮件脚本 |
| `SMTP_PASSWORD` | 邮箱授权码 | 邮件脚本 |
| `EMAIL_RECIPIENT` | 收件人邮箱 | 邮件脚本 |
| `EMAIL_DRY_RUN` | `true` 仅打印不发送 | 邮件脚本 |

> GitHub Actions Secrets 需同步配置同名字段。

---

## 🌐 部署

### Vercel（推荐）

项目已配置 `vercel.json`，数据文件 `max-age=0` 不缓存，含安全响应头。

```bash
npm install -g vercel
vercel login
vercel --prod
```

从 GitHub 导入后每次 push 自动部署。

---

## 🛠 技术栈

| 层 | 技术 |
|----|------|
| **前端** | HTML5, CSS3 (CSS Variables, Grid, Flexbox), Vanilla JS (ES6+) |
| **图表** | 统计卡片 + 排行表格 |
| **AI 调用** | OpenAI API 兼容格式 |
| **爬虫** | Python requests + BeautifulSoup4 |
| **自动化** | GitHub Actions (4 个工作流) |
| **部署** | Vercel (自动部署 + CDN) |
| **邮件** | smtplib (SMTP_SSL, QQ 邮箱) |

---

## 📚 文档索引

| 文档 | 内容 |
|------|------|
| [doc/prompt2.0.md](./doc/prompt2.0.md) | Prompt 模板 v2.0（4 策略，主用） |

---

## ⚠️ 免责声明

本项目仅供学习交流使用，不构成任何投资建议。彩票具有随机性，AI 预测仅为技术演示，不保证准确性。双色球开奖为随机事件，任何预测均无法保证命中。