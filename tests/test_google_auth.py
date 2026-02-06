"""Tests for Google OAuth authentication helpers."""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch

# Mock session_manager before importing main to avoid import errors
sys.modules["session_manager"] = Mock()

from main import get_authenticated_user_email


class TestAuthHelpers:
    """Test authentication helper functions."""

    def test_get_authenticated_user_email_success(self, monkeypatch):
        """Test extracting email from valid OAuth token."""
        # Mock get_access_token
        mock_token = Mock()
        mock_token.claims = {"email": "test@example.com"}

        def mock_get_access_token():
            return mock_token

        monkeypatch.setattr("fastmcp.server.dependencies.get_access_token", mock_get_access_token)

        email = get_authenticated_user_email()
        assert email == "test@example.com"

    def test_get_authenticated_user_email_no_email_in_token(self, monkeypatch):
        """Test error when email not in token."""
        mock_token = Mock()
        mock_token.claims = {}

        def mock_get_access_token():
            return mock_token

        monkeypatch.setattr("fastmcp.server.dependencies.get_access_token", mock_get_access_token)

        with pytest.raises(ValueError, match="Email not found"):
            get_authenticated_user_email()

    def test_get_authenticated_user_email_no_token(self, monkeypatch):
        """Test error when no auth token available."""

        def mock_get_access_token():
            raise AttributeError("No token available")

        monkeypatch.setattr(
            "fastmcp.server.dependencies.get_access_token", mock_get_access_token
        )

        with pytest.raises(ValueError, match="Authentication required"):
            get_authenticated_user_email()


import asyncio
from unittest.mock import AsyncMock
from main import get_user_client, telegram_clients


class TestClientManagement:
    """Test per-user client caching."""

    @pytest.mark.asyncio
    async def test_get_user_client_no_session(self, monkeypatch):
        """Test error when user has no session in sessions.json."""
        # Mock session_manager to return None
        mock_session_manager = Mock()
        mock_session_manager.get_session = Mock(return_value=None)
        monkeypatch.setattr("main.session_manager", mock_session_manager)

        with pytest.raises(ValueError, match="No Telegram session found"):
            await get_user_client("test@example.com")

    @pytest.mark.asyncio
    async def test_get_user_client_creates_and_caches(self, monkeypatch):
        """Test client is created and cached on first call."""
        # Clear cache
        telegram_clients.clear()

        # Mock session_manager
        mock_session_manager = Mock()
        mock_session_manager.get_session = Mock(return_value="fake_session_string")
        monkeypatch.setattr("main.session_manager", mock_session_manager)

        # Mock StringSession to avoid validation
        mock_string_session = Mock()
        monkeypatch.setattr("main.StringSession", Mock(return_value=mock_string_session))

        # Mock TelegramClient
        mock_client = Mock()
        mock_client.connect = AsyncMock()
        mock_client.is_user_authorized = AsyncMock(return_value=True)
        mock_client.is_connected = Mock(return_value=True)

        def mock_telegram_client(*args, **kwargs):
            return mock_client

        monkeypatch.setattr("main.TelegramClient", mock_telegram_client)

        # First call should create client
        client = await get_user_client("test@example.com")
        assert client == mock_client
        assert "test@example.com" in telegram_clients

        # Second call should return cached client
        client2 = await get_user_client("test@example.com")
        assert client2 == mock_client
        assert mock_client.connect.call_count == 1  # Only called once

    @pytest.mark.asyncio
    async def test_get_user_client_reconnects_if_disconnected(self, monkeypatch):
        """Test client reconnects if cached client is disconnected."""
        # Pre-populate cache with disconnected client
        mock_old_client = Mock()
        mock_old_client.is_connected = Mock(return_value=False)
        telegram_clients["test@example.com"] = mock_old_client

        # Mock session_manager
        mock_session_manager = Mock()
        mock_session_manager.get_session = Mock(return_value="fake_session_string")
        monkeypatch.setattr("main.session_manager", mock_session_manager)

        # Mock StringSession to avoid validation
        mock_string_session = Mock()
        monkeypatch.setattr("main.StringSession", Mock(return_value=mock_string_session))

        # Mock new TelegramClient
        mock_new_client = Mock()
        mock_new_client.connect = AsyncMock()
        mock_new_client.is_user_authorized = AsyncMock(return_value=True)
        mock_new_client.is_connected = Mock(return_value=True)

        def mock_telegram_client(*args, **kwargs):
            return mock_new_client

        monkeypatch.setattr("main.TelegramClient", mock_telegram_client)

        # Should detect disconnection and create new client
        client = await get_user_client("test@example.com")
        assert client == mock_new_client
        assert telegram_clients["test@example.com"] == mock_new_client


