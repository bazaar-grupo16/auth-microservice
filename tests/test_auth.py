"""Tests for JWT endpoints: ``/token`` and ``/validate``."""

import uuid

from fastapi.testclient import TestClient


class TestTokenEndpoint:
    """Coverage for ``/token`` endpoint behavior."""

    def test_generates_a_bearer_token(self, client: TestClient) -> None:
        user_id = uuid.uuid4()

        response = client.post("/token", json={"user_id": str(user_id)})

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data["access_token"], str)
        assert data["access_token"]
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0


class TestValidateEndpoint:
    """Coverage for ``/validate`` endpoint behavior."""

    def test_returns_user_id_for_valid_token(self, client: TestClient) -> None:
        user_id = uuid.uuid4()
        token_response = client.post("/token", json={"user_id": str(user_id)})
        token = token_response.json()["access_token"]

        response = client.get("/validate", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json() == {"status": "valid", "user_id": str(user_id)}

    def test_returns_401_for_invalid_token(self, client: TestClient) -> None:
        response = client.get(
            "/validate",
            headers={"Authorization": "Bearer not.a.valid.token"},
        )

        assert response.status_code == 401
        assert response.json() == {"detail": "Token is invalid"}

    def test_returns_401_when_authorization_header_missing(self, client: TestClient) -> None:
        response = client.get("/validate")

        assert response.status_code == 401
        assert response.json() == {"detail": "Missing Authorization header"}

    def test_returns_401_when_authorization_header_is_not_bearer(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/validate", headers={"Authorization": "Basic abc"})

        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid Authorization header format"}
