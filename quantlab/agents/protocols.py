"""Agent communication and peer review protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from quantlab.agents.roles import AgentMessage


@dataclass(frozen=True, slots=True)
class ResearchDialogue:
    dialogue_id: str
    messages: tuple[AgentMessage, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "dialogue_id": self.dialogue_id,
            "messages": [m.as_dict() for m in self.messages],
        }


class AgentOrchestrationProtocol(Protocol):
    def conduct_roundtable(self, topic: str) -> ResearchDialogue: ...
