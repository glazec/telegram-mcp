# Google OAuth Multi-Tenant Authentication Design

**Date:** 2026-02-05
**Status:** Approved
**Author:** Claude Sonnet 4.5

## Overview

Add Google OAuth authentication to the Telegram MCP server to enable true multi-tenant support. Each authenticated Google user will automatically use their own Telegram session based on their email address.

## Current State

- Server loads single session from `sessions.json` (first available)
- All MCP clients share the same Telegram account
- No user isolation or multi-tenancy

## Goals

- Authenticate users via Google OAuth
- Each user's Google email maps to their Telegram session
- Lazy-load and cache Telegram clients per user
- Minimal changes to existing tool implementations
- Maintain backward compatibility with `/setup` UI

## Architecture

### 1. Authentication Setup

Add Google OAuth provider to FastMCP initialization:

```python
from fastmcp.server.auth import GoogleProvider

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

auth_provider = None
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
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

mcp = FastMCP(
    name="telegram",
    auth=auth_provider,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    ),
)
```

**Environment Variables:**
- `GOOGLE_CLIENT_ID` - Google OAuth Client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth Client Secret
- `BASE_URL` - Deployment URL (Railway, localhost, etc.)

### 2. Client Management (Hybrid Caching)

Replace global `client` with per-user cache:

```python
# Global cache: {email: TelegramClient}
telegram_clients: Dict[str, TelegramClient] = {}

async def get_user_client(user_email: str) -> TelegramClient:
    """
    Get or create a Telegram client for the authenticated user.

    - Checks cache first (fast path)
    - Loads session from sessions.json (lazy initialization)
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

**Cleanup Strategy:**
- Clients stay cached until server restart
- Automatic reconnection on cache hit with disconnected client
- Optional manual disconnect tool for troubleshooting

### 3. Auth Helper Functions

```python
from fastmcp.server.dependencies import get_access_token

def get_authenticated_user_email() -> str:
    """
    Extract the authenticated user's email from the OAuth token.

    Returns:
        User's email address

    Raises:
        ValueError: If no auth token or email not in token
    """
    try:
        token = get_access_token()
        email = token.claims.get("email")
        if not email:
            raise ValueError("Email not found in authentication token")
        return email
    except Exception as e:
        raise ValueError(f"Authentication required: {str(e)}")
```

### 4. Decorator Pattern

Create a decorator to inject authenticated client into all tools:

```python
from functools import wraps
from typing import Callable

