# AGENTS.md — Telegram MCP Server

## Project Overview

Telegram MCP server exposing 90+ tools via FastMCP + Telethon. Most implementation lives in `main.py`, with transport setup, OAuth, helpers, and tool implementations in the same module. Supports stdio (single-user) and HTTP (multi-tenant with Google OAuth) transport modes.

## Build & Run Commands

```bash
# Install dependencies
uv sync

# Run server (stdio mode — default)
uv run main.py

# Run server (HTTP mode)
uv run main.py --http --host 0.0.0.0 --port 8000

# Run server (HTTP mode with allowlisted file roots)
uv run main.py --http --host 0.0.0.0 --port 8000 /srv/telegram-files /srv/shared-media

# Generate Telegram session string (QR login or phone-code flow)
uv run session_string_generator.py
```

## Code Quality

```bash
# Format (Black, line-length 99, target py311)
uv run black main.py session_string_generator.py test_file_path_security.py

# Lint (flake8, max-line-length 99, max-complexity 10)
uv run flake8 main.py session_string_generator.py test_file_path_security.py
```

**Black config** (`pyproject.toml`): line-length=99, target-version py311.
**Flake8 config** (`pyproject.toml`): ignores E203, E501, W503. Excludes .git, __pycache__, .venv, build, dist.

## Testing

```bash
# Run all tests
uv run pytest -v

# Run a single test file
uv run pytest test_validation.py -v

# Run a single test class
uv run pytest test_tools.py::TestChatTools -v

# Run a single test function
uv run pytest test_validation.py::test_valid_integer_id -v

# Run with coverage
uv run pytest test_tools.py --cov=main --cov-report=html
```

**Test files** primarily live at the project root. Current root-level files include `test_file_path_security.py`; additional coverage also exists under `tests/`.

**Test pattern**: pytest + pytest-asyncio. Tests that import `main` should set `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` before import. Async tools use `@pytest.mark.asyncio`. Mocking is mostly via `unittest.mock` (`AsyncMock`, `MagicMock`, `patch`).

## File Structure

| File | Purpose |
|---|---|
| `main.py` | All 94 MCP tool implementations, server setup, auth, decorators, helpers |
| `session_manager.py` | Multi-tenant session CRUD with file locking (`sessions.json`) |
| `session_string_generator.py` | CLI tool to generate Telegram session strings via QR or phone-code login |
| `templates/setup.html` | Web UI for browser-based Telegram session setup (HTTP mode) |
| `test_file_path_security.py` | Coverage for allowlisted-root and path traversal protections |
| `test_*.py`, `tests/` | Additional tests |

## Code Style

### Imports
Order: stdlib → third-party → local. Separated by blank lines with section comments:
```python
import os
import json
from typing import List, Dict, Optional, Union, Any

# Third-party libraries
from dotenv import load_dotenv
from telethon import TelegramClient, functions, utils

# Local
from session_manager import session_manager
```

### Naming
- **Functions/variables**: `snake_case` (`get_chats`, `format_entity`, `chat_id`)
- **Classes**: `PascalCase` (`SessionManager`, `ValidationError`, `ErrorCategory`)
- **Constants**: `UPPER_SNAKE_CASE` (`TELEGRAM_API_ID`, `SESSION_STRING`, `BASE_URL`)
- **Error codes**: `PREFIX-ERR-NNN` format (`CHAT-ERR-001`, `SENDMSG-ERR-001`)

### Type Hints
Use `typing` module types (`Union[int, str]`, `Optional[str]`, `List[Dict]`). All tool functions have parameter type hints and return type annotations (typically `-> str`).

### Tool Implementation Pattern
Every tool follows this exact decorator stack and structure:
```python
@mcp.tool(annotations=ToolAnnotations(title="Tool Name", openWorldHint=True, readOnlyHint=True))
@with_telegram_client
@validate_id("chat_id")  # only for tools accepting chat_id/user_id
async def tool_name(client, chat_id: Union[int, str], ...) -> str:
    """
    Docstring with Args block.
    Args:
        chat_id: The ID or username of the chat.
    """
    try:
        entity = await resolve_entity(client, chat_id)
        # ... tool logic ...
        return "Success message" or "\n".join(lines)
    except Exception as e:
        return log_and_format_error("tool_name", e, chat_id=chat_id)
```

