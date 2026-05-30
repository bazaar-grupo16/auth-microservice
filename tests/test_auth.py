"""Tests for JWT endpoints: ``/token`` and ``/validate``."""

import uuid

from fastapi.testclient import TestClient


class TestTokenEndpoint:
    """Coverage for ``/token`` endpoint behavior."""

    def test_generates_access_and_refresh_tokens(self, client: TestClient) -> None:
        user_id = uuid.uuid4()

        response = client.post("/token", json={"user_id": str(user_id), "is_admin": False})

        assert response.status_code == 201
        data = response.json()
        assert isinstance(data["access_token"], str)
        assert data["access_token"]
        assert isinstance(data["refresh_token"], str)
        assert data["refresh_token"]
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert data["refresh_expires_in"] > data["expires_in"]

    def test_requires_is_admin_field(self, client: TestClient) -> None:
        user_id = uuid.uuid4()

        response = client.post("/token", json={"user_id": str(user_id)})

        assert response.status_code == 422


class TestValidateEndpoint:
    """Coverage for ``/validate`` endpoint behavior."""

    def test_returns_user_id_and_headers_for_non_admin_token(self, client: TestClient) -> None:
        user_id = uuid.uuid4()
        token_response = client.post("/token", json={"user_id": str(user_id), "is_admin": False})
        token = token_response.json()["access_token"]

        response = client.get("/validate", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json() == {"status": "valid", "user_id": str(user_id)}
        assert response.headers["x-user-id"] == str(user_id)
        assert response.headers["x-is-admin"] == "false"

    def test_returns_user_id_and_headers_for_admin_token(self, client: TestClient) -> None:
        user_id = uuid.uuid4()
        token_response = client.post("/token", json={"user_id": str(user_id), "is_admin": True})
        token = token_response.json()["access_token"]

        response = client.get("/validate", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json() == {"status": "valid", "user_id": str(user_id)}
        assert response.headers["x-user-id"] == str(user_id)
        assert response.headers["x-is-admin"] == "true"

    def test_returns_401_for_invalid_token(self, client: TestClient) -> None:
        response = client.get(
            "/validate",
            headers={"Authorization": "Bearer not.a.valid.token"},
        )

        assert response.status_code == 401
        assert response.json() == {"detail": "Token is invalid"}

    def test_returns_401_for_refresh_token_in_validate_endpoint(
        self,
        client: TestClient,
    ) -> None:
        user_id = uuid.uuid4()
        token_response = client.post("/token", json={"user_id": str(user_id), "is_admin": False})
        refresh_token = token_response.json()["refresh_token"]

        response = client.get(
            "/validate",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )

        assert response.status_code == 401
        assert response.json() == {"detail": "Token type is invalid for this endpoint"}

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


class TestRevokeEndpoint:
    """Coverage for ``DELETE /token/{user_id}`` endpoint behavior."""

    def test_revokes_all_refresh_tokens_for_user(self, client: TestClient) -> None:
        user_id = uuid.uuid4()
        tokens = client.post("/token", json={"user_id": str(user_id), "is_admin": False}).json()
        refresh_token = tokens["refresh_token"]

        revoke_response = client.delete(f"/token/{user_id}")
        assert revoke_response.status_code == 204

        refresh_response = client.post(
            "/token/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 401
        assert refresh_response.json() == {"detail": "Refresh token has been revoked"}

    def test_revoke_does_not_affect_other_users(self, client: TestClient) -> None:
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        client.post("/token", json={"user_id": str(user_a), "is_admin": False})
        tokens_b = client.post("/token", json={"user_id": str(user_b), "is_admin": False}).json()

        client.delete(f"/token/{user_a}")

        refresh_response = client.post(
            "/token/refresh",
            json={"refresh_token": tokens_b["refresh_token"]},
        )
        assert refresh_response.status_code == 200

    def test_revoke_is_idempotent(self, client: TestClient) -> None:
        user_id = uuid.uuid4()
        client.post("/token", json={"user_id": str(user_id), "is_admin": False})

        assert client.delete(f"/token/{user_id}").status_code == 204
        assert client.delete(f"/token/{user_id}").status_code == 204


class TestRefreshEndpoint:
    """Coverage for ``/token/refresh`` endpoint behavior."""

    def test_rotates_refresh_token_and_returns_new_pair(self, client: TestClient) -> None:
        user_id = uuid.uuid4()
        token_response = client.post("/token", json={"user_id": str(user_id), "is_admin": False})
        old_refresh = token_response.json()["refresh_token"]

        refresh_response = client.post(
            "/token/refresh",
            json={"refresh_token": old_refresh},
        )

        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert new_tokens["access_token"]
        assert new_tokens["refresh_token"]
        assert new_tokens["refresh_token"] != old_refresh

        reused_old_refresh = client.post(
            "/token/refresh",
            json={"refresh_token": old_refresh},
        )
        assert reused_old_refresh.status_code == 401
        assert reused_old_refresh.json() == {"detail": "Refresh token has been revoked"}

    def test_preserves_is_admin_flag_after_rotation(self, client: TestClient) -> None:
        user_id = uuid.uuid4()
        token_response = client.post("/token", json={"user_id": str(user_id), "is_admin": True})
        old_refresh = token_response.json()["refresh_token"]

        new_tokens = client.post("/token/refresh", json={"refresh_token": old_refresh}).json()
        new_access = new_tokens["access_token"]

        validate_response = client.get(
            "/validate", headers={"Authorization": f"Bearer {new_access}"}
        )
        assert validate_response.status_code == 200
        assert validate_response.headers["x-is-admin"] == "true"

    def test_returns_401_for_invalid_refresh_token(self, client: TestClient) -> None:
        response = client.post(
            "/token/refresh",
            json={"refresh_token": "not.a.valid.token"},
        )

        assert response.status_code == 401
        assert response.json() == {"detail": "Token is invalid"}
