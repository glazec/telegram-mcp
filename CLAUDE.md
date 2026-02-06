# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram MCP (Model Context Protocol) server that provides comprehensive Telegram integration for Claude, Cursor, and any MCP-compatible client. The server exposes 80+ Telegram tools powered by Telethon, enabling programmatic interaction with Telegram accounts including messaging, group management, contact handling, and media operations.

## Development Commands

### Environment Setup
```bash
# Install dependencies
uv sync

# Generate session string for authentication
uv run session_string_generator.py
```

### Running the Server
```bash
# Run locally with stdio (default, for Claude Desktop/Cursor)
uv run main.py

# Run with HTTP transport (for remote VPS access)
uv run main.py --http --host 0.0.0.0 --port 8000

# Custom port
uv run main.py --http --port 9000

# View all options
python main.py --help

# Docker build
docker build -t telegram-mcp:latest .

# Docker Compose (recommended for local testing)
docker compose up --build

# Docker run with manual env vars
docker run -it --rm \
  -e TELEGRAM_API_ID="YOUR_API_ID" \
  -e TELEGRAM_API_HASH="YOUR_API_HASH" \
  -e TELEGRAM_SESSION_STRING="YOUR_SESSION_STRING" \
  telegram-mcp:latest
```

### Code Quality
```bash
# Format code with Black (line length: 99)
uv run black main.py session_string_generator.py test_validation.py

# Lint with flake8 (configured in pyproject.toml)
uv run flake8 main.py session_string_generator.py
```

## Architecture

### Core Components

**main.py** (primary server file):
- MCP server implementation using FastMCP
- 80+ Telegram tool implementations using Telethon
- Dual session support: string-based (portable) and file-based
- Comprehensive error handling with structured JSON logging to `mcp_errors.log`
- Input validation decorator for chat_id/user_id parameters

**session_string_generator.py**:
- Interactive CLI tool for generating portable session strings
- Handles Telegram authentication flow
- Can auto-update `.env` file with generated session string

**session_manager.py** (multi-tenant session storage):
- Manages session storage in `sessions.json` for multiple users
- Provides CRUD operations: get_session, save_session, delete_session, session_exists
- Uses file locking to prevent race conditions
- Sessions mapped by email address

**templates/setup.html** (web UI for session management):
- Browser-based session setup interface (available in HTTP mode at `/setup`)
- Multi-step flow: email → phone number → verification code → 2FA password (if enabled)
- Automatically saves session to `sessions.json`
- Eliminates need for CLI-based session generation when deployed remotely

**Authentication**:
The server supports multiple authentication and session modes:

**HTTP Mode (Multi-Tenant with Google OAuth):**
- Google OAuth authentication for user identification
- Each user's Google email maps to their Telegram session in `sessions.json`
- Per-user Telegram clients with caching and lazy loading
- Automatic session isolation - users can only access their own Telegram account
- No server restart needed when users create new sessions via `/setup`

**stdio Mode (Single-User):**
1. **TELEGRAM_SESSION_STRING** (recommended): String session from environment variable
2. **TELEGRAM_SESSION_NAME** (legacy): File-based session

String sessions are preferred to avoid database lock issues and enable containerized deployments.

### Google OAuth Multi-Tenant Setup

**Prerequisites:**
1. Create a Google OAuth 2.0 Client ID:
   - Go to https://console.cloud.google.com/apis/credentials
   - Create OAuth 2.0 Client ID (Web application)
   - Add authorized redirect URIs:
     - `https://claude.ai/api/mcp/auth_callback` (for Claude Desktop)
     - `http://localhost:*` (for local testing)
   - Copy Client ID and Client Secret

2. Configure environment variables in `.env`:
```env
# Required for Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
BASE_URL=http://localhost:8000  # Or your deployment URL (e.g., https://your-app.railway.app)

# Required for Telegram
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
```

**User Flow:**
1. User connects from Claude with Google OAuth authentication
2. Server authenticates user and extracts email from OAuth token
3. On first tool call, server checks if user has a Telegram session
4. If no session: error message directs user to visit `/setup`
5. User visits `/setup` URL in browser and authenticates with Telegram
6. Session saved to `sessions.json` with user's email as key
7. Subsequent tool calls automatically use user's cached Telegram client

