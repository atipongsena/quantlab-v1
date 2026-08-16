"""Agent role definitions and communication message models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class AgentRole(StrEnum):
    IDEA_GENERATOR = "IDEA_GENERATOR"
    FACTOR_ENGINEER = "FACTOR_ENGINEER"
    VALIDATION_CRITIC = "VALIDATION_CRITIC"
    LEAD_STRATEGIST = "LEAD_STRATEGIST"


@dataclass(frozen=True, slots=True)
class AgentMessage:
    sender_role: AgentRole
    content: str
    metadata: Mapping[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "sender_role": self.sender_role.value,
            "content": self.content,
            "metadata": dict(self.metadata),
        }
