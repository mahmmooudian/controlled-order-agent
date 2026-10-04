from typing import Any

import pytest

from controlled_agent.services.order import OrderService
from controlled_agent.tools.order import (
    LookupOrderToolError,
    lookup_order,
)


class MismatchedOrderService(OrderService):
    """
    Simulates a compromised or faulty external service.

    The caller requests order 8452, but the service
    intentionally returns data for a different order.
    """

    def get_order(
        self,
        order_id: str,
    ) -> dict[str, Any]:

        return {
            "order_id": "9999",
            "status": "delayed",
            "days_delayed": 5,
        }


def test_lookup_rejects_mismatched_returned_order_id():
    service = MismatchedOrderService()

    with pytest.raises(LookupOrderToolError):
        lookup_order(
            "8452",
            service=service,
        )