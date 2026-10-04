"""Backward-compatible imports for the v1 application.

The canonical audit implementation now lives in controlled_agent.observability.
"""

from controlled_agent.observability import AuditEvent, AuditLogger

__all__ = ["AuditEvent", "AuditLogger"]
