"""Tests for the RBAC model + permission-check endpoints (keel auth gap)."""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_roles_endpoint_returns_matrix():
    r = client.get("/api/auth/roles")
    assert r.status_code == 200
    data = r.json()
    roles = {x["role"] for x in data["roles"]}
    assert {"viewer", "developer", "maintainer", "admin"} <= roles

    # viewer is read-only; admin has admin:*.
    viewer = next(x for x in data["roles"] if x["role"] == "viewer")
    admin = next(x for x in data["roles"] if x["role"] == "admin")
    assert viewer["read_only"] is True and viewer["permissions"] == []
    assert "admin:*" in admin["permissions"]

    # Permissions carry descriptions; personas are present.
    perms = {p["permission"] for p in data["permissions"]}
    assert "knowledge:project" in perms
    assert all(p["description"] for p in data["permissions"])
    personas = {p["persona"] for p in data["personas"]}
    assert {"dev", "qa", "ba", "sm", "domain"} <= personas


def test_roles_are_cumulative():
    data = client.get("/api/auth/roles").json()
    by = {x["role"]: set(x["permissions"]) for x in data["roles"]}
    # maintainer includes developer's build permissions.
    assert by["developer"] <= by["maintainer"]
    assert "platform:configure" in by["maintainer"]


def test_check_permission_endpoint():
    # Dev provider resolves an admin principal, so it passes any permission.
    r = client.get("/api/auth/check", params={"permission": "knowledge:project"})
    assert r.status_code == 200
    body = r.json()
    assert body["permission"] == "knowledge:project"
    assert body["allowed"] is True
    assert body["subject"]