def with_telegram_client(func: Callable) -> Callable:
    """
    Decorator that injects authenticated user's Telegram client into tool functions.

    Usage:
        @mcp.tool()
        @with_telegram_client
        async def send_message(client: TelegramClient, chat_id: str, message: str):
            result = await client.send_message(chat_id, message)
            return {"success": True, "message_id": result.id}
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

**Tool Update Pattern:**

```python
# Before:
@mcp.tool()
async def send_message(chat_id: Union[int, str], message: str) -> dict:
    global client  # Uses global client
    result = await client.send_message(chat_id, message)
    return {"success": True, "message_id": result.id}

# After:
@mcp.tool()
@with_telegram_client
async def send_message(client: TelegramClient, chat_id: Union[int, str], message: str) -> dict:
    # Client injected by decorator
    result = await client.send_message(chat_id, message)
    return {"success": True, "message_id": result.id}
```

### 5. Startup Logic Changes

**HTTP Mode Initialization:**

```python
async def _main_http(host: str, port: int) -> None:
    """Start HTTP server with Google OAuth authentication."""
    print("\n" + "=" * 60)
    print("🚀 Telegram MCP Server (Multi-Tenant Mode)")
    print("=" * 60)
    print(f"📍 MCP endpoint: http://{host}:{port}/mcp")
    print(f"🔧 Setup UI: http://{host}:{port}/setup")
    print(f"🔐 Auth: Google OAuth (multi-tenant)")
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

**Key Changes:**
- Remove global `client` initialization
- Remove `reload_telegram_client()` function (no longer needed)
- Keep `/setup` endpoints (users still create sessions there)
- Sessions are now per-user, loaded lazily

## Error Handling

### Error Scenarios

1. **User not authenticated:**
   - Returns: `{"success": False, "error": "Authentication required", "error_code": "AUTH_REQUIRED"}`

2. **User has no Telegram session:**
   - Returns: `{"success": False, "error": "No Telegram session found for user@example.com. Please visit /setup", "error_code": "AUTH_REQUIRED"}`

3. **Session expired/invalid:**
   - Returns: `{"success": False, "error": "Session invalid for user@example.com", "error_code": "CONNECTION_FAILED"}`

4. **Client disconnected mid-operation:**
   - Automatically reconnects by removing from cache and recreating

### Helper Tools

**Auth Info Tool:**
```python
@mcp.tool()
async def get_my_auth_info() -> dict:
    """Get information about your authentication status."""
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
        return {"success": False, "error": str(e)}
```

**Disconnect Tool (Optional):**
```python
@mcp.tool()
async def disconnect_my_session() -> dict:
    """Disconnect your cached Telegram client (forces reconnect on next use)."""
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

        return {"success": True, "message": "No active session to disconnect."}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## User Flow

1. **Initial Connection:**
   - User connects from Claude with Google OAuth
   - MCP server receives authenticated request with Google email

2. **First Tool Call:**
   - Decorator extracts email from token
   - `get_user_client()` checks sessions.json
   - If no session: error with `/setup` URL

3. **Session Creation:**
   - User visits `/setup` in browser
   - Authenticates with Telegram (phone + code + 2FA)
   - Session saved to sessions.json with their Google email

4. **Subsequent Tool Calls:**
   - `get_user_client()` loads session from sessions.json
   - Creates TelegramClient, connects, caches
   - All future calls reuse cached client

## Implementation Tasks

1. **Environment Configuration:**
   - ✅ Update `.env` and `.env.example` with Google OAuth variables

2. **Core Functions:**
   - Add `get_authenticated_user_email()` helper
   - Add `get_user_client(email)` with caching
   - Replace global `client` with `telegram_clients` dict

3. **Decorator:**
   - Implement `@with_telegram_client` decorator
   - Add error handling for auth/connection failures

4. **Tool Updates:**
   - Update all 80+ tools with decorator
   - Add `client` parameter as first argument
   - Remove global `client` references

5. **Startup Changes:**
   - Add Google OAuth provider initialization
   - Remove global client initialization from `_main_http()`
   - Remove `reload_telegram_client()` function
   - Update startup messages

6. **Helper Tools:**
   - Add `get_my_auth_info()` tool
   - Add `disconnect_my_session()` tool (optional)

7. **Testing:**
   - Unit tests for auth helpers
   - Unit tests for client management
   - Unit tests for decorator
   - Integration tests for multi-user isolation
   - Manual testing with multiple Google accounts

8. **Documentation:**
   - Update CLAUDE.md with OAuth setup instructions
   - Update README with Google OAuth configuration
   - Add troubleshooting guide for auth issues

## Testing Strategy

### Unit Tests
- `test_get_authenticated_user_email()` - Extract email from token
- `test_get_user_client_cache_hit()` - Client reused from cache
- `test_get_user_client_cache_miss()` - Client created when not cached
- `test_get_user_client_no_session()` - Error when no session
- `test_with_telegram_client_decorator()` - Decorator injects client

### Integration Tests
- `test_multi_user_isolation()` - Two users get different clients
- `test_user_session_lookup()` - Correct session loaded per user

### Manual Testing
1. Start server: `uv run main.py --http`
2. Connect from Claude with Google OAuth
3. Call `get_my_auth_info` - should show "no session"
4. Visit `/setup`, authenticate Telegram
5. Call `get_my_auth_info` - should show "ready"
6. Call Telegram tools - should work with your session
7. Test with second Google account - should get separate session

## Rollout Plan

1. **Phase 1: Core Implementation**
   - Add auth helpers and client management
   - Implement decorator
   - Test with single user

2. **Phase 2: Tool Migration**
   - Update all 80+ tools with decorator
   - Remove global client references
   - Test tools work with auth

3. **Phase 3: Multi-Tenant Testing**
   - Test with multiple Google accounts
   - Verify session isolation
   - Load testing with concurrent users

4. **Phase 4: Documentation & Deployment**
   - Update all documentation
   - Deploy to Railway
   - Monitor for auth issues

## Backward Compatibility

- `/setup` UI continues to work unchanged
- Existing sessions in `sessions.json` are compatible
- stdio mode can remain unauthenticated (for local use)
- HTTP mode requires OAuth (multi-tenant mode)

## Security Considerations

- Google OAuth tokens verified by FastMCP
- Session strings remain secure in sessions.json
- Each user can only access their own Telegram session
- No cross-user data leakage via cached clients
- Email-based session lookup provides strong isolation

## Future Enhancements

- Periodic cleanup of idle cached clients
- Session expiration/refresh logic
- Admin tools for session management
- Metrics/logging for auth failures
- Rate limiting per user
