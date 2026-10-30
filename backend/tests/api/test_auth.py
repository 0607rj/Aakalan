from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import LoginFailure
from tests.conftest import TEST_PASSWORD


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"


def test_login_and_me(client: TestClient) -> None:
    response = client.post(
        "/auth/login", json={"email": "Finance@aakalan.local", "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "finance"
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "finance@aakalan.local"
    assert me.json()["org_name"] == "Demo Systems Integrator"


def test_login_wrong_password(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": "admin@aakalan.local", "password": "x"})
    assert response.status_code == 401


def test_me_requires_valid_token(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401
    bad = client.get("/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert bad.status_code == 401


def test_wrong_passwords_slow_down_sign_in(client: TestClient, db: Session) -> None:
    """After `login_max_failures` wrong passwords for one email, even the right one waits;
    another account is not affected, and the wait ends with the window."""
    limit = get_settings().login_max_failures
    wrong = {"email": "viewer@aakalan.local", "password": "wrong-password"}
    right = {"email": "Viewer@aakalan.local", "password": TEST_PASSWORD}
    try:
        for _ in range(limit):
            assert client.post("/auth/login", json=wrong).status_code == 401
        refused = client.post("/auth/login", json=right)
        assert refused.status_code == 429
        assert int(refused.headers["Retry-After"]) > 0
        assert "Too many wrong passwords" in refused.json()["detail"]
        ok = {"email": "admin@aakalan.local", "password": TEST_PASSWORD}
        assert client.post("/auth/login", json=ok).status_code == 200
        db.execute(
            update(LoginFailure).values(
                created_at=datetime.now(UTC)
                - timedelta(minutes=get_settings().login_window_minutes + 1)
            )
        )
        db.commit()
        assert client.post("/auth/login", json=right).status_code == 200
        assert db.scalar(select(func.count()).select_from(LoginFailure)) == 0
    finally:
        db.execute(delete(LoginFailure))
        db.commit()
