# 🏢 Agent Company

多 AI 协作讨论与执行框架 — 让 AI Agent 团队像真实研发组织一样协作

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-109%20passed-brightgreen.svg)]()

## ✨ 特性

- **9 个 Agent 角色** — Idea / Architect / Coder / Reviewer / QA / Security / DevOps / Docs / Perf
- **5 种协作模式** — Debate / Pair Programming / Red-Blue Team / Spec-First / TDD Loop
- **4 个 LLM Provider** — GitHub Models (免费) / OpenAI / Google Gemini / Claude
- **GitHub OAuth 登录** — Device Flow 一键授权，无需手动配置 Token
- **SSE 实时流式** — 讨论过程实时推送，前端即时展示
- **智能记忆系统** — 跨讨论关联、标签分类、重要度评级、归档管理
- **Markdown 导出** — 一键导出讨论报告
- **Docker 支持** — 一键部署

## 🖥️ 截图

Web UI 包含：讨论页 · 历史记录 · 项目记忆 · Provider 配置

## 🚀 快速开始

### 方式一：本地运行

```bash
# 克隆
git clone https://github.com/AllenS0104/agent-company.git
cd agent-company

# 安装后端
pip install -e ".[web]"

# 安装前端
cd web && npm install && cd ..

# 启动（后端 + 前端开发服务器）
python -m agent_company.cli.app serve  # 终端 1：后端 :8000
cd web && npm run dev                   # 终端 2：前端 :5173

# 打开浏览器访问 http://localhost:5173
```

### 方式二：Docker

```bash
git clone https://github.com/AllenS0104/agent-company.git
cd agent-company
cp .env.example .env
docker compose up --build
# 打开 http://localhost:8000
```

### 方式三：CLI

```bash
pip install -e ".[dev]"
agent-company discuss "如何设计一个高并发消息队列？"
agent-company discuss "微服务 vs 单体架构" --mode tdd -r 3
agent-company agents    # 查看角色
agent-company modes     # 查看协作模式
```

## 🏗️ 架构

```
用户接口层 (CLI / Web UI / API)
        ↓
调度层 (Planner + Moderator + Judge)
        ↓
消息总线 (发布/订阅/广播)
        ↓
Agent 团队 (9 个专业角色)
        ↓
工具执行层 (Git / pytest / ruff / 命令执行器)
        ↓
LLM Provider (GitHub Models / OpenAI / Gemini / Claude)
```

## 📁 项目结构

```
agent-company/
├── agent_company/          # Python 后端
│   ├── agents/             # 9 个 Agent 角色
│   ├── api/                # FastAPI 路由 + OAuth
│   ├── cli/                # CLI 命令
│   ├── core/               # 消息总线 / 数据模型 / 存储
│   ├── llm/                # 4 个 LLM Provider 适配
│   ├── memory/             # 智能记忆系统
│   ├── orchestration/      # 调度层（Planner/Moderator/Judge/状态机）
│   ├── tools/              # 工具层（命令执行/测试/Lint/导出）
│   └── workflow/           # 5 种协作工作流
├── web/                    # React 19 前端
│   └── src/
│       ├── pages/          # 讨论 / 历史 / 记忆 / 欢迎 / 404
│       ├── components/     # Sidebar / 消息气泡 / 决策卡片 / 任务列表
│       └── api/            # API 客户端
├── tests/                  # 109 个测试
├── prompts/                # Agent 角色 Prompt 模板
├── Dockerfile              # Docker 多阶段构建
└── docker-compose.yml      # Docker Compose 配置
```

## 🔄 协作模式

| 模式 | 适用场景 | 参与角色 |
|------|---------|---------|
| Debate → Synthesize | 方案选型、架构权衡 | Idea + Architect + Coder + Reviewer → Judge |
| Pair Programming | 快速迭代、高质量模块 | Architect + Coder + Reviewer + QA |
| Red Team / Blue Team | 安全敏感、高稳定性 | Blue(Idea+Arch+Coder) vs Red(Reviewer+Security+QA) |
| Spec-first | 多模块协作、契约驱动 | Architect → QA → Coder → Reviewer |
| TDD Loop | 算法、核心逻辑 | QA → Coder → Reviewer (红绿重构) |

## 🤖 Agent 角色

| 角色 | 职责 |
|------|------|
| 💡 Idea | 产品需求分析、用户故事 |
| 🏗️ Architect | 系统设计、模块拆分 |
| 💻 Coder | 代码实现、技术选型 |
| 🔍 Reviewer | 代码审查、质量把关 |
| 🧪 QA | 测试设计、覆盖分析 |
| 🛡️ Security | 安全评估、威胁建模 |
| 🚀 DevOps | CI/CD、部署策略 |
| 📝 Docs | 文档工程、ADR 记录 |
| ⚡ Perf | 性能分析、优化建议 |

## 🔌 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/discuss` | POST | 发起讨论 |
| `/api/discuss/stream` | POST | SSE 流式讨论 |
| `/api/threads` | GET | 获取讨论列表 |
| `/api/threads/{id}/messages` | GET | 获取讨论消息 |
| `/api/threads/{id}/export` | GET | 导出 Markdown |
| `/api/config` | GET/POST | 查看/更新配置 |
| `/api/auth/github/device-code` | POST | GitHub OAuth |
| `/api/memory` | GET | 查询记忆 |
| `/api/memory/summary` | GET | 记忆统计 |
| `/api/memory/related` | GET | 关联搜索 |
| `/api/modes` | GET | 协作模式列表 |
| `/api/roles` | GET | Agent 角色列表 |
| `/api/providers` | GET | Provider 列表 |

## 🧪 测试

```bash
# 运行全部 109 个测试
pytest

# 代码检查
ruff check agent_company/
```

## 📄 License

MIT
