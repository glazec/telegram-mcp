"""Tests for Google OAuth authentication helpers."""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch

# Mock session_manager before importing main to avoid import errors
sys.modules['session_manager'] = Mock()

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
            raise Exception("No token available")

        monkeypatch.setattr("fastmcp.server.dependencies.get_access_token", mock_get_access_token)

        with pytest.raises(ValueError, match="Authentication required"):
            get_authenticated_user_email()
