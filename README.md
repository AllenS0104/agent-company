# Agent Company

多AI协作讨论与执行框架 —— AI 虚拟研发组织

## 愿景

让多个 AI Agent 扮演产品、架构、开发、测试、审查等角色，通过结构化讨论稳定地产出靠谱决策和可交付工程产物。

## 核心架构

```
用户接口层 (CLI / Web API)
        ↓
调度层 (Planner + Moderator + Judge)
        ↓
消息总线 (发布/订阅/广播)
        ↓
角色 Agent (Idea / Architect / Coder / Reviewer / QA / Security / ...)
        ↓
工具执行层 (Git / pytest / ruff / 命令执行器)
        ↓
LLM Provider (OpenAI / Gemini / Claude / Local)
```

## 快速开始

```bash
# 安装
pip install -e ".[dev]"

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 运行 Demo
agent-company discuss "如何设计一个高并发消息队列？"

# 查看帮助
agent-company --help
```

## 协作模式

| 模式 | 适用场景 |
|------|---------|
| Debate → Synthesize | 方案选型、架构权衡 |
| Pair Programming | 快速迭代、高质量模块 |
| Red Team / Blue Team | 安全敏感、高稳定性 |
| Spec-first | 多模块协作 |
| TDD Loop | 算法、核心逻辑 |

## 产出物

- PR / Commit（可合并的代码变更）
- 测试报告（单测/集成测 + 覆盖率）
- ADR 决策记录（为什么选这个方案）
- 风险清单（安全/性能/兼容性）

## 开发

```bash
pip install -e ".[all]"
pytest
ruff check .
```

## License

MIT
