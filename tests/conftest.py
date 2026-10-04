import pytest

from controlled_agent.adapters.mock import TICKET_STORE


@pytest.fixture(autouse=True)
def reset_ticket_store():
    """
    Keep tests isolated from the in-memory mock ticket database.
    """
    TICKET_STORE.clear()

    yield

    TICKET_STORE.clear()