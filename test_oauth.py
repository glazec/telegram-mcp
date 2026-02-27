"""
OAuth flow integration tests for Telegram MCP Server.

Requires the server to be running: uv run main.py --http
Tests the full MCP OAuth flow: discovery, registration, authorization, token exchange.
"""

import hashlib
import base64
import secrets
import pytest
import httpx

BASE_URL = "https://telegram-mcp-production-762b.up.railway.app"


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10, follow_redirects=False) as c:
        yield c


@pytest.fixture(scope="module")
def async_client():
    return httpx.AsyncClient(base_url=BASE_URL, timeout=10, follow_redirects=False)


def _generate_pkce():
    """Generate PKCE code_verifier and code_challenge (S256)."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


# ── Discovery ────────────────────────────────────────────────────────────────


class TestOAuthDiscovery:
    def test_authorization_server_metadata(self, client):
        """RFC 8414: OAuth server must expose .well-known metadata."""
        r = client.get("/.well-known/oauth-authorization-server")
        assert r.status_code == 200
        meta = r.json()

        # Required fields
        assert "issuer" in meta
        assert "authorization_endpoint" in meta
        assert "token_endpoint" in meta
        assert "registration_endpoint" in meta
        assert "scopes_supported" in meta
        assert "response_types_supported" in meta
        assert "code" in meta["response_types_supported"]
        assert "S256" in meta.get("code_challenge_methods_supported", [])

    def test_protected_resource_metadata(self, client):
        """MCP spec: protected resource metadata at /.well-known/oauth-protected-resource/mcp."""
        r = client.get("/.well-known/oauth-protected-resource/mcp")
        assert r.status_code == 200
        meta = r.json()
        assert "resource" in meta

    def test_mcp_endpoint_requires_auth(self, client):
        """MCP endpoint should reject unauthenticated requests with 401."""
        r = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 401
        body = r.json()
        assert body["error"] == "invalid_token"


# ── Dynamic Client Registration ──────────────────────────────────────────────


class TestClientRegistration:
    def test_register_client(self, client):
        """RFC 7591: Dynamic client registration should return client_id and client_secret."""
        r = client.post(
            "/register",
            json={
                "client_name": "pytest-oauth-test",
                "redirect_uris": ["http://localhost:3000/callback"],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "client_secret_post",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert "client_id" in data
        assert "client_secret" in data
        assert data["client_name"] == "pytest-oauth-test"
        assert "http://localhost:3000/callback" in data["redirect_uris"]

    def test_register_missing_redirect_uri(self, client):
        """Registration without redirect_uris should fail."""
        r = client.post(
            "/register",
            json={"client_name": "bad-client"},
        )
        assert r.status_code in (400, 422)

    def test_register_invalid_redirect_uri(self, client):
        """Registration with non-allowed redirect URI should fail."""
        r = client.post(
            "/register",
            json={
                "client_name": "bad-redirect",
                "redirect_uris": ["https://evil.example.com/callback"],
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
            },
        )
        # Should reject since https://evil.example.com is not in allowed_client_redirect_uris
        assert r.status_code in (400, 422)


# ── Authorization Flow ───────────────────────────────────────────────────────


class TestAuthorizationFlow:
    @pytest.fixture(autouse=True)
    def _register_client(self, client):
        """Register a fresh client for authorization tests."""
        r = client.post(
            "/register",
            json={
                "client_name": "pytest-auth-flow",
                "redirect_uris": ["http://localhost:3000/callback"],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "client_secret_post",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        self.client_id = data["client_id"]
        self.client_secret = data["client_secret"]
        self.verifier, self.challenge = _generate_pkce()

    def test_authorize_redirects_to_consent(self, client):
        """/authorize should 302 redirect to /consent with a txn_id."""
        r = client.get(
            "/authorize",
            params={
                "client_id": self.client_id,
                "redirect_uri": "http://localhost:3000/callback",
                "response_type": "code",
                "scope": "openid https://www.googleapis.com/auth/userinfo.email",
                "code_challenge": self.challenge,
                "code_challenge_method": "S256",
                "state": "test-state-123",
            },
        )
        assert r.status_code == 302
        location = r.headers["location"]
        assert "/consent" in location
        assert "txn_id=" in location

    def test_consent_page_or_redirect_to_google(self, client):
        r1 = client.get(
            "/authorize",
            params={
                "client_id": self.client_id,
                "redirect_uri": "http://localhost:3000/callback",
                "response_type": "code",
                "scope": "openid https://www.googleapis.com/auth/userinfo.email",
                "code_challenge": self.challenge,
                "code_challenge_method": "S256",
                "state": "test-state-456",
            },
        )
        assert r1.status_code == 302
        consent_url = r1.headers["location"]
        r2 = client.get(consent_url)
        if r2.status_code == 302:
            google_url = r2.headers["location"]
            assert "accounts.google.com" in google_url
        else:
            assert r2.status_code == 200
            assert "text/html" in r2.headers.get("content-type", "")

    def test_authorize_missing_client_id(self, client):
        """/authorize without client_id should fail."""
        r = client.get(
            "/authorize",
            params={
                "redirect_uri": "http://localhost:3000/callback",
                "response_type": "code",
                "code_challenge": self.challenge,
                "code_challenge_method": "S256",
            },
        )
        assert r.status_code in (400, 401, 422)

    def test_authorize_unknown_client_id(self, client):
        """/authorize with unregistered client_id should fail."""
        r = client.get(
            "/authorize",
            params={
                "client_id": "nonexistent-client-id",
                "redirect_uri": "http://localhost:3000/callback",
                "response_type": "code",
                "code_challenge": self.challenge,
                "code_challenge_method": "S256",
            },
        )
        assert r.status_code in (400, 401, 403)

    def test_authorize_mismatched_redirect_uri(self, client):
        """/authorize with redirect_uri not matching registration should fail."""
        r = client.get(
            "/authorize",
            params={
                "client_id": self.client_id,
                "redirect_uri": "http://evil.example.com/steal",
                "response_type": "code",
                "code_challenge": self.challenge,
                "code_challenge_method": "S256",
            },
        )
        assert r.status_code in (400, 401, 403)


# ── Token Endpoint ───────────────────────────────────────────────────────────


class TestTokenEndpoint:
    @pytest.fixture(autouse=True)
    def _register_client(self, client):
        r = client.post(
            "/register",
            json={
                "client_name": "pytest-token-test",
                "redirect_uris": ["http://localhost:3000/callback"],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "client_secret_post",
            },
        )
        data = r.json()
        self.client_id = data["client_id"]
        self.client_secret = data["client_secret"]
        self.verifier, self.challenge = _generate_pkce()

    def test_token_invalid_grant(self, client):
        """/token with invalid authorization code should fail."""
        r = client.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": "invalid-code-12345",
                "redirect_uri": "http://localhost:3000/callback",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code_verifier": self.verifier,
            },
        )
        assert r.status_code in (400, 401)
        body = r.json()
        assert "error" in body

    def test_token_missing_grant_type(self, client):
        """/token without grant_type should fail."""
        r = client.post(
            "/token",
            data={
                "code": "some-code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        assert r.status_code in (400, 422)

    def test_token_invalid_client(self, client):
        """/token with wrong client_secret should fail."""
        r = client.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "code": "some-code",
                "redirect_uri": "http://localhost:3000/callback",
                "client_id": self.client_id,
                "client_secret": "wrong-secret",
                "code_verifier": self.verifier,
            },
        )
        assert r.status_code in (400, 401)


# ── MCP Auth Integration ─────────────────────────────────────────────────────


class TestMCPAuthIntegration:
    def test_mcp_rejects_invalid_bearer(self, client):
        """MCP endpoint should reject invalid bearer token."""
        r = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer invalid-token-abc123",
            },
        )
        assert r.status_code == 401

    def test_mcp_rejects_expired_bearer(self, client):
        r = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer expired.token.value",
            },
        )
        assert r.status_code == 401

    def test_mcp_rejects_no_auth_header(self, client):
        """MCP endpoint should reject request without Authorization header."""
        r = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 401


# ── Setup Endpoint ────────────────────────────────────────────────────────────


class TestSetupEndpoint:
    def test_setup_page_loads(self, client):
        """/setup should serve the HTML setup page."""
        r = client.get("/setup")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_setup_send_code_requires_post(self, client):
        """/setup/send-code should reject GET."""
        r = client.get("/setup/send-code")
        assert r.status_code == 405

    def test_setup_verify_requires_post(self, client):
        """/setup/verify should reject GET."""
        r = client.get("/setup/verify")
        assert r.status_code == 405
