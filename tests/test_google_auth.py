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
