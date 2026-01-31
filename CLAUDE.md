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
# Run locally with uv
uv --directory /path/to/telegram-mcp run main.py

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

**Authentication**:
The server supports two session modes (configured via environment variables):
- **String sessions** (recommended): Portable, no file dependencies, set via `TELEGRAM_SESSION_STRING`
- **File sessions**: Traditional file-based, set via `TELEGRAM_SESSION_NAME`

String sessions are preferred to avoid database lock issues and enable containerized deployments.

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

**Database Lock Errors**: Use string session authentication instead of file-based sessions.

**Authentication Failures**: Regenerate session string if Telegram password changed.

**Bot-Only Function Errors**: Certain tools require bot accounts - error messages will indicate this.

**Detailed Error Logs**: Check `mcp_errors.log` for structured JSON error logs with full context.

**iCloud/Dropbox Issues**: Move project to a local path without spaces.

## Security

- **Never commit `.env` or session strings** - they provide full account access
- Session strings are equivalent to account credentials
- All processing is local; no data sent anywhere except Telegram's official API
- Test files automatically excluded in `.gitignore`
