"""Tests for agent roles and LLM communication."""

from quantlab.agents.llm_client import FakeLLMClient
from quantlab.agents.roles import AgentMessage, AgentRole


def test_agent_roles_and_fake_llm() -> None:
    client = FakeLLMClient()

    idea = client.complete("Generate an idea for quality momentum")
    assert "Quality" in idea
    assert "Momentum" in idea or "momentum" in idea

    msg = AgentMessage(
        sender_role=AgentRole.IDEA_GENERATOR,
        content=idea,
        metadata={"hypothesis_id": "HYP-01"},
    )
    assert msg.sender_role == AgentRole.IDEA_GENERATOR
    assert msg.metadata["hypothesis_id"] == "HYP-01"
