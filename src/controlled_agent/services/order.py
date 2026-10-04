from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class OrderServiceError(Exception):
    """Base exception for order service failures."""


class OrderServiceTimeoutError(OrderServiceError):
    """Raised when the order provider times out."""


class OrderService(ABC):
    """
    Contract for all order data providers.

    Implementations may retrieve data from:
    - an in-memory mock
    - a database
    - an ERP
    - an HTTP API
    """

    @abstractmethod
    def get_order(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        """
        Return raw, untrusted order data.

        Validation belongs to the tool/security layer.
        """
        raise NotImplementedError
