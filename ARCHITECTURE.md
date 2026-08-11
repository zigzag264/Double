# 双色球 AI 预测系统 — 架构文档

> 完整的系统架构、数据流、组件关系与部署拓扑

---

## 一、系统总览

```
┌─────────────────────────────────────────────────────────────────┐
│                       GitHub Actions 层                          │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │更新开奖数据      │  │生成 AI 预测      │  │邮件推送          │ │
│  │每天 UTC 14:00   │  │每周一三五 UTC 0:00│  │每天 UTC 0:30+10:00│ │
│  └────────┬────────┘  └────────┬─────────┘  └────────┬────────┘ │
└───────────┼─────────────────────┼──────────────────────┼─────────┘
            │                     │                      │
            ▼                     ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Git 仓库 = 数据层                          │
│  ┌──────────────────┐  ┌────────────────┐  ┌──────────────────┐ │
│  │lottery_history   │  │ai_predictions  │  │predictions_history│ │
│  │.json (开奖数据)  │  │.json (当期预测) │  │.json (历史命中)   │ │
│  └──────────────────┘  └────────────────┘  └──────────────────┘ │
│  ┌──────────────────┐  ┌────────────────┐                        │
│  │token_usage.json  │  │archive/ (备份)  │                        │
│  │(API 用量统计)    │  │                │                        │
│  └──────────────────┘  └────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
            │
            │ git push → Vercel 自动部署
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Vercel CDN 层                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │index.html    │  │css/style.css │  │js/*.js       │           │
│  │(SPA 入口)    │  │(样式)        │  │(前端逻辑)    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│  vercel.json: data/* max-age=0 不缓存                            │
└─────────────────────────────────────────────────────────────────┘
            │
            │ 浏览器 fetch JSON
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      浏览器端                                    │
│  data-loader.js → components.js → app.js → DOM 渲染              │
└─────────────────────────────────────────────────────────────────┘
```

**核心设计思想**: 没有后端服务器。Git 仓库本身就是数据库，GitHub Actions 定时写入 JSON，Vercel 静态托管，前端直接 fetch JSON 文件。

---

## 二、项目目录结构

```
double/
├── index.html                        # SPA 入口，3 个 Tab
├── css/
│   └── style.css                     # 全部样式（CSS 变量，深色/浅色主题）
├── js/
│   ├── data-loader.js                # 数据加载层（fetch 4 个 JSON 源）
│   ├── components.js                 # UI 组件层（纯 DOM 构建函数）
│   └── app.js                        # 编排层（数据加载 → 渲染 → 事件绑定）
├── data/                             # ★ 核心数据文件（版本控制）
│   ├── lottery_history.json          # 历史开奖数据 + 下期信息
│   ├── ai_predictions.json           # 当期 AI 预测（未开奖期号）
│   ├── predictions_history.json      # 历史预测命中记录
│   ├── token_usage.json              # API token 用量统计
│   └── archive/                      # 备份归档（gitignore）
├── fetch_history/                    # 爬虫模块
│   ├── fetch_lottery_history.py      # 500.com 爬虫
│   └── lottery_data.json             # 爬虫原始数据
├── doc/                              # Prompt 模板
│   ├── prompt.md                     # v1.0（5 策略，旧版）
│   └── prompt2.0.md                  # v2.0（4 策略，★ 当前使用）
├── generate_ai_prediction.py         # ★ AI 预测生成主入口
├── email_content_builder.py          # 邮件内容组装（纯函数模块）
├── email_daily_digest.py             # 每日邮件推送
├── email_push_notify.py              # Push 触发邮件推送
├── test_prediction.py                # 预测数据格式验证
├── add_gpt5_prediction.py            # 历史预测手动回填
├── test_single_model.py              # 单模型 API 调试
├── diagnose.js                       # 前端命中逻辑模拟
├── vercel.json                       # Vercel 部署配置
├── deploy.sh                         # Vercel CLI 部署辅助
├── start_server.sh / .bat            # 本地开发服务器
├── .github/workflows/                # 4 个 GitHub Actions 工作流
│   ├── update-lottery-data.yml
│   ├── generate-ai-prediction.yml
│   ├── email-daily-digest.yml
│   └── push-notify.yml
├── .env.example                      # 环境变量模板
├── .gitignore
└── *.md                              # 文档
```

