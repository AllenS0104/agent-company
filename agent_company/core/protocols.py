"""消息协议 — 标准化 Agent 输入输出格式"""

from __future__ import annotations

import json

from .models import EvidenceBlock, Message, Role

# Agent 输出解析：从 LLM 原始文本提取结构化证据块
EVIDENCE_MARKERS = {
    "claim": ["[Claim]", "[主张]", "**Claim**", "**主张**"],
    "evidence": ["[Evidence]", "[证据]", "**Evidence**", "**证据**"],
    "risk": ["[Risk]", "[风险]", "**Risk**", "**风险**"],
    "next_step": ["[Next Step]", "[下一步]", "**Next Step**", "**下一步**"],
}


def parse_evidence_block(text: str) -> EvidenceBlock:
    """从 LLM 输出文本中解析证据块。

    支持两种格式：
    1. JSON 格式: {"claim": "...", "evidence": "...", ...}
    2. Markdown 标记格式: [Claim] ... [Evidence] ...
    """
    # 尝试 JSON 解析
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "claim" in data:
            return EvidenceBlock(**{k: data.get(k, "") for k in EvidenceBlock.model_fields})
    except (json.JSONDecodeError, TypeError):
        pass

    # Markdown 标记解析
    result: dict[str, str] = {}
    for field, markers in EVIDENCE_MARKERS.items():
        for marker in markers:
            idx = text.find(marker)
            if idx != -1:
                start = idx + len(marker)
                # 查找下一个标记或结尾
                end = len(text)
                for other_field, other_markers in EVIDENCE_MARKERS.items():
                    if other_field == field:
                        continue
                    for other_marker in other_markers:
                        other_idx = text.find(other_marker, start)
                        if other_idx != -1 and other_idx < end:
                            end = other_idx
                result[field] = text[start:end].strip().strip(":")
                break

    return EvidenceBlock(**result)


def format_evidence_prompt() -> str:
    """生成提示 Agent 使用证据格式的指令"""
    return """请在你的回复中使用以下结构化格式：

[Claim] 你的核心主张/观点
[Evidence] 支撑你主张的证据（测试结果/日志/基准/推导/引用）
[Risk] 这个方案的潜在风险
[Next Step] 建议的下一步行动

注意：没有 Evidence 的主张权重会被降低。"""


def format_message_for_display(msg: Message) -> str:
    """格式化消息用于显示"""
    role_emoji = {
        Role.IDEA: "💡",
        Role.ARCHITECT: "🏗️",
        Role.CODER: "💻",
        Role.REVIEWER: "🔍",
        Role.QA: "🧪",
        Role.SECURITY: "🔒",
        Role.PERF: "⚡",
        Role.DOCS: "📝",
        Role.PLANNER: "📋",
        Role.MODERATOR: "🎙️",
        Role.JUDGE: "⚖️",
    }
    emoji = role_emoji.get(msg.agent_role, "🤖")
    header = f"{emoji} [{msg.agent_role.value.upper()}] ({msg.msg_type.value})"
    lines = [header, msg.content]

    if msg.evidence_block and msg.has_evidence:
        eb = msg.evidence_block
        lines.append(f"  📌 Claim: {eb.claim}")
        lines.append(f"  📊 Evidence: {eb.evidence}")
        if eb.risk:
            lines.append(f"  ⚠️ Risk: {eb.risk}")
        if eb.next_step:
            lines.append(f"  ➡️ Next: {eb.next_step}")

    return "\n".join(lines)


def build_context_messages(
    thread_messages: list[Message],
    system_prompt: str,
    evidence_instruction: bool = True,
) -> list[dict[str, str]]:
    """构建发送给 LLM 的上下文消息列表"""
    messages: list[dict[str, str]] = []

    prompt = system_prompt
    if evidence_instruction:
        prompt += "\n\n" + format_evidence_prompt()
    messages.append({"role": "system", "content": prompt})

    for msg in thread_messages:
        orchestration_roles = (Role.PLANNER, Role.MODERATOR, Role.JUDGE)
        role = "assistant" if msg.agent_role in orchestration_roles else "user"
        display = format_message_for_display(msg)
        messages.append({"role": role, "content": display})

    return messages
