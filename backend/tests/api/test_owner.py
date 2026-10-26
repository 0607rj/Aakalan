"""The site owner's console: every account, read-only viewing, disable, role, delete."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Estimate, Organisation, Project, Role, User
from app.models.base import utcnow
from tests.conftest import TEST_PASSWORD, login

H = dict[str, str]


def _company(db: Session, members: int = 1) -> list[User]:
    """A fresh company with its own people, so the shared test users are never touched."""
    tag = uuid4().hex[:8]
    org = Organisation(name=f"Owner test {tag}")
    db.add(org)
    db.flush()
    users = [
        User(
            org_id=org.id,
            email=f"p{i}-{tag}@example.com",
            full_name=f"Person {i}",
            role=Role.ADMIN,
            password_hash=hash_password(TEST_PASSWORD),
            email_verified_at=utcnow(),
        )
        for i in range(members)
    ]
    db.add_all(users)
    db.commit()
    return users


def _estimate(client: TestClient, headers: H, name: str) -> dict[str, object]:
    body = {"name": name, "features": ["online_forms"]}
    r = client.post("/quick-estimates", json=body, headers=headers)
    assert r.status_code == 201, r.text
    out: dict[str, object] = r.json()
    return out


def test_only_the_owner_reaches_the_console(
    client: TestClient, admin_headers: H, estimator_headers: H
) -> None:
    for path in ("/owner/overview", "/owner/users"):
        assert client.get(path, headers=estimator_headers).status_code == 403
        assert client.get(path).status_code == 401
        assert client.get(path, headers=admin_headers).status_code == 200


def test_lists_every_company_with_its_use(
    client: TestClient, db: Session, admin_headers: H
) -> None:
    (person,) = _company(db)
    _estimate(client, login(client, person.email), "Their portal")
    rows = client.get("/owner/users", headers=admin_headers).json()
    row = next(r for r in rows if r["id"] == person.id)
    assert row["org_members"] == 1 and row["projects"] == 1 and row["estimates"] == 1
    assert row["last_estimate_at"] is not None and row["is_owner"] is False
    me = next(r for r in rows if r["email"] == "admin@aakalan.local")
    assert me["is_owner"] is True
    overview = client.get("/owner/overview", headers=admin_headers).json()
    assert overview["users"] >= len(rows) and overview["estimates"] >= 1

    listed = client.get(f"/owner/users/{person.id}/estimates", headers=admin_headers).json()
    assert [s["name"] for s in listed] == ["Their portal"]


def test_view_as_is_read_only(client: TestClient, db: Session, admin_headers: H) -> None:
    (person,) = _company(db)
    s = _estimate(client, login(client, person.email), "Look but not touch")
    r = client.post(f"/owner/users/{person.id}/view", headers=admin_headers)
    assert r.status_code == 200, r.text
    viewing = {"Authorization": f"Bearer {r.json()['access_token']}"}
    me = client.get("/auth/me", headers=viewing).json()
    assert me["email"] == person.email and me["viewed_by_owner"] == "admin@aakalan.local"
    assert client.get(f"/estimates/{s['estimate_id']}/summary", headers=viewing).status_code == 200
    assert client.get("/quick-estimates", headers=viewing).status_code == 200
    # nothing can be changed while viewing
    assert client.delete(f"/projects/{s['project_id']}", headers=viewing).status_code == 403
    blocked = client.post(
        "/quick-estimates", json={"name": "x", "features": ["online_forms"]}, headers=viewing
    )
    assert blocked.status_code == 403
    # a normal session has no owner on it
    assert (
        client.get("/auth/me", headers=login(client, person.email)).json()["viewed_by_owner"]
        is None
    )


def test_owner_accounts_are_not_changed_here(
    client: TestClient, db: Session, admin_headers: H
) -> None:
    owner = db.scalars(select(User).where(User.email == "admin@aakalan.local")).one()
    for call in (
        client.patch(f"/owner/users/{owner.id}", json={"is_active": False}, headers=admin_headers),
        client.post(f"/owner/users/{owner.id}/view", headers=admin_headers),
        client.delete(f"/owner/users/{owner.id}", headers=admin_headers),
    ):
        assert call.status_code == 409
    assert client.patch("/owner/users/nope", json={}, headers=admin_headers).status_code == 404


def test_disable_role_and_verify(client: TestClient, db: Session, admin_headers: H) -> None:
    (person,) = _company(db)
    theirs = login(client, person.email)
    url = f"/owner/users/{person.id}"

    r = client.patch(url, json={"is_active": False}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert client.get("/auth/me", headers=theirs).status_code == 401  # signed out at once
    login_again = {"email": person.email, "password": TEST_PASSWORD}
    assert client.post("/auth/login", json=login_again).status_code == 401
    assert client.post(f"{url}/view", headers=admin_headers).status_code == 409

    client.patch(url, json={"is_active": True}, headers=admin_headers)
    r = client.patch(url, json={"role": "viewer", "email_verified": False}, headers=admin_headers)
    assert r.json()["role"] == "viewer" and r.json()["email_verified"] is False
    r = client.patch(url, json={"email_verified": True}, headers=admin_headers)
    assert r.json()["email_verified"] is True
    assert client.get("/auth/me", headers=login(client, person.email)).json()["role"] == "viewer"


def test_delete_a_lone_user_takes_the_company(
    client: TestClient, db: Session, admin_headers: H
) -> None:
    (person,) = _company(db)
    org_id = person.org_id
    _estimate(client, login(client, person.email), "Gone with them")
    assert client.delete(f"/owner/users/{person.id}", headers=admin_headers).status_code == 204
    db.expire_all()
    assert db.get(Organisation, org_id) is None
    assert db.scalars(select(Project).where(Project.org_id == org_id)).first() is None
    assert db.scalars(select(Estimate).where(Estimate.org_id == org_id)).first() is None


def test_delete_one_of_several_keeps_the_company(
    client: TestClient, db: Session, admin_headers: H
) -> None:
    leaving, staying = _company(db, members=2)
    leaving_id, staying_id, staying_email = leaving.id, staying.id, staying.email
    s = _estimate(client, login(client, leaving.email), "Made by the leaver")
    assert client.delete(f"/owner/users/{leaving_id}", headers=admin_headers).status_code == 204
    db.expire_all()
    assert db.get(User, leaving_id) is None and db.get(User, staying_id) is not None
    project = db.get(Project, s["project_id"])
    assert project is not None and project.created_by is None
    listed = client.get("/quick-estimates", headers=login(client, staying_email)).json()
    assert [x["name"] for x in listed] == ["Made by the leaver"]