---

## 三、数据流详解

### 3.1 完整数据生命周期

```
开奖 (周二/四/日 21:15 北京)
  │
  ▼ 北京 22:00 (UTC 14:00)
[update-lottery-data.yml] ──运行──► fetch_lottery_history.py
  │                                      │
  │                                      ▼ 爬取 500.com
  │                               fetch_history/lottery_data.json
  │                                      │
  │                                      ▼ 格式化同步
  │                               data/lottery_history.json
  │
  ▼ 北京 08:00 (UTC 00:00) 周一/三/五
[generate-ai-prediction.yml] ──运行──► generate_ai_prediction.py
  │                                      │
  │                               ┌──────┴──────┐
  │                               │ 步骤 1: 归档 │ ← 检测旧预测是否已开奖
  │                               │              │    计算命中 → 写入历史
  │                               ├──────────────┤
  │                               │ 步骤 2: 生成 │ ← 调用 4 个 AI 模型
  │                               │              │    每组 4 个策略预测
  │                               ├──────────────┤
  │                               │ 步骤 3: 后处理│ ← 去重、防复读、补齐 4 组
  │                               ├──────────────┤
  │                               │ 步骤 4: 记录 │ ← token 用量 → token_usage.json
  │                               └──────┬──────┘
  │                                      ▼
  │                               data/ai_predictions.json  (新预测)
  │                               data/predictions_history.json (追加)
  │                               data/token_usage.json (追加)
  │
  ▼ 北京 08:30 & 18:00 (UTC 00:30 & 10:00)
[email-daily-digest.yml] ──运行──► email_daily_digest.py
  │                                      │
  │                                      ▼ 读取 4 个 JSON
  │                               email_content_builder.py
  │                                      │
  │                                      ▼ 组装 HTML 邮件
  │                               SMTP_SSL → QQ 邮箱
  │
  ▼ 每次 git push
Vercel 自动部署 → 浏览器访问 → fetch JSON → 渲染
```

### 3.2 数据文件依赖关系

```
lottery_history.json
  ├── 被 generate_ai_prediction.py 读取（最近 30 期）
  ├── 被 email_content_builder.py 读取
  └── 被前端 data-loader.js 加载

ai_predictions.json
  ├── 被 generate_ai_prediction.py 写入/归档
  ├── 被 test_prediction.py 验证
  ├── 被 email_content_builder.py 读取
  └── 被前端 data-loader.js 加载

predictions_history.json
  ├── 被 generate_ai_prediction.py 追加写入
  ├── 被 email_content_builder.py 读取
  └── 被前端 data-loader.js 加载

token_usage.json
  ├── 被 generate_ai_prediction.py 追加写入
  └── 被前端 data-loader.js 加载
```

---

## 四、Python 脚本层

### 4.1 依赖关系图

```
┌──────────────────────────────────────────────┐
│              generate_ai_prediction.py        │
│  (独立运行，无 import 其他模块)                 │
│  reads: doc/prompt2.0.md, data/lottery_*.json │
│  writes: data/ai_predictions.json             │
│          data/predictions_history.json        │
│          data/token_usage.json                │
│  calls: OpenAI API × 4 个模型                  │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│              email_content_builder.py         │
│  (纯函数模块，被下面两个脚本 import)             │
│  exports: load_data(), validate_data(),       │
│           build_html_digest(), ...            │
└──────────────┬───────────────────────────────┘
               │
      ┌────────┴────────┐
      ▼                  ▼
┌─────────────┐  ┌──────────────┐
│email_daily_ │  │email_push_   │
│digest.py    │  │notify.py     │
│(schedule)   │  │(on push)     │
└─────────────┘  └──────────────┘

┌──────────────────────────────────────────────┐
│              fetch_lottery_history.py         │
│  (独立运行，无 import 其他模块)                 │
│  dependencies: requests, beautifulsoup4      │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│              test_prediction.py               │
│  (独立运行，读 ai_predictions.json 验证格式)   │
└──────────────────────────────────────────────┘
```

### 4.2 `generate_ai_prediction.py` 内部流程