from main import with_telegram_client


class TestDecorator:
    """Test @with_telegram_client decorator."""

    @pytest.mark.asyncio
    async def test_decorator_injects_client_success(self, monkeypatch):
        """Test decorator injects client into function."""
        # Mock auth and client functions
        monkeypatch.setattr(
            "main.get_authenticated_user_email", lambda: "test@example.com"
        )

        mock_client = Mock()

        async def mock_get_user_client(email):
            return mock_client

        monkeypatch.setattr("main.get_user_client", mock_get_user_client)

        # Define test function
        @with_telegram_client
        async def test_tool(client, arg1, arg2):
            return {"client": client, "arg1": arg1, "arg2": arg2}

        # Call decorated function
        result = await test_tool("value1", "value2")

        assert result["client"] == mock_client
        assert result["arg1"] == "value1"
        assert result["arg2"] == "value2"

    @pytest.mark.asyncio
    async def test_decorator_handles_auth_error(self, monkeypatch):
        """Test decorator returns error dict on auth failure."""
        # Mock auth to raise ValueError
        def mock_auth():
            raise ValueError("No auth token")

        monkeypatch.setattr("main.get_authenticated_user_email", mock_auth)

        @with_telegram_client
        async def test_tool(client):
            return {"success": True}

        result = await test_tool()

        assert result["success"] is False
        assert "No auth token" in result["error"]
        assert result["error_code"] == "AUTH_REQUIRED"

    @pytest.mark.asyncio
    async def test_decorator_handles_connection_error(self, monkeypatch):
        """Test decorator returns error dict on connection failure."""
        monkeypatch.setattr(
            "main.get_authenticated_user_email", lambda: "test@example.com"
        )

        async def mock_get_user_client(email):
            raise ConnectionError("Session invalid")

        monkeypatch.setattr("main.get_user_client", mock_get_user_client)

        @with_telegram_client
        async def test_tool(client):
            return {"success": True}

        result = await test_tool()

        assert result["success"] is False
        assert "Session invalid" in result["error"]
        assert result["error_code"] == "CONNECTION_FAILED"


from main import get_my_auth_info, disconnect_my_session


class TestHelperTools:
    """Test helper tools for auth management."""

    @pytest.mark.asyncio
    async def test_get_my_auth_info_with_session(self, monkeypatch):
        """Test get_my_auth_info returns correct info."""
        monkeypatch.setattr(
            "main.get_authenticated_user_email", lambda: "test@example.com"
        )

        mock_session_manager = Mock()
        mock_session_manager.session_exists = Mock(return_value=True)
        monkeypatch.setattr("main.session_manager", mock_session_manager)

        result = await get_my_auth_info()

        assert result["success"] is True
        assert result["google_email"] == "test@example.com"
        assert result["has_telegram_session"] is True
        assert "Ready to use" in result["message"]

    @pytest.mark.asyncio
    async def test_get_my_auth_info_without_session(self, monkeypatch):
        """Test get_my_auth_info shows setup URL when no session."""
        monkeypatch.setattr(
            "main.get_authenticated_user_email", lambda: "test@example.com"
        )

        mock_session_manager = Mock()
        mock_session_manager.session_exists = Mock(return_value=False)
        monkeypatch.setattr("main.session_manager", mock_session_manager)

        result = await get_my_auth_info()

        assert result["success"] is True
        assert result["has_telegram_session"] is False
        assert result["setup_url"] == "/setup"
        assert "Visit /setup" in result["message"]

    @pytest.mark.asyncio
    async def test_disconnect_my_session_success(self, monkeypatch):
        """Test disconnect removes client from cache."""
        monkeypatch.setattr(
            "main.get_authenticated_user_email", lambda: "test@example.com"
        )

        # Pre-populate cache
        mock_client = Mock()
        mock_client.disconnect = AsyncMock()
        telegram_clients["test@example.com"] = mock_client

        result = await disconnect_my_session()

        assert result["success"] is True
        assert "disconnected" in result["message"].lower()
        assert "test@example.com" not in telegram_clients
        mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_my_session_no_active_session(self, monkeypatch):
        """Test disconnect when no cached client."""
        monkeypatch.setattr(
            "main.get_authenticated_user_email", lambda: "test@example.com"
        )

        telegram_clients.clear()

        result = await disconnect_my_session()

        assert result["success"] is True
        assert "No active session" in result["message"]