**Architecture:**
- `@with_telegram_client` decorator on all 94 tools
- Decorator extracts user email from OAuth token
- `get_user_client(email)` manages per-user client cache
- Per-user locks prevent race conditions
- Automatic reconnection on cache hit with disconnected client

### Key Architectural Patterns

**Input Validation**:
All tools accepting `chat_id` or `user_id` use the `@validate_id()` decorator which normalizes:
- Integer IDs (e.g., `123456789`, `-1001234567890`)
- String IDs (e.g., `"123456789"`)
- Usernames (e.g., `"@username"` or `"username"`)

**Error Handling**:
- Custom `log_and_format_error()` function categorizes errors into ERROR_CATEGORY enum
- All exceptions logged to `mcp_errors.log` with JSON formatting (pythonjsonlogger)
- User-facing error messages are sanitized with error codes (e.g., `SENDMSG-ERR-001`)
- Graceful degradation with multiple fallback approaches for critical functions

**Tool Categories** (80+ tools organized by function):
1. **Chat & Group Management**: get_chats, create_group, invite_to_group, get_participants, promote_admin, etc.
2. **Messaging**: send_message, reply_to_message, edit_message, forward_message, pin_message, etc.
3. **Contact Management**: list_contacts, add_contact, block_user, import_contacts, etc.
4. **User & Profile**: get_me, update_profile, get_user_status, etc.
5. **Search & Discovery**: search_public_chats, search_messages, resolve_username
6. **Folders**: list_folders, create_folder, update_folder, delete_folder, add_chat_to_folder, etc.
7. **Reactions & Engagement**: send_reaction, remove_reaction, get_message_reactions
8. **Drafts**: save_draft, get_drafts, clear_draft
9. **Privacy & Settings**: mute_chat, archive_chat, get_privacy_settings, etc.

**Transport Modes**:
The server supports dual transport modes:
- **stdio mode** (default): Uses stdin/stdout for local MCP clients like Claude Desktop
- **HTTP mode**: Uses Streamable HTTP protocol for remote connections via uvicorn ASGI server

Transport selection via command-line flags:
- Default behavior (no flags): stdio mode
- `--http` flag: HTTP mode on 0.0.0.0:8000
- `--host` and `--port`: Customize HTTP binding

Environment variables:
- `MCP_HTTP_HOST`: Default host for HTTP mode (default: 0.0.0.0)
- `MCP_HTTP_PORT`: Default port for HTTP mode (default: 8000)

HTTP mode implementation:
- Uses FastMCP's `streamable_http_app()` to generate ASGI application
- Runs with uvicorn server for production-ready HTTP handling
- Supports concurrent client connections
- Works with FastMCP 3.0.0b1 (beta) which uses uvicorn for HTTP transport
- DNS rebinding protection disabled to allow connections from localhost, Railway, etc.

HTTP mode endpoints:
- `/mcp` - MCP protocol endpoint for tool calls
- `/setup` - Web UI for Telegram session setup
- `/setup/send-code` - API endpoint to initiate authentication
- `/setup/verify` - API endpoint to verify code and save session
- `/setup/verify-2fa` - API endpoint for 2FA password verification

### Removed Functionality

File-based tools have been removed due to MCP environment limitations:
- `send_file`, `download_media`, `set_profile_photo`, `edit_chat_photo`
- `send_voice`, `send_sticker`, `upload_file`
- GIF tools (`get_gif_search`, `get_saved_gifs`, `send_gif`) removed due to Telethon reliability issues

### Configuration Requirements

**Environment Variables** (in `.env` file):
```
TELEGRAM_API_ID=your_api_id_here          # From my.telegram.org/apps
TELEGRAM_API_HASH=your_api_hash_here      # From my.telegram.org/apps
TELEGRAM_SESSION_STRING=your_session_here # Generate with session_string_generator.py
# OR (legacy file-based):
TELEGRAM_SESSION_NAME=anon                # For file-based sessions
```

**MCP Client Configuration** (Claude Desktop or Cursor):
```json
{
  "mcpServers": {
    "telegram-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/full/path/to/telegram-mcp",
        "run",
        "main.py"
      ]
    }
  }
}
```

## Recent Bug Fixes (2026-02-04/05)