```
main()
  │
  ├── 1. 加载配置
  │     ├── 读取环境变量 AI_API_KEY, AI_BASE_URL
  │     ├── 定义 MODELS 列表（4 个模型）
  │     └── 加载 doc/prompt2.0.md 模板
  │
  ├── 2. 加载历史数据
  │     ├── 读取 lottery_history.json
  │     └── 取最近 30 期 + 下期信息
  │
  ├── 3. 归档旧预测（如果已开奖）
  │     ├── 读取 ai_predictions.json
  │     ├── 对比实际开奖号码
  │     ├── 计算每组命中（red_hits, blue_hit, total_hits）
  │     ├── 标记 best_group / best_hit_count
  │     └── 追加到 predictions_history.json
  │
  ├── 4. 生成新预测（循环 4 个模型）
  │     ├── 构建 prompt（模板 + 历史数据）
  │     ├── 调用 AI API（streaming + 重试）
  │     ├── 解析 JSON 响应
  │     ├── 后处理：去重、防复读、补齐 4 组
  │     └── 记录 token 用量
  │
  ├── 5. 验证与保存
  │     ├── 验证格式（4 组、6 红球、排序、蓝球非空）
  │     ├── 备份旧文件 → data/archive/
  │     └── 写入 ai_predictions.json
  │
  └── 6. 保存 token 用量
        └── 追加到 token_usage.json
```

### 4.3 模型配置

```python
MODELS = [
    {"id": "deepseek-v3",        "name": "DeepSeek V3"},
    {"id": "deepseek-v3.2-exp",  "name": "DeepSeek V3.2 Exp"},
    {"id": "tongyi-xiaomi-analysis-pro", "name": "Tongyi Analysis Pro"},
    {"id": "Moonshot-Kimi-K2-Instruct",  "name": "Kimi K2"},
]
```

每个模型配置：`supports_streaming=True`, `timeout=240`, `temperature=0.8`, `max_retries=2`。

---

## 五、前端架构

### 5.1 文件职责

| 文件 | 职责 | 暴露的全局对象 |
|------|------|----------------|
| `data-loader.js` | fetch 封装，加载 4 个 JSON 源 | `window.DataLoader` |
| `components.js` | 纯 DOM 构建函数，无数据访问 | `window.Components` |
| `app.js` | 编排：加载数据 → 渲染 → 事件绑定 | 无（立即执行） |

### 5.2 加载顺序

```
index.html
  ├── <script src="js/data-loader.js">    ← 最先加载
  ├── <script src="js/components.js">     ← 第二
  └── <script src="js/app.js">            ← 最后（依赖前两者）
```

### 5.3 初始化流程

```
DOMContentLoaded
  │
  └── initApp()
        │
        ├── loadAllData()
        │     └── Promise.all([
        │           DataLoader.loadLotteryHistory(),
        │           DataLoader.loadPredictions(),
        │           DataLoader.loadPredictionsHistory(),
        │           DataLoader.loadTokenUsage()
        │         ])
        │
        ├── renderHeroBanner()      ← 最新预测 Tab 顶部
        ├── renderModelsGrid()      ← 4 个模型卡片
        │
        ├── renderHistoryTab()      ← 分析 Tab（懒渲染）
        │     ├── renderStatisticsCards()
        │     ├── renderHistoryTable()
        │     └── renderAccuracyCards()
        │
        ├── renderRankingTab()      ← 排名 Tab（懒渲染）
        │     ├── renderHitRankings()
        │     ├── renderGroupedRankings()
        │     └── renderTokenUsage()
        │
        ├── setupEventListeners()   ← Tab 切换、主题切换
        │
        └── hideLoadingScreen()
```

### 5.4 组件树

