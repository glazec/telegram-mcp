# Google OAuth Multi-Tenant Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Google OAuth authentication to enable multi-tenant Telegram MCP server where each authenticated user uses their own Telegram session.

**Architecture:** Replace global client with per-user client cache (lazy-loaded). Add decorator to inject authenticated user's client into all tools. Keep /setup UI for session creation.

**Tech Stack:** FastMCP 3.0.0b1, Google OAuth (authlib), Telethon, Starlette

---

## Task 1: Add Auth Helper Functions

**Files:**
- Modify: `main.py` (add after imports, before global client initialization ~line 130)
- Test: `tests/test_google_auth.py` (create new)

**Step 1: Write failing tests for auth helpers**

Create `tests/test_google_auth.py`:

```python
"""Tests for Google OAuth authentication helpers."""

import pytest
from unittest.mock import Mock, MagicMock
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

        monkeypatch.setattr("main.get_access_token", mock_get_access_token)

        email = get_authenticated_user_email()
        assert email == "test@example.com"

    def test_get_authenticated_user_email_no_email_in_token(self, monkeypatch):
        """Test error when email not in token."""
        mock_token = Mock()
        mock_token.claims = {}

        def mock_get_access_token():
            return mock_token

        monkeypatch.setattr("main.get_access_token", mock_get_access_token)

        with pytest.raises(ValueError, match="Email not found"):
            get_authenticated_user_email()

    def test_get_authenticated_user_email_no_token(self, monkeypatch):
        """Test error when no auth token available."""
        def mock_get_access_token():
            raise Exception("No token available")

        monkeypatch.setattr("main.get_access_token", mock_get_access_token)

        with pytest.raises(ValueError, match="Authentication required"):
            get_authenticated_user_email()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_google_auth.py -xvs`

Expected: FAIL with "cannot import name 'get_authenticated_user_email'"

**Step 3: Implement auth helper function**

Add to `main.py` after imports (around line 70):

```python
def get_authenticated_user_email() -> str:
    """
    Extract the authenticated user's email from the OAuth token.

    Returns:
        User's email address

    Raises:
        ValueError: If no auth token or email not in token
    """
    try:
        from fastmcp.server.dependencies import get_access_token
        token = get_access_token()
        email = token.claims.get("email")
        if not email:
            raise ValueError("Email not found in authentication token")
        return email
    except Exception as e:
        raise ValueError(f"Authentication required: {str(e)}")
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_google_auth.py -xvs`

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add tests/test_google_auth.py main.py
git commit -m "feat: add get_authenticated_user_email helper

- Extracts email from OAuth token claims
- Raises ValueError if no token or email missing
- Comprehensive test coverage for success and error cases"
```

---

## Task 2: Add Client Management Functions

**Files:**
- Modify: `main.py` (replace global `client` initialization around line 130)
- Test: `tests/test_google_auth.py` (append)

**Step 1: Write failing tests for client management**

Append to `tests/test_google_auth.py`:

```python
import asyncio
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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_google_auth.py::TestClientManagement -xvs`

Expected: FAIL with "cannot import name 'get_user_client'" or "cannot import name 'telegram_clients'"

**Step 3: Replace global client with per-user cache**

Find the global client initialization in `main.py` (around line 130):

```python
# OLD CODE (remove this):
client = None  # Global Telegram client
```

Replace with:

```python
# Global Telegram clients cache (per authenticated user)
telegram_clients: Dict[str, TelegramClient] = {}


async def get_user_client(user_email: str) -> TelegramClient:
    """
    Get or create a Telegram client for the authenticated user.

    Implements lazy-loading with caching:
    - Checks cache first (fast path)
    - Loads session from sessions.json if not cached
    - Connects and caches client for reuse

    Args:
        user_email: User's Google email from auth token

    Returns:
        Connected TelegramClient for this user

    Raises:
        ValueError: If user has no session in sessions.json
        ConnectionError: If client connection fails
    """
    # Check cache first
    if user_email in telegram_clients:
        client = telegram_clients[user_email]
        if client.is_connected():
            return client
        # Client disconnected, remove from cache
        del telegram_clients[user_email]

    # Load session from sessions.json
    session_string = session_manager.get_session(user_email)
    if not session_string:
        raise ValueError(
            f"No Telegram session found for {user_email}. "
            f"Please visit /setup to authenticate your Telegram account."
        )

    # Create and connect new client
    client = TelegramClient(
        StringSession(session_string),
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH
    )
    await client.connect()

    if not await client.is_user_authorized():
        raise ConnectionError(f"Session invalid for {user_email}")

    # Cache for reuse
    telegram_clients[user_email] = client
    return client
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_google_auth.py -xvs`

Expected: PASS (6 tests total)

**Step 5: Commit**

```bash
git add main.py tests/test_google_auth.py
git commit -m "feat: add per-user client caching with lazy loading

