"""测试协议解析"""

from agent_company.core.protocols import parse_evidence_block


def test_parse_json_format():
    text = '{"claim": "方案A", "evidence": "测试通过", "risk": "无", "next_step": "实现"}'
    eb = parse_evidence_block(text)
    assert eb.claim == "方案A"
    assert eb.evidence == "测试通过"


def test_parse_markdown_format():
    text = """
[Claim] 推荐使用事件驱动架构
[Evidence] 基准测试显示延迟 < 30ms
[Risk] 事件丢失需要处理
[Next Step] 实现核心模块
"""
    eb = parse_evidence_block(text)
    assert "事件驱动" in eb.claim
    assert "30ms" in eb.evidence
    assert "事件丢失" in eb.risk
    assert "核心模块" in eb.next_step


def test_parse_empty():
    eb = parse_evidence_block("just some random text")
    assert eb.claim == ""
    assert eb.evidence == ""