```
index.html
├── #loadingScreen                  ← 加载中动画
└── #mainApp                        ← 主应用（隐藏直到加载完成）
    ├── .navbar                     ← 桌面导航（3 个 Tab 按钮）
    ├── .mobile-nav                 ← 移动端底部导航
    ├── .main-content
    │   ├── [data-tab=prediction]   ← Tab 1: 最新预测
    │   │   ├── .hero-banner        ← 期号/日期/倒计时
    │   │   ├── .info-card          ← 策略说明
    │   │   ├── #modelsGrid         ← ★ 4 个模型卡片（动态渲染）
    │   │   │   └── .model-card
    │   │   │       ├── .model-header      ← 模型名称 + 图标
    │   │   │       ├── .strategies-container ← 4 组策略预测
    │   │   │       │   └── .strategy-row
    │   │   │       │       ├── 6 个 .ball.red    ← 红球
    │   │   │       │       ├── .ball-divider
    │   │   │       │       └── 1 个 .ball.blue   ← 蓝球
    │   │   │       └── .best-badge      ← 最佳命中徽章（历史模式）
    │   │   └── .disclaimer-card
    │   │
    │   ├── [data-tab=analysis]     ← Tab 2: 图表分析
    │   │   ├── .prize-rules-card
    │   │   ├── .stats-cards-grid   ← 4 个统计卡
    │   │   ├── #historyTableBody   ← 历史开奖表格
    │   │   └── #accuracyCardsContainer ← 历史命中记录卡片
    │   │
    │   └── [data-tab=ranking]      ← Tab 3: 历史回溯
    │       ├── #rankingContainer         ← 时间窗口命中排名
    │       ├── #groupedRankingContainer  ← 策略/模型聚合排名
    │       └── #tokenUsageContainer      ← Token 用量统计表
    │
    └── footer
```

### 5.5 组件函数映射

| 组件函数 | 位置 | 用途 |
|----------|------|------|
| `createLotteryBall(number, type, size, hit)` | components.js | 创建单个号码球（红/蓝） |
| `createModelCard(model, actualResult, isDrawn)` | components.js | 构建模型卡片 |
| `createStrategyRow(prediction, isLast, actualResult, isBest)` | components.js | 构建策略预测行 |
| `createAccuracyCard(record, model)` | components.js | 构建历史命中记录卡片 |
| `createPredictionGroupRow(prediction, actualResult)` | components.js | 构建预测组行（含命中数） |
| `createHistoryTableRow(draw)` | components.js | 构建历史开奖表格行 |
| `compareNumbers(prediction, actualResult)` | components.js | 计算命中数 |

### 5.6 主题系统

- CSS 变量实现深色/浅色模式（`[data-theme="dark"]` / `[data-theme="light"]`）
- 偏好保存在 `localStorage.theme`
- 切换按钮在顶部导航栏

---

## 六、GitHub Actions 工作流

### 6.1 工作流对比

| 工作流 | 触发 | 运行脚本 | 提交的文件 | 环境变量 |
|--------|------|----------|-----------|---------|
| `update-lottery-data.yml` | 每天 UTC 14:00 + 手动 | `fetch_lottery_history.py` | `data/lottery_history.json`, `fetch_history/lottery_data.json` | 无 |
| `generate-ai-prediction.yml` | 每周一三五 UTC 00:00 + 手动 | `generate_ai_prediction.py` | `data/ai_predictions.json`, `data/predictions_history.json`, `data/token_usage.json` | `AI_API_KEY`, `AI_BASE_URL` |
| `email-daily-digest.yml` | 每天 UTC 00:30 + 10:00 + 手动 | `email_daily_digest.py` | 无（发送邮件） | `SMTP_*`, `EMAIL_*` |
| `push-notify.yml` | 每次 push 到 master + 手动 | `email_push_notify.py` | 无（发送邮件） | `SMTP_*`, `EMAIL_*` |

### 6.2 通用工作流模板

```yaml
steps:
  1. actions/checkout@v4          # 检出代码
  2. actions/setup-python@v5      # 安装 Python
  3. pip install 依赖               # 安装依赖
  4. python3 运行脚本               # 执行脚本（含 env 注入 secrets）
  5. git diff --quiet data/        # 检查是否有数据变更
  6. git add + git commit + push   # 仅在有变更时提交
```

### 6.3 时序与依赖

```
周一/三/五                   每天                    每天
UTC 00:00                  UTC 00:30              UTC 10:00
  │                          │                      │
  ▼                          ▼                      ▼
生成预测 ──git push──► 发送早报         发送晚报
  │                          │
  │  Vercel 自动部署          │ 读取最新数据
  ▼                          ▼
浏览器可访问最新预测         邮件含最新预测
```

**注意**: 工作流之间没有 `workflow_run` 或 `needs:` 依赖，通过共享数据文件 + 时间顺序协调。