- Replace global client with telegram_clients dict
- Implement get_user_client() with cache-first lookup
- Auto-reconnect if cached client disconnected
- Load session from sessions.json per user email
- Comprehensive test coverage"
```

---

## Task 3: Add Decorator for Auth Integration

**Files:**
- Modify: `main.py` (add decorator after `get_user_client` function)
- Test: `tests/test_google_auth.py` (append)

**Step 1: Write failing tests for decorator**

Append to `tests/test_google_auth.py`:

```python
from main import with_telegram_client


class TestDecorator:
    """Test @with_telegram_client decorator."""

    @pytest.mark.asyncio
    async def test_decorator_injects_client_success(self, monkeypatch):
        """Test decorator injects client into function."""
        # Mock auth and client functions
        monkeypatch.setattr(
            "main.get_authenticated_user_email",
            lambda: "test@example.com"
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
            "main.get_authenticated_user_email",
            lambda: "test@example.com"
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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_google_auth.py::TestDecorator -xvs`

Expected: FAIL with "cannot import name 'with_telegram_client'"

**Step 3: Implement decorator**

Add to `main.py` after `get_user_client()` function:

```python
from functools import wraps
from typing import Callable


def with_telegram_client(func: Callable) -> Callable:
    """
    Decorator that injects authenticated user's Telegram client into tool functions.

    Handles:
    - Extracting user email from OAuth token
    - Getting/creating user's Telegram client (with caching)
    - Error handling for auth and connection failures

    Usage:
        @mcp.tool()
        @with_telegram_client
        async def send_message(client: TelegramClient, chat_id: str, message: str):
            result = await client.send_message(chat_id, message)
            return {"success": True, "message_id": result.id}

    The decorator:
    - Passes client as first argument to the tool
    - Returns error dict on auth/connection failures
    - Tool functions should only implement business logic
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> dict:
        try:
            # Extract authenticated user's email
            user_email = get_authenticated_user_email()

            # Get user's Telegram client (cached or create new)
            client = await get_user_client(user_email)

            # Call original function with client as first arg
            return await func(client, *args, **kwargs)

        except ValueError as e:
            # Auth errors (no token, no session, etc.)
            return {
                "success": False,
                "error": str(e),
                "error_code": "AUTH_REQUIRED"
            }
        except ConnectionError as e:
            # Connection errors (invalid session, etc.)
            return {
                "success": False,
                "error": str(e),
                "error_code": "CONNECTION_FAILED"
            }
        except Exception as e:
            # Unexpected errors
            return {
                "success": False,
                "error": f"Internal error: {str(e)}",
                "error_code": "INTERNAL_ERROR"
            }

    return wrapper
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_google_auth.py -xvs`

Expected: PASS (9 tests total)

**Step 5: Commit**

```bash
git add main.py tests/test_google_auth.py
git commit -m "feat: add @with_telegram_client decorator

- Injects authenticated user's client into tool functions
- Handles auth errors (no token, no session)
- Handles connection errors (invalid session)
- Returns structured error dicts with error codes
- Comprehensive test coverage"
```

---

## Task 4: Add Google OAuth Provider

**Files:**
- Modify: `main.py` (add before `mcp = FastMCP()` initialization, around line 76)

**Step 1: Add OAuth provider initialization**

Find the FastMCP initialization in `main.py` (around line 76):

```python
# OLD CODE:
mcp = FastMCP(
    name="telegram",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    ),
)
```

Replace with:

```python
# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Initialize auth provider (optional - only if credentials provided)
auth_provider = None
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    from fastmcp.server.auth import GoogleProvider

    auth_provider = GoogleProvider(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        base_url=BASE_URL,
        required_scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        allowed_client_redirect_uris=[
            "https://claude.ai/api/mcp/auth_callback",
            "http://localhost:*"
        ],
        redirect_path="/auth/callback",
    )
    print("🔐 Google OAuth enabled (multi-tenant mode)")
else:
    print("⚠️  Google OAuth disabled (set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to enable)")

mcp = FastMCP(
    name="telegram",
    auth=auth_provider,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    ),
)
```

**Step 2: Verify imports**

Check that `os` is imported at the top of `main.py`. If not, add:

```python
import os
```

**Step 3: Test OAuth initialization**

Run: `uv run python -c "import main; print('OAuth init OK')"`

Expected: Should print OAuth status message and "OAuth init OK"

**Step 4: Commit**

```bash
git add main.py
git commit -m "feat: add Google OAuth provider initialization

- Load credentials from environment variables
- Initialize GoogleProvider if credentials present
- Optional auth (backward compatible with local mode)
- Pass auth_provider to FastMCP initialization
- Print status message on startup"
```

---

## Task 5: Add Helper Tools (Auth Info & Disconnect)

**Files:**
- Modify: `main.py` (add new tools after existing tool definitions, around line 4100)
- Test: `tests/test_google_auth.py` (append)

**Step 1: Write failing tests for helper tools**

Append to `tests/test_google_auth.py`:

```python
from main import get_my_auth_info, disconnect_my_session


class TestHelperTools:
    """Test helper tools for auth management."""

    @pytest.mark.asyncio
    async def test_get_my_auth_info_with_session(self, monkeypatch):
        """Test get_my_auth_info returns correct info."""
        monkeypatch.setattr(
            "main.get_authenticated_user_email",
            lambda: "test@example.com"
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
            "main.get_authenticated_user_email",
            lambda: "test@example.com"
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
            "main.get_authenticated_user_email",
            lambda: "test@example.com"
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
            "main.get_authenticated_user_email",
            lambda: "test@example.com"
        )

        telegram_clients.clear()

        result = await disconnect_my_session()

        assert result["success"] is True
        assert "No active session" in result["message"]
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_google_auth.py::TestHelperTools -xvs`

Expected: FAIL with "cannot import name 'get_my_auth_info'" or similar

**Step 3: Implement helper tools**

Add to `main.py` after existing tool definitions (around line 4100):

```python
@mcp.tool()
async def get_my_auth_info() -> dict:
    """
    Get information about your authentication status.

    Shows your Google email and whether you have a Telegram session configured.
    If no session exists, provides link to /setup UI.

    Returns:
        Dict with authentication status and setup instructions if needed
    """
    try:
        user_email = get_authenticated_user_email()
        has_session = session_manager.session_exists(user_email)

        return {
            "success": True,
            "google_email": user_email,
            "has_telegram_session": has_session,
            "setup_url": "/setup" if not has_session else None,
            "message": "Ready to use Telegram tools" if has_session
                      else "Visit /setup to connect your Telegram account"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def disconnect_my_session() -> dict:
    """
    Disconnect your cached Telegram client.

    Forces reconnection on next tool use. Useful for troubleshooting
    connection issues or switching sessions.

    Returns:
        Dict with success status and message
    """
    try:
        user_email = get_authenticated_user_email()

        if user_email in telegram_clients:
            client = telegram_clients[user_email]
            await client.disconnect()
            del telegram_clients[user_email]
            return {
                "success": True,
                "message": "Session disconnected. Will reconnect on next tool use."
            }

        return {
            "success": True,
            "message": "No active session to disconnect."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_google_auth.py -xvs`

Expected: PASS (13 tests total)

**Step 5: Commit**

```bash
git add main.py tests/test_google_auth.py
git commit -m "feat: add auth helper tools

- get_my_auth_info: check auth status and session existence
- disconnect_my_session: force client reconnection
- Helpful for users to verify setup and troubleshoot
- Comprehensive test coverage"
```

---

## Task 6: Update Existing Tools with Decorator (Batch 1: Chat Tools)

**Files:**
- Modify: `main.py` (update first ~15 tools, around lines 300-800)

**Step 1: Update send_message tool**

Find the `send_message` tool (around line 300):

```python
# OLD CODE:
@mcp.tool()
@validate_id("chat_id")
async def send_message(
    chat_id: Union[int, str],
    message: str,
    ...
) -> dict:
    """Send a message to a chat."""
    try:
        global client
        # ... rest of function
```

Replace with:

```python
# NEW CODE:
@mcp.tool()
@with_telegram_client
@validate_id("chat_id")
async def send_message(
    client: TelegramClient,  # NEW: injected by decorator
    chat_id: Union[int, str],
    message: str,
    ...
) -> dict:
    """Send a message to a chat."""
    try:
        # Remove: global client
        # ... rest of function (no changes needed)
```

**Step 2: Apply same pattern to these chat tools:**

Update the following tools with the same pattern (add `@with_telegram_client`, add `client` parameter, remove `global client`):

- `get_chats` (line ~350)
- `get_messages` (line ~400)
- `reply_to_message` (line ~450)
- `edit_message` (line ~500)
- `delete_message` (line ~550)
- `forward_message` (line ~600)
- `pin_message` (line ~650)
- `unpin_message` (line ~700)
- `get_chat` (line ~750)
- `leave_chat` (line ~800)
- `archive_chat` (line ~850)
- `unarchive_chat` (line ~900)
- `mute_chat` (line ~950)
- `unmute_chat` (line ~1000)
- `read_history` (line ~1050)

**Step 3: Test updated tools**

Run: `uv run pytest tests/test_tools.py::TestChatTools -xvs`

Expected: PASS (existing tests should still work)

**Step 4: Commit**

```bash
git add main.py
git commit -m "refactor: migrate chat tools to use @with_telegram_client

- Add decorator to 15 chat-related tools
- Add client parameter as first argument
- Remove global client references
- All existing tests pass"
```

---

## Task 7: Update Existing Tools with Decorator (Batch 2: Group Tools)

**Files:**
- Modify: `main.py` (update next ~15 tools, around lines 1100-1800)

**Step 1: Apply decorator pattern to group tools**

Update the following tools (add `@with_telegram_client`, add `client` parameter, remove `global client`):

- `create_group` (line ~1100)
- `get_participants` (line ~1150)
- `invite_to_group` (line ~1200)
- `remove_from_group` (line ~1250)
- `promote_admin` (line ~1300)
- `demote_admin` (line ~1350)
- `ban_user` (line ~1400)
- `unban_user` (line ~1450)
- `get_admins` (line ~1500)
- `update_group_title` (line ~1550)
- `update_group_description` (line ~1600)
- `get_group_invite_link` (line ~1650)
- `join_group_by_link` (line ~1700)
- `set_group_permissions` (line ~1750)
- `get_group_info` (line ~1800)

**Step 2: Test updated tools**

Run: `uv run pytest tests/test_tools.py::TestGroupTools -xvs`

Expected: PASS

**Step 3: Commit**

```bash
git add main.py
git commit -m "refactor: migrate group tools to use @with_telegram_client

- Add decorator to 15 group-related tools
- Add client parameter as first argument
- Remove global client references
- All existing tests pass"
```

---

## Task 8: Update Existing Tools with Decorator (Batch 3: Contact Tools)

**Files:**
- Modify: `main.py` (update next ~15 tools, around lines 1850-2500)

**Step 1: Apply decorator pattern to contact tools**

Update the following tools (same pattern as before):

- `list_contacts` (line ~1850)
- `add_contact` (line ~1900)
- `delete_contact` (line ~1950)
- `block_user` (line ~2000)
- `unblock_user` (line ~2050)
- `get_blocked_users` (line ~2100)
- `search_contacts` (line ~2150)
- `get_contact_ids` (line ~2200)
- `import_contacts` (line ~2250)
- `get_user` (line ~2300)
- `get_user_status` (line ~2350)
- `get_user_photos` (line ~2400)
- `resolve_username` (line ~2450)

**Step 2: Test updated tools**

Run: `uv run pytest tests/test_tools.py::TestContactTools -xvs`

Expected: PASS

**Step 3: Commit**

```bash
git add main.py
git commit -m "refactor: migrate contact tools to use @with_telegram_client

- Add decorator to 13 contact-related tools
- Add client parameter as first argument
- Remove global client references
- All existing tests pass"
```

---

## Task 9: Update Existing Tools with Decorator (Batch 4: Profile & Search Tools)

**Files:**
- Modify: `main.py` (update next ~15 tools, around lines 2550-3200)

**Step 1: Apply decorator pattern to profile and search tools**

Update the following tools:

- `get_me` (line ~2550)
- `update_profile` (line ~2600)
- `update_username` (line ~2650)
- `update_bio` (line ~2700)
- `search_public_chats` (line ~2750)
- `search_messages` (line ~2800)
- `search_global` (line ~2850)
- `get_common_chats` (line ~2900)
- `get_full_chat` (line ~2950)
- `subscribe_public_channel` (line ~3000)
- `unsubscribe_channel` (line ~3050)
- `create_channel` (line ~3100)
- `get_channel_participants` (line ~3150)

**Step 2: Test updated tools**

Run: `uv run pytest tests/test_tools.py::TestProfileTools tests/test_tools.py::TestSearchTools -xvs`

Expected: PASS

**Step 3: Commit**

```bash
git add main.py
git commit -m "refactor: migrate profile and search tools to @with_telegram_client

- Add decorator to 13 profile/search tools
- Add client parameter as first argument
- Remove global client references
- All existing tests pass"
```

---

## Task 10: Update Existing Tools with Decorator (Batch 5: Folder & Reaction Tools)

**Files:**
- Modify: `main.py` (update next ~15 tools, around lines 3250-3900)

**Step 1: Apply decorator pattern to folder and reaction tools**

Update the following tools:

- `list_folders` (line ~3250)
- `create_folder` (line ~3300)
- `update_folder` (line ~3350)
- `delete_folder` (line ~3400)
- `add_chat_to_folder` (line ~3450)
- `remove_chat_from_folder` (line ~3500)
- `send_reaction` (line ~3550)
- `remove_reaction` (line ~3600)
- `get_message_reactions` (line ~3650)
- `get_available_reactions` (line ~3700)
- `save_draft` (line ~3750)
- `get_drafts` (line ~3800)
- `clear_draft` (line ~3850)

**Step 2: Test updated tools**

Run: `uv run pytest tests/test_tools.py::TestFolderTools tests/test_tools.py::TestReactionTools -xvs`

Expected: PASS

**Step 3: Commit**

```bash
git add main.py
git commit -m "refactor: migrate folder and reaction tools to @with_telegram_client

- Add decorator to 13 folder/reaction/draft tools
- Add client parameter as first argument
- Remove global client references
- All existing tests pass"
```

---

## Task 11: Update Existing Tools with Decorator (Batch 6: Remaining Tools)

**Files:**
- Modify: `main.py` (update remaining tools, around lines 3950-4100)

**Step 1: Apply decorator pattern to remaining tools**

Update all remaining tools (approximately 20-30 tools):

- Privacy tools: `get_privacy_settings`, `set_privacy`, etc.
- Inline button tools: `list_inline_buttons`, `press_inline_button`
- Bot tools: `set_bot_commands`, `get_bot_commands`, etc.
- Any other tools not yet migrated

**Step 2: Run full test suite**

Run: `uv run pytest tests/test_tools.py -xvs`

Expected: PASS (all tool tests)

**Step 3: Commit**

```bash
git add main.py
git commit -m "refactor: migrate remaining tools to @with_telegram_client

- Add decorator to all remaining tools (~25 tools)
- Add client parameter as first argument
- Remove global client references
- Full test suite passes"
```

---

## Task 12: Remove Global Client Initialization from HTTP Mode

**Files:**
- Modify: `main.py` (_main_http function, around line 4350)

**Step 1: Update _main_http function**

Find the `_main_http` function (around line 4350):

```python
# OLD CODE:
async def _main_http(host: str, port: int) -> None:
    """Start HTTP server with optional session."""
    global client

    # Load from sessions.json first
    user_email, user_session = session_manager.get_any_session()
    if user_session:
        client = TelegramClient(StringSession(user_session), TELEGRAM_API_ID, TELEGRAM_API_HASH)
    else:
        client = TelegramClient(StringSession(), TELEGRAM_API_ID, TELEGRAM_API_HASH)

    # Connect client...
    await client.connect()
    ...
```

Replace with:

```python
# NEW CODE:
async def _main_http(host: str, port: int) -> None:
    """Start HTTP server with Google OAuth authentication."""
    print("\n" + "=" * 60)
    print("🚀 Telegram MCP Server (Multi-Tenant Mode)")
    print("=" * 60)
    print(f"📍 MCP endpoint: http://{host}:{port}/mcp")
    print(f"🔧 Setup UI: http://{host}:{port}/setup")
    if auth_provider:
        print(f"🔐 Auth: Google OAuth (multi-tenant)")
    else:
        print(f"⚠️  Auth: Disabled (local mode)")
    print("=" * 60 + "\n")

    # Add routes for /setup UI (still needed for session creation)
    app.routes.insert(0, Route("/setup", serve_setup_page))
    app.routes.insert(1, Route("/setup/send-code", send_code_endpoint, methods=["POST"]))
    app.routes.insert(2, Route("/setup/verify", verify_code_endpoint, methods=["POST"]))
    app.routes.insert(3, Route("/setup/verify-2fa", verify_2fa_endpoint, methods=["POST"]))

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    try:
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n❌ Error: Port {port} is already in use")
            print(f"Try a different port: uv run main.py --http --port {port + 1}\n")
        sys.exit(1)
```

**Step 2: Remove reload_telegram_client function**

Find and delete the `reload_telegram_client()` function (no longer needed).

Also remove calls to `reload_telegram_client()` in:
- `verify_code_endpoint` (line ~4260)
- `verify_2fa_endpoint` (line ~4320)

**Step 3: Test HTTP mode startup**

Run: `uv run main.py --http --port 8889 > /tmp/http_startup_test.log 2>&1 &`

Then check: `cat /tmp/http_startup_test.log`

Expected: Server starts, prints multi-tenant message, no errors

Kill the server: `pkill -f "main.py --http"`

**Step 4: Run full test suite**

Run: `uv run pytest -xvs`

Expected: PASS (all 118+ tests)

**Step 5: Commit**

```bash
git add main.py
git commit -m "refactor: remove global client from HTTP mode startup

- No longer initialize global client in _main_http
- Remove reload_telegram_client function (obsolete)
- Clients now loaded lazily per authenticated user
- Update startup messages for multi-tenant mode
- Keep /setup endpoints for session creation
- All tests pass"
```

---

## Task 13: Update Documentation

**Files:**
- Modify: `CLAUDE.md` (add OAuth section)
- Modify: `README.md` (if exists, update with OAuth setup)

**Step 1: Add OAuth section to CLAUDE.md**

Add new section after "Configuration Requirements":

```markdown
### Google OAuth Multi-Tenant Configuration (Optional)

**Enable Multi-Tenant Mode:**

When OAuth is enabled, each authenticated Google user automatically uses their own Telegram session based on their email address.

**Environment Variables** (add to `.env`):
```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
BASE_URL=http://localhost:8000  # Or your deployment URL
```

**Google Cloud Console Setup:**
1. Go to https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID (Web application)
3. Add authorized redirect URIs:
   - `https://claude.ai/api/mcp/auth_callback`
   - `http://localhost:*/auth/callback`
4. Copy Client ID and Client Secret to `.env`

**Multi-Tenant Flow:**
1. User connects from Claude with Google OAuth
2. First tool call checks sessions.json for their email
3. If no session: returns error with `/setup` link
4. User visits `/setup`, creates Telegram session
5. Session saved with their Google email as key
6. Subsequent tool calls use their cached client

**Helper Tools:**
- `get_my_auth_info` - Check auth status and session existence
- `disconnect_my_session` - Force client reconnection (troubleshooting)

**Note:** OAuth is optional. Without credentials, server runs in local mode (no authentication).
```

**Step 2: Update Recent Bug Fixes section**

Add new entry at the end of "Recent Bug Fixes":

```markdown
### Enhancement: Google OAuth Multi-Tenant Support (2026-02-05)
**Added**: True multi-tenant support via Google OAuth authentication.

**Features**:
- Each authenticated Google user uses their own Telegram session
- Per-user client caching with lazy loading
- Decorator pattern (`@with_telegram_client`) for clean integration
- Helper tools for auth status and troubleshooting
- Backward compatible (OAuth is optional)

**User Flow**:
1. Authenticate with Google via Claude
2. Call any Telegram tool
3. If no session: error with `/setup` link
4. Create session via `/setup` UI
5. All tools now work with your personal Telegram account

**Technical Details**:
- `telegram_clients` dict caches clients per email
- `get_user_client()` implements lazy loading
- Decorator handles auth/connection errors gracefully
- Sessions still stored in `sessions.json` (keyed by email)

**Commit**: Multiple commits in `feature/google-oauth-multi-tenant` branch
```

**Step 3: Commit documentation**

```bash
git add CLAUDE.md
git commit -m "docs: add Google OAuth multi-tenant configuration guide

- OAuth setup instructions
- Google Cloud Console configuration
- Multi-tenant flow explanation
- Helper tools documentation
- Update Recent Bug Fixes with new feature"
```

---

## Task 14: Integration Testing

**Files:**
- Create: `tests/test_integration_oauth.py`

**Step 1: Write integration tests**

Create `tests/test_integration_oauth.py`:

```python
"""Integration tests for Google OAuth multi-tenant functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from main import (
    get_authenticated_user_email,
    get_user_client,
    with_telegram_client,
    telegram_clients,
    send_message,
)


class TestMultiTenantIsolation:
    """Test that multiple users get isolated clients."""

    @pytest.mark.asyncio
    async def test_two_users_get_different_clients(self, monkeypatch):
        """Test two users with different emails get separate clients."""
        telegram_clients.clear()

        # Mock session_manager to return different sessions
        def mock_get_session(email):
            return f"session_for_{email}"

        mock_session_manager = Mock()
        mock_session_manager.get_session = mock_get_session
        monkeypatch.setattr("main.session_manager", mock_session_manager)

        # Mock TelegramClient to track instances
        created_clients = {}

        def mock_telegram_client(session, *args):
            client = Mock()
            client.connect = AsyncMock()
            client.is_user_authorized = AsyncMock(return_value=True)
            client.is_connected = Mock(return_value=True)
            created_clients[session.save()] = client
            return client

        monkeypatch.setattr("main.TelegramClient", mock_telegram_client)

        # Get clients for two different users
        client1 = await get_user_client("user1@example.com")
        client2 = await get_user_client("user2@example.com")

        # Should be different instances
        assert client1 != client2
        assert telegram_clients["user1@example.com"] == client1
        assert telegram_clients["user2@example.com"] == client2

    @pytest.mark.asyncio
    async def test_tool_uses_correct_user_client(self, monkeypatch):
        """Test that decorated tool uses the correct user's client."""
        telegram_clients.clear()

        # Track which client was used
        used_clients = []

        @with_telegram_client
        async def test_tool(client, arg):
            used_clients.append(client)
            return {"success": True, "arg": arg}

        # Mock auth to return user1
        def mock_auth_user1():
            return "user1@example.com"

        monkeypatch.setattr("main.get_authenticated_user_email", mock_auth_user1)

        # Mock get_user_client
        mock_client1 = Mock()
        async def mock_get_client1(email):
            return mock_client1
        monkeypatch.setattr("main.get_user_client", mock_get_client1)

        # Call tool as user1
        result1 = await test_tool("value1")
        assert result1["success"] is True
        assert used_clients[-1] == mock_client1

        # Now mock auth to return user2
        def mock_auth_user2():
            return "user2@example.com"

        monkeypatch.setattr("main.get_authenticated_user_email", mock_auth_user2)

        mock_client2 = Mock()
        async def mock_get_client2(email):
            return mock_client2
        monkeypatch.setattr("main.get_user_client", mock_get_client2)

        # Call tool as user2
        result2 = await test_tool("value2")
        assert result2["success"] is True
        assert used_clients[-1] == mock_client2

        # Should have used different clients
        assert used_clients[0] != used_clients[1]


class TestEndToEndFlow:
    """Test complete OAuth flow from auth to tool execution."""

    @pytest.mark.asyncio
    async def test_complete_flow_with_session(self, monkeypatch):
        """Test: auth → get client → call tool → success."""
        telegram_clients.clear()

        # 1. Mock OAuth auth
        monkeypatch.setattr(
            "main.get_authenticated_user_email",
            lambda: "test@example.com"
        )

        # 2. Mock session exists
        mock_session_manager = Mock()
        mock_session_manager.get_session = Mock(return_value="fake_session")
        monkeypatch.setattr("main.session_manager", mock_session_manager)

        # 3. Mock TelegramClient
        mock_client = Mock()
        mock_client.connect = AsyncMock()
        mock_client.is_user_authorized = AsyncMock(return_value=True)
        mock_client.is_connected = Mock(return_value=True)
        mock_client.send_message = AsyncMock()

        mock_result = Mock()
        mock_result.id = 12345
        mock_client.send_message.return_value = mock_result

        def mock_telegram_client(*args, **kwargs):
            return mock_client

        monkeypatch.setattr("main.TelegramClient", mock_telegram_client)

        # 4. Call actual send_message tool (decorated)
        result = await send_message(123, "Hello")

        # 5. Verify success
        assert result["success"] is True
        assert result["message_id"] == 12345
        mock_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_flow_without_session(self, monkeypatch):
        """Test: auth → no session → error with setup link."""
        telegram_clients.clear()

        # Mock OAuth auth
        monkeypatch.setattr(
            "main.get_authenticated_user_email",
            lambda: "test@example.com"
        )

        # Mock NO session exists
        mock_session_manager = Mock()
        mock_session_manager.get_session = Mock(return_value=None)
        monkeypatch.setattr("main.session_manager", mock_session_manager)

        # Call tool - should return error
        result = await send_message(123, "Hello")

        assert result["success"] is False
        assert "No Telegram session found" in result["error"]
        assert result["error_code"] == "AUTH_REQUIRED"
```

**Step 2: Run integration tests**

Run: `uv run pytest tests/test_integration_oauth.py -xvs`

Expected: PASS (all integration tests)

**Step 3: Run full test suite**

Run: `uv run pytest -xvs`

Expected: PASS (120+ tests including new integration tests)

**Step 4: Commit**

```bash
git add tests/test_integration_oauth.py
git commit -m "test: add integration tests for OAuth multi-tenant

- Test user isolation (different users get different clients)
- Test tool uses correct user's client
- Test end-to-end flow with session
- Test end-to-end flow without session (error case)
- All integration tests pass"
```

---

## Task 15: Final Verification and Merge Preparation

**Files:**
- Run all tests
- Format code
- Lint code

**Step 1: Run complete test suite**

Run: `uv run pytest -v`

Expected: All tests pass (120+ tests)

**Step 2: Format code with Black**

Run: `uv run black main.py tests/*.py`

Expected: Files formatted

**Step 3: Lint with flake8**

Run: `uv run flake8 main.py tests/test_google_auth.py tests/test_integration_oauth.py`

Expected: No errors (or only acceptable warnings)

**Step 4: Manual smoke test**

Run: `uv run main.py --http --port 8889 > /tmp/smoke_test.log 2>&1 &`

Check logs: `tail -f /tmp/smoke_test.log`

Expected:
- Server starts successfully
- Prints "Multi-Tenant Mode" message
- Shows OAuth status

Kill server: `pkill -f "main.py --http"`

**Step 5: Final commit**

```bash
git add -A
git commit -m "chore: format and lint code

- Run black formatting on all modified files
- Fix any linting issues
- Ready for code review and merge"
```

**Step 6: Push branch**

```bash
git push origin feature/google-oauth-multi-tenant
```

---

## Summary

**Total Tasks:** 15 tasks
**Estimated Time:** 2-3 hours for implementation + testing
**Test Coverage:** 120+ tests (existing + 20+ new)
**Lines Changed:** ~500 lines (add auth, update 91 tools, tests, docs)

**Key Milestones:**
1. ✅ Auth helpers and client management (Tasks 1-2)
2. ✅ Decorator pattern (Task 3)
3. ✅ OAuth provider setup (Task 4)
4. ✅ Helper tools (Task 5)
5. ✅ Migrate all 91 tools (Tasks 6-11)
6. ✅ Update startup logic (Task 12)
7. ✅ Documentation (Task 13)
8. ✅ Integration tests (Task 14)
9. ✅ Final verification (Task 15)

**Success Criteria:**
- All tests pass (120+ tests)
- All 91 tools use `@with_telegram_client` decorator
- No global `client` references in tools
- OAuth provider initialized correctly
- HTTP mode starts without global client
- Documentation updated with OAuth setup
- Code formatted and linted
- Branch ready for review

**Next Steps After Implementation:**
1. Create pull request from `feature/google-oauth-multi-tenant` to `remote-mcp`
2. Code review
3. Merge to `remote-mcp`
4. Deploy to Railway
5. Test with real Google OAuth credentials
6. Update production environment variables
