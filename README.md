# 🎯 双色球 模型预测

> 在线访问：[https://double-color-ball-ai.vercel.app](https://double-color-ball-ai.vercel.app)

<div align="center">

![GitHub last commit](https://img.shields.io/github/last-commit/zhens/double-color-ball?color=3b82f6)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/zhens?color=3b82f6&label=commits)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-4%20workflows-3b82f6)
![Site](https://img.shields.io/badge/deploy-Vercel-3b82f6)

</div>

基于 **10 个统计/概率/机器学习模型** 的双色球彩票预测与数据分析展示平台。多模型预测对比、历史命中率回溯、模型排行，以及每日邮件推送。

> **统计/概率/ML 模型**: 马尔可夫链、贝叶斯推断、正态分布(Z-score)、泊松分布、蒙特卡洛模拟、频率热号、遗漏回补、指数平滑(EWMA)、关联规则、集成投票（本地纯标准库计算，确定性输出，不调用 API、不消耗 token）

---

## 📊 实时数据

| 指标 | 当前值 |
|------|--------|
| 最新开奖 | **26095** 期 (2026-08-18) — `04 06 14 21 22 33` + `16` |
| 下期预告 | **26096** 期 · 2026年08月20日（周四）21:15 |
| 历史数据 | 156 期 |
| 预测模型数 | 10 个统计/概率/ML 模型 |
| 已归档预测 | 7 期 |

---

## 🏗 系统架构

### 架构概览

```
┌─ GitHub Actions ───────────────────────────────────────────────────┐
│ 爬虫 (UTC 14:00) → 预测 (UTC 00:00) → 邮件推送 (UTC 00:30)         │
│                              │ git push                            │
└──────────────────────────────┼─────────────────────────────────────┘
                               ▼
┌─ Git 仓库 = 数据层 ──────────┼─────────────────────────────────────┐
│  data/ 目录下 3 个 JSON 文件 + archive/ 备份                       │
│  (紧凑格式，JSON 即数据库)                                          │
└──────────────────────────────┼─────────────────────────────────────┘
                               ▼
┌─ Vercel (静态托管) ──────────┼─────────────────────────────────────┐
│ 每次 push 自动部署，数据文件 max-age=0 不缓存                        │
└──────────────────────────────┼─────────────────────────────────────┘
                               ▼
┌─ 浏览器端 ───────────────────┼─────────────────────────────────────┐
│  首屏 (Tab1)                  │  懒加载 (Tab2/Tab3)                 │
│  lottery_history.json         │  predictions_history.json          │
│  ai_predictions.json          │                                    │
│         ↓                     │         ↓                          │
│  data-loader.js ─→ components.js ─→ app.js ─→ 3 个 Tab 页面       │
└────────────────────────────────────────────────────────────────────┘
```

**核心设计**: 无后端服务器。**Git 即数据库**，GitHub Actions 定时写入 JSON，Vercel 静态托管，前端直接 fetch JSON。

### 本地开发服务器

除 `python -m http.server` 外，项目提供 `server.py`（端口 **8080**），额外提供一键更新 API：

```bash
python server.py
# POST /api/update — 自动执行爬虫 + 统计模型预测，返回最新全部数据
```

---

## 📁 项目结构

```
double/
├── index.html                        # 主页面（3 个 Tab）
├── css/
│   └── style.css                     # 样式（CSS 变量，清新简约淡彩设计）
├── js/
│   ├── data-loader.js                # 数据加载模块（fetch JSON，缓存清除）
│   ├── components.js                 # UI 组件（号码球、模型卡片、命中对比）
│   └── app.js                        # 编排层（Tab 渲染、排行统计、懒加载）
├── data/                             # ★ 核心数据（版本控制，紧凑格式 JSON）
│   ├── lottery_history.json          # 历史开奖 + 下期信息
│   ├── ai_predictions.json           # 当前预测（10 统计模型 × 4 组）
│   ├── predictions_history.json      # 历史预测命中记录（含 hit_result）
│   └── archive/                      # 备份归档（git 忽略，保留最近 10 份）
│       ├── ai_predictions_backup_*.json
│       └── predictions_history_backup_*.json
├── fetch_history/                    # 爬虫模块
│   ├── fetch_lottery_history.py      # 500.com 爬虫（BeautifulSoup）
│   └── lottery_data.json             # 爬虫原始数据
├── .github/workflows/                # 4 个自动化工作流
│   ├── update-lottery-data.yml       # 爬虫：每天 UTC 14:00
│   ├── generate-prediction.yml       # 预测：每周一三五 UTC 00:00
│   ├── email-daily-digest.yml        # 邮件推送：每天 UTC 00:30
│   └── push-notify.yml               # Push 事件邮件通知
├── server.py                         # 本地开发服务器（端口 8080，含 /api/update）
├── generate_ai_prediction.py         # ★ 预测生成主入口（集成 10 统计模型）
├── stats_models.py                   # 10 个统计/概率/ML 模型（纯标准库，确定性）
├── email_content_builder.py          # 邮件 HTML 构建（纯函数模块）
├── email_smtp_utils.py               # SMTP 配置/发送（共享模块）
├── email_daily_digest.py             # 每日邮件推送主入口
├── email_push_notify.py              # Push 触发邮件通知
├── test_prediction.py                # 预测数据格式验证
├── vercel.json                       # Vercel 部署配置
├── start_server.*                    # 本地开发启动脚本
├── .env.example                      # 环境变量模板
├── .gitignore                        # Git 忽略规则
├── LICENSE                           # 许可证
└── README.md                         # 本文件
```

---

## 🚀 快速开始

### 本地开发

```bash
# 选项 A：使用本地开发服务器（推荐，含 /api/update 一键更新）
python server.py

# 选项 B：简单 HTTP 服务器（仅静态文件，必须，否则 CORS 阻止加载 JSON）
start_server.bat     # Windows
./start_server.sh    # macOS/Linux
python3 -m http.server 8000
```

访问 `http://localhost:8000`（或 `http://localhost:8080`）

### 生成预测

```bash
# 安装 Python 依赖（爬虫用；预测仅用标准库，无需额外依赖）
pip install requests beautifulsoup4

# 一键生成（10 个统计模型本地计算，不调用 API）
python3 generate_ai_prediction.py
```

---

## 🔄 数据流与自动化

### 完整数据流程

```
               ┌──────────────┐
               │  500.com 开奖 │
               └──────┬───────┘
                      │ 爬虫抓取
                      ▼
           ┌──────────────────────┐
           │ fetch_lottery_history.py │
           └──────────┬───────────┘
                      │ 写入 JSON
                      ▼
           ┌──────────────────────┐
           │ lottery_history.json │ ◄── 历史开奖数据
           └──────────┬───────────┘
                      │ 预测脚本读取全部历史
                      ▼
           ┌──────────────────────┐
           │ generate_ai_prediction.py │
           │                      │
           │  1. 归档旧预测 → 计算命中 → predictions_history.json
           │  2. 调用 10 个统计模型（本地计算，0 token 消耗）
           │  3. 去重 / 防复读 / 格式校验
           │  4. 输出 ai_predictions.json
           └──────────┬───────────┘
                      │ git push
                      ▼
           ┌──────────────────────┐
           │  Vercel 自动部署     │
           └──────────┬───────────┘
                      │ 浏览器 fetch JSON
                      ▼
           ┌─────────────────────────────────────────────┐
           │  前端 3 个 Tab                              │
           │  ┌──────────────────────────────────────┐   │
           │  │ Tab1 最新预测（首屏加载）              │   │
           │  │  Hero Banner + 10 模型卡片 × 4 组预测 │   │
           │  └──────────────────────────────────────┘   │
           │  ┌──────────────────────────────────────┐   │
           │  │ Tab2 历史分析（懒加载）                │   │
           │  │  统计卡片 + 开奖号码表 + 命中记录摘要   │   │
           │  └──────────────────────────────────────┘   │
           │  ┌──────────────────────────────────────┐   │
           │  │ Tab3 模型排行（懒加载）                │   │
           │  │  命中率排行 + 模型分组统计             │   │
           │  └──────────────────────────────────────┘   │
           └─────────────────────────────────────────────┘
```

### 数据优化

- **JSON 紧凑格式**: 所有落盘数据文件使用 `separators=(',',':')` 无缩进序列化，较 `indent=2` 减小 **30%~54%** 体积，节省 git 存储与传输带宽
- **数据懒加载**: 首屏只拉取 `lottery_history.json` + `ai_predictions.json`（Tab1 所需）；进入 Tab2/Tab3 时由 `loadSecondaryData()` 并发拉取 `predictions_history.json`（并发去重，仅拉一次）

### 自动时序

```
开奖 (周二/四/日 21:15)
  ↓ 北京 22:00 (UTC 14:00)
[爬虫] 更新 lottery_history.json
  ↓ 周一/三/五 北京 08:00 (UTC 00:00)
[预测] 归档旧预测 + 生成新预测
  ↓ 北京 08:30 (UTC 00:30)
[邮件推送] 发送每日汇总邮件
  ↓
Vercel 自动重新部署
```

### 手动触发

1. **立即更新开奖数据**: GitHub Actions → Update Lottery Data → Run workflow
2. **手动生成预测**: `python3 generate_ai_prediction.py`
3. **一键更新（本地）**: `curl -X POST http://localhost:8080/api/update`
4. **测试邮件**: `EMAIL_DRY_RUN=true python3 email_daily_digest.py`

---

## 🤖 统计/概率/ML 模型引擎（10 个，本地计算）

所有模型基于全部历史开奖数据本地计算，**不调用 API、不消耗 token**，仅依赖 Python 标准库（`random/math/statistics/itertools`）：

| model_id | 模型 | 类型 | 核心算法 |
|---------|------|------|---------|
| `markov-chain` | 马尔可夫链 | 概率 | 相邻期红→红转移矩阵 + 平稳分布 |
| `bayesian` | 贝叶斯推断 | 概率 | Beta 收缩估计（先验×近期似然） |
| `normal-distribution` | 正态分布(Z-score) | 统计 | 近期 vs 全史的标准化偏离 + 和值正态约束 |
| `poisson` | 泊松分布 | 概率 | 出现次数 ~ Poisson(λ)，P(出现)≈1−e^{−λ} |
| `monte-carlo` | 蒙特卡洛模拟 | 概率 | 加权随机抽样 1 万次 + 约束筛选，固定种子 |
| `frequency-hot` | 频率热号 | 统计 | 5/10/30 期多窗口加权频率 |
| `cold-miss` | 遗漏回补 | 统计 | 当前遗漏 vs 平均遗漏（冷号回补） |
| `ewma` | 指数平滑(EWMA) | 统计 | 0/1 序列指数加权，不同 α |
| `apriori` | 关联规则 | ML | 红球共现置信度 / 提升度 |
| `ensemble` | 集成投票 | ML | 前 9 模型评分均值/中位数/去极值融合 |

每个模型输出 4 组参数变体预测，结构与策略覆盖统计、概率、机器学习三大类。

---

## 🎛 前端架构

### 三个 Tab 页面

| Tab | 数据加载 | 内容 |
|-----|---------|------|
| **最新预测** | 首屏加载 | Hero Banner（下期期号/日期/倒计时）、统计模型卡片（共 10 个，各 4 组预测）、免责声明 |
| **历史分析** | 懒加载 | 4 个统计卡（数据样本/最热红球/最热蓝球/平均和值）、历史开奖号码表格、命中记录紧凑摘要 |
| **模型排行** | 懒加载 | 模型命中率排行（最新一期/最近一月/最近一年）、模型分组统计 |

### 核心组件（`components.js`）

- `createLotteryBall()` — 号码球元素（红/蓝、sm/md/lg、命中高亮）
- `createModelCard()` — 模型卡片（含模型头部、策略行、最佳命中徽章）
- `createStrategyRow()` — 策略预测行（含命中统计）
- `createAccuracySummaryRow()` — 命中记录紧凑摘要行（期号 + 开奖号码 + 最佳命中）
- `createHistoryTableRow()` — 历史开奖表格行
- `compareNumbers()` — 命中计算逻辑

### 视觉风格

清新简约：白底 + 细边框 + 轻阴影；10 个模型各配一个低饱和度淡彩头部（`--tint-*` CSS 变量），便于分类辨识，整体大量留白。

---

## 📧 邮件推送

两种推送机制，共用 `email_content_builder.py` 统一 HTML 构建，`email_smtp_utils.py` 共享配置加载/校验/发送（含 `send_digest` 编排封装，消除重复逻辑）：

| 类型 | 脚本 | 触发 | 内容 |
|------|------|------|------|
| **每日汇总** | `email_daily_digest.py` | 每天 UTC 00:30 | 最新开奖 + 命中排行 + 模型预测 |
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
| **预测引擎** | Python 标准库（random/math/statistics/itertools），纯本地计算 |
| **爬虫** | Python requests + BeautifulSoup4（500.com） |
| **自动化** | GitHub Actions（4 个工作流：爬虫/预测/邮件/Push） |
| **部署** | Vercel（自动部署 + CDN，数据文件不缓存） |
| **邮件** | smtplib（SMTP_SSL，QQ 邮箱） |
| **数据格式** | 紧凑 JSON（`separators=(',',':')`，体积缩小 30~54%） |

---

## 📚 文档索引

| 文档 | 内容 |
|------|------|
| [.claude/CLAUDE.md](./.claude/CLAUDE.md) | 项目内部维护说明（数据结构、脚本详情、Git 规则） |

---

## ⚠️ 免责声明

本项目仅供学习交流使用，不构成任何投资建议。彩票具有随机性，预测仅为技术演示，不保证准确性。双色球开奖为随机事件，任何预测均无法保证命中。