---

## 七、数据格式规范

### 7.1 `lottery_history.json`

```json
{
  "last_updated": "2026-08-09T14:27:24Z",
  "data": [
    {
      "period": "26091",
      "date": "2026-08-09",
      "red_balls": ["02", "13", "14", "16", "20", "24"],
      "blue_ball": "05"
    }
  ],
  "next_draw": {
    "next_period": "26092",
    "next_date": "2026-08-11",
    "next_date_display": "2026年08月11日",
    "weekday": "周二",
    "draw_time": "21:15"
  }
}
```

### 7.2 `ai_predictions.json`

```json
{
  "prediction_date": "2026-08-11",
  "target_period": "26092",
  "models": [
    {
      "prediction_date": "2026-08-11",
      "target_period": "26092",
      "model_id": "deepseek-v3",
      "model_name": "DeepSeek V3",
      "predictions": [
        {
          "group_id": 1,
          "strategy": "热号追随者",
          "red_balls": ["02", "05", "14", "16", "24", "33"],
          "blue_ball": "05",
          "description": "基于5期加权频率..."
        }
      ]
    }
  ]
}
```

### 7.3 `predictions_history.json`

```json
{
  "predictions_history": [
    {
      "prediction_date": "2026-08-09",
      "target_period": "26091",
      "actual_result": { "period": "26091", ... },
      "models": [
        {
          "model_id": "deepseek-v3",
          "model_name": "DeepSeek V3",
          "predictions": [
            {
              "group_id": 1,
              "strategy": "热号追随者",
              "red_balls": [...],
              "blue_ball": "03",
              "hit_result": {
                "red_hits": ["24"],
                "red_hit_count": 1,
                "blue_hit": false,
                "total_hits": 1
              }
            }
          ],
          "best_group": 2,
          "best_hit_count": 1
        }
      ]
    }
  ]
}
```

---

## 八、部署拓扑

```
┌──────────┐    git push    ┌────────────┐    HTTPS    ┌──────────┐
│ 开发者    │ ──────────────► │ GitHub      │ ◄───────── │ 用户     │
│ (本地)   │                │ Actions     │            │ (浏览器) │
└──────────┘                │ + 仓库      │            └──────────┘
                            └──────┬───────┘
                                   │ Vercel 自动部署
                                   ▼
                            ┌──────────────┐
                            │ Vercel CDN   │
                            │ (静态托管)    │
                            │ max-age=0    │
                            └──────────────┘
```

**Vercel 配置** (`vercel.json`):
- 数据文件 `data/*.json` 设置 `max-age=0` 不缓存
- 安全响应头（X-Content-Type-Options, X-Frame-Options 等）
- SPA 路由回退

---

## 九、环境变量

| 变量 | 用途 | 来源 |
|------|------|------|
| `AI_API_KEY` | AI 模型 API 密钥 | GitHub Secrets / `.env` |
| `AI_BASE_URL` | AI API 端点（默认 `https://aihubmix.com/v1`） | GitHub Secrets / `.env` |
| `SMTP_SERVER` | SMTP 服务器（默认 `smtp.qq.com`） | GitHub Secrets / `.env` |
| `SMTP_PORT` | SMTP 端口（默认 465） | GitHub Secrets / `.env` |
| `SMTP_USER` | 邮箱地址 | GitHub Secrets / `.env` |
| `SMTP_PASSWORD` | 邮箱授权码 | GitHub Secrets / `.env` |
| `EMAIL_RECIPIENT` | 收件人邮箱 | GitHub Secrets / `.env` |
| `EMAIL_DRY_RUN` | `true` 仅打印不发送 | 本地 `.env` 专用 |

---

## 十、架构原则

1. **Git 即数据库**：所有数据持久化通过 JSON 文件 + git commit，无传统数据库
2. **无后端服务器**：Vercel 纯静态托管，前端直接 fetch JSON
3. **单向数据流**：爬虫 → 生成 → 归档 → 邮件，各步骤独立可运行
4. **幂等写入**：每个工作流先 `git diff` 检查变更，无变更不提交
5. **纯函数模块**：`email_content_builder.py` 无副作用，便于测试
6. **前端零依赖**：原生 JS（ES6+），无框架，无构建步骤