**Decorator order matters**: `@mcp.tool()` → `@with_telegram_client` → `@validate_id()`.
`@with_telegram_client` injects `client` as the first argument (hidden from MCP signature).
`@validate_id()` normalizes int IDs, string IDs, and `@username` formats.

### Error Handling
- **Centralized**: `log_and_format_error(function_name, error, prefix=..., **context)` logs to `mcp_errors.log` (JSON format) and returns a sanitized user-facing message.
- **ErrorCategory enum**: CHAT, MSG, CONTACT, GROUP, MEDIA, PROFILE, AUTH, ADMIN, FOLDER.
- **Pattern**: Wrap tool body in `try/except Exception as e`, return `log_and_format_error()`.
- **Never expose raw exceptions** to users — always use error codes.
- **ValidationError**: Custom exception for input validation failures.

### Docstrings
All tools use imperative docstrings with `Args:` blocks (Google style). Helpers use single-line or short multi-line docstrings.

### Return Values
- Tools return `str` (human-readable) or occasionally `dict` (JSON-serializable).
- Success: descriptive string (`"Message sent successfully."`) or `"\n".join(lines)` for lists.
- Error: result of `log_and_format_error()` — never raise from tools.

## Key Architectural Patterns

- **Multi-tenant OAuth**: `@with_telegram_client` extracts user email from OAuth token, loads per-user Telegram client from `sessions.json` cache.
- **Entity resolution helpers**: use `resolve_entity()` / `resolve_input_entity()` instead of raw Telethon lookups when possible so StringSession caches can self-heal after reconnects.
- **Input validation**: `@validate_id()` decorator normalizes integer IDs, string IDs, and `@username` strings. Validates ranges (int64).
- **Helper functions**: `format_entity()`, `format_message()`, `get_sender_name()`, `get_engagement_info()` for consistent formatting.
- **File locking**: `session_manager.py` uses `fcntl.flock()` for concurrent session access.
- **File-path hardening**: file-based tools (`send_file`, `download_media`, profile/chat photo uploads, stickers, voice) are allowlist-gated via MCP roots or positional server roots. Reads/writes should go through the safe path helpers.
- **Graceful fallbacks**: Critical operations (e.g., `get_invite_link`) implement multiple fallback methods.

## Environment Variables

Required in `.env`:
- `TELEGRAM_API_ID` — from my.telegram.org/apps
- `TELEGRAM_API_HASH` — from my.telegram.org/apps
- `TELEGRAM_SESSION_STRING` — generated via `session_string_generator.py` (stdio mode)
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — for multi-tenant HTTP mode (optional)
- `BASE_URL` — server base URL for OAuth (optional, defaults to localhost:8000)

Recommended for production HTTP deployments:
- `FASTMCP_JWT_SIGNING_KEY` — stable signing key so OAuth-issued JWTs survive restarts
- `OAUTH_STORAGE_PATH` — encrypted OAuth persistence directory
- `SESSIONS_STORAGE_PATH` — persistent directory for `sessions.json`

**Never commit `.env`, session strings, or `sessions.json`.**

## CI/CD

GitHub Actions (`.github/workflows/python-lint-format.yml`):
- Runs on push/PR to `main`
- Python 3.11, flake8 lint + black format check
- Note: CI uses `--max-line-length=88` (Black default) while local config uses 99 — follow **99** locally

## Common Pitfalls

- All test files must set `os.environ["TELEGRAM_API_ID"]` and `os.environ["TELEGRAM_API_HASH"]` **before** `import main`.
- The `client` parameter in tool functions is injected by `@with_telegram_client` — never pass it manually in tool signatures exposed to MCP.
- File-based tools exist again, but they should only resolve paths through the safe root helpers and must not bypass the allowlist.
- `download_media()` intentionally strips a user-supplied suffix before calling Telethon so the final file extension matches the downloaded media type.
- GIF tools removed due to Telethon reliability issues.
- Use string sessions over file-based sessions to avoid SQLite lock issues.
