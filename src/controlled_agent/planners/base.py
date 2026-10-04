from __future__ import annotations

from abc import ABC, abstractmethod

from controlled_agent.domain.schemas import AgentDecision
from controlled_agent.domain.state import AgentState


class BasePlanner(ABC):
    """
    Common interface for every planner.

    All planner implementations propose the next action.
    They never execute tools directly.
    """

    @abstractmethod
    def decide(
        self,
        state: AgentState,
    ) -> AgentDecision:
        raise NotImplementedError