### Fix 1: Non-Interactive HTTP Mode
**Problem**: Server prompted for phone input when started with `--http` flag, blocking deployment.
```
Please enter your phone (or bot token):
```

**Root Cause**: Used `await client.start()` which is interactive.

**Solution**: Changed to non-interactive flow:
- Uses `await client.connect()` instead of `await client.start()`
- Checks authorization with `await client.is_user_authorized()`
- Server starts gracefully without session, directing users to `/setup`

**Commit**: `3a83d7f` - "fix: make HTTP mode non-interactive and add /setup endpoints"

---

### Fix 2: Client Not Reconnecting After /setup Authentication
**Problem**: After authenticating via `/setup` UI, MCP tools failed with:
```
ConnectionError: Cannot send requests while disconnected
```

**Root Cause**: Global `client` was initialized at startup. When a new session was created via `/setup`, it was saved to `sessions.json` but the global client was never reconnected.

**Solution**: Added `reload_telegram_client()` function:
- Disconnects old client
- Loads latest session from `sessions.json`
- Creates new client with session
- Starts client and updates global variable
- Called automatically after successful authentication in both `/setup/verify` and `/setup/verify-2fa`

**Impact**: No restart needed after `/setup` authentication - client reconnects automatically.

**Commit**: `3a83d7f` - "fix: make HTTP mode non-interactive and add /setup endpoints"

---

### Fix 3: Missing Email in /setup/send-code Request
**Problem**: 400 Bad Request when sending verification code:
```
Email and phone are required
```

**Root Cause**: JavaScript only sent `{ phone }` but backend requires both `email` and `phone`.

**Solution**: Updated fetch call to include email:
```javascript
body: JSON.stringify({ email: userEmail, phone })
```

**Commit**: `6595a8c` - "fix: include email in /setup/send-code request"

---

### Fix 4: DNS Rebinding Protection Blocking MCP Inspector
**Problem**: 421 Misdirected Request when connecting via MCP Inspector or localhost:
```
StreamableHTTPError: Invalid Host header
```

**Root Cause**: FastMCP's DNS rebinding protection rejected requests with certain Host headers.

**Solution**: Disabled DNS rebinding protection:
```python
mcp = FastMCP(
    name="telegram",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    ),
)
```

**Impact**: Allows connections from localhost, 0.0.0.0, Railway URLs, and MCP Inspector.

**Commit**: `d9fceed` - "fix: disable DNS rebinding protection for MCP server"

---

### Enhancement: Debug Logging for 2FA Issues
**Added**: Detailed logging to diagnose 2FA verification failures:
- Logs email, phone, password presence
- Logs available phones in `pending_verifications`
- Logs when 2FA is triggered and client is kept alive
- Logs success and error cases with details

**Purpose**: Helps identify phone number format mismatches, session timeouts, or password validation issues.

**Commit**: `3d6c879` - "debug: add detailed logging to 2FA verification endpoint"

## Important Implementation Notes

### Inline Button Interaction
Two-step process for button automation:
1. `list_inline_buttons(chat_id, message_id)` - Discover button layout and indices
2. `press_inline_button(chat_id, message_id, button_text=None, button_index=None)` - Trigger callbacks

If `message_id` is omitted, the server searches recent messages for the latest inline keyboard.

### Invite Link Handling
`get_invite_link()` implements multiple fallback methods:
1. `ExportChatInviteRequest` (primary)
2. `export_chat_invite_link` (fallback)
3. `GetFullChatRequest` (last resort)

`join_chat_by_link()` handles various link formats and detects already-member cases.

### Account Type Detection
Some tools (e.g., `set_bot_commands`) are bot-only and will return clear error messages when used with regular user accounts.

### Folder Management (7 new tools)
Full support for Telegram folder operations including creating, updating, deleting folders and managing chat memberships.

### Message Engagement Metrics
Messages include engagement info via `get_engagement_info()`: views, forwards, reactions, and edit history.

## Troubleshooting

### HTTP Mode Issues

**Server Prompts for Phone Input**:
- **Cause**: Using old version before non-interactive fix
- **Fix**: Update to latest version (commit `3a83d7f` or later) and restart

**421 Misdirected Request / Invalid Host Header**:
- **Cause**: DNS rebinding protection enabled
- **Fix**: Update to latest version (commit `d9fceed` or later) with DNS protection disabled

