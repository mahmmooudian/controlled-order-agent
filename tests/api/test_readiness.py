from fastapi.testclient import (
    TestClient,
)

from controlled_agent.api import (
    create_app,
)
from controlled_agent.api.dependencies import (
    check_database_readiness,
    get_database_readiness,
)


# ============================================================
# REAL SQLITE READINESS
# ============================================================

def test_database_readiness_with_real_sqlite(
    tmp_path,
):
    database_path = (
        tmp_path
        / "readiness.db"
    )

    ready = check_database_readiness(
        database_path
    )

    assert ready is True

    assert (
        database_path.exists()
        is True
    )


# ============================================================
# READY ENDPOINT - HEALTHY
# ============================================================

def test_ready_endpoint_when_database_is_healthy():
    app = create_app()

    app.dependency_overrides[
        get_database_readiness
    ] = lambda: True

    client = TestClient(
        app
    )

    response = client.get(
        "/ready"
    )

    assert response.status_code == 200

    assert response.json() == {
        "ready": True,
        "service": "controlled-order-agent",
    }


# ============================================================
# READY ENDPOINT - DATABASE FAILURE
# ============================================================

def test_ready_endpoint_returns_503_when_database_fails():
    app = create_app()

    app.dependency_overrides[
        get_database_readiness
    ] = lambda: False

    client = TestClient(
        app
    )

    response = client.get(
        "/ready"
    )

    assert response.status_code == 503

    assert response.json() == {
        "detail": "Database is not ready.",
    }


# ============================================================
# HEALTH MUST REMAIN INDEPENDENT
# ============================================================

def test_health_remains_available_when_database_is_not_ready():
    app = create_app()

    app.dependency_overrides[
        get_database_readiness
    ] = lambda: False

    client = TestClient(
        app
    )

    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "ok"

    assert (
        payload["service"]
        == "controlled-order-agent"
    )