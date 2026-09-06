from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from wdl_be_core.domain.exceptions import AuthenticationError
from wdl_be_core.infrastructure.identity import JWTAccessTokenVerifier
from wdl_be_core.main import app

SECRET = "test-secret-key-that-is-long-enough"


def issue_token(*, kind: str = "access") -> tuple[str, object, object]:
    account_id = uuid4()
    session_id = uuid4()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(account_id),
            "sid": str(session_id),
            "type": kind,
            "iss": "wdl-identity",
            "aud": "wdl-api",
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=5),
            "jti": str(uuid4()),
        },
        SECRET,
        algorithm="HS256",
    )
    return token, account_id, session_id


def test_identity_access_token_is_mapped_to_current_user() -> None:
    token, account_id, session_id = issue_token()
    verifier = JWTAccessTokenVerifier(
        secret_key=SECRET,
        issuer="wdl-identity",
        audience="wdl-api",
    )

    current_user = verifier.verify(token)

    assert current_user.account_id == account_id
    assert current_user.session_id == session_id


def test_refresh_token_is_not_accepted_by_core() -> None:
    token, _, _ = issue_token(kind="refresh")
    verifier = JWTAccessTokenVerifier(
        secret_key=SECRET,
        issuer="wdl-identity",
        audience="wdl-api",
    )

    with pytest.raises(AuthenticationError):
        verifier.verify(token)


def test_realm_routes_require_bearer_token() -> None:
    response = TestClient(app).get("/realms/")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_realm_writes_do_not_accept_client_controlled_audit_fields() -> None:
    schema = app.openapi()
    create_schema = schema["components"]["schemas"]["RealmCreateRequestModel"]
    update_schema = schema["components"]["schemas"]["RealmUpdateRequestModel"]

    assert "author_id" not in create_schema["properties"]
    assert "updated_by" not in update_schema["properties"]
