"""Backward-compatible import for the v1 application.

The canonical runtime now lives in controlled_agent.runtime.
"""

from controlled_agent.runtime import ControlledOrderAgent

__all__ = ["ControlledOrderAgent"]
