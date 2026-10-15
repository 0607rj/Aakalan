from fastapi.testclient import TestClient

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