**MCP Tools Fail After /setup Authentication**:
- **Cause**: Client not reconnecting after session creation
- **Fix**: Update to latest version (commit `3a83d7f` or later) with auto-reconnect

### /setup Web UI Issues

**400 Bad Request on "Send Code"**:
- **Symptom**: "Email and phone are required"
- **Cause**: Missing email in request (old version)
- **Fix**: Update to latest version (commit `6595a8c` or later)

**400 Bad Request on "Verify 2FA"**:
- **Common causes**:
  1. Phone number format mismatch (e.g., spaces in one step but not the other)
  2. Session expired (waited too long between steps)
  3. Server restarted between verify code and verify 2FA
  4. Wrong 2FA password
- **Diagnosis**: Check server logs for `[DEBUG]` and `[ERROR]` messages
- **Fix**: Restart from step 1, ensure phone format is consistent

### General Issues

**Database Lock Errors**: Use string session authentication instead of file-based sessions.

**Authentication Failures**: Regenerate session string if Telegram password changed, or use `/setup` UI to create a new session.

**No Session Error**:
- In HTTP mode: Server starts anyway! Visit `/setup` to create session - **no restart needed** (auto-reconnects)
- In stdio mode: Set `TELEGRAM_SESSION_STRING` in `.env` or run `session_string_generator.py`, then restart

**Two-Factor Authentication**: Fully supported! If 2FA is enabled, you'll be prompted for your cloud password after entering the verification code.

**Bot-Only Function Errors**: Certain tools require bot accounts - error messages will indicate this.

**Detailed Error Logs**: Check `mcp_errors.log` for structured JSON error logs with full context.

**iCloud/Dropbox Issues**: Move project to a local path without spaces.

### Google OAuth Multi-Tenant Issues

**"AUTH_REQUIRED" Error on Tool Calls**:
- **Symptom**: Tools return `{"success": false, "error": "Authentication required", "error_code": "AUTH_REQUIRED"}`
- **Cause**: No OAuth token in request OR user has no Telegram session
- **Fix**:
  1. Ensure Google OAuth is configured (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET in .env)
  2. Connect from Claude with OAuth authentication
  3. If authenticated but no session: Visit `/setup` to create Telegram session

**"No Telegram session found" Error**:
- **Symptom**: `No Telegram session found for user@example.com. Please visit /setup`
- **Cause**: User authenticated with Google OAuth but hasn't created Telegram session yet
- **Fix**: Visit http://your-server:port/setup in browser and authenticate with Telegram

**"CONNECTION_FAILED" Error**:
- **Symptom**: `{"success": false, "error": "Session invalid for user@example.com", "error_code": "CONNECTION_FAILED"}`
- **Cause**: Telegram session expired or invalidated
- **Fix**:
  1. Delete old session: Remove entry from `sessions.json`
  2. Visit `/setup` to create new session
  3. Or use `disconnect_my_session` tool to force reconnection

**Tools Work for One User But Not Another**:
- **Symptom**: Tools work for user A but return AUTH_REQUIRED for user B
- **Cause**: Multi-tenant isolation working correctly - user B needs their own session
- **Fix**: User B should visit `/setup` and authenticate with their Telegram account

**OAuth Disabled Warning**:
- **Symptom**: Server logs `⚠️  Auth: Disabled (set GOOGLE_CLIENT_ID/SECRET to enable)`
- **Cause**: Missing Google OAuth credentials in environment
- **Fix**:
  1. Create Google OAuth 2.0 Client ID (see setup instructions above)
  2. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env
  3. Restart server

**Client Cache Issues**:
- **Symptom**: Stale connection, tools timing out
- **Fix**: Use `disconnect_my_session` tool to clear cached client and force reconnection

**Session Isolation Concerns**:
- **Question**: Can users access each other's Telegram accounts?
- **Answer**: No. Each user's email from OAuth token maps to their own session in `sessions.json`. The decorator ensures users can ONLY access their own Telegram client.

## Security

- **Never commit `.env` or session strings** - they provide full account access
- Session strings are equivalent to account credentials
- All processing is local; no data sent anywhere except Telegram's official API
- Test files automatically excluded in `.gitignore`
