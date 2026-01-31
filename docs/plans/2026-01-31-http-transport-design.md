# HTTP Transport Implementation Design

**Date:** 2026-01-31
**Status:** Approved
**Author:** Design Session with User

## Overview

Add HTTP transport support to the Telegram MCP server while maintaining backward compatibility with stdio transport. This enables remote deployment on VPS while keeping local Claude Desktop integration working.

## Requirements

- **Deployment Target:** VPS without authentication (for now)
- **Transport Support:** Both stdio (default) and HTTP
- **HTTP Method:** Streamable HTTP protocol (FastMCP standard)
- **Mode Selection:** Command-line flag (`--http`)
- **Backward Compatibility:** Existing stdio functionality must work unchanged

## Architecture

### Transport Dual-Mode Support

The server supports two transport modes:
1. **stdio mode** (default): Current behavior, communicates via stdin/stdout for local MCP clients
2. **http mode**: New Streamable HTTP transport for remote connections

### Mode Selection

Command-line argument parser using Python's `argparse`:
- Default: stdio mode (backward compatible)
- `--http` flag: HTTP mode
- Optional `--port` and `--host` arguments

### Code Structure

```python
async def _main_stdio():
    """Existing stdio logic"""
    await client.start()
    await mcp.run_stdio_async()

async def _main_http(host: str, port: int):
    """New HTTP logic"""
    await client.start()
    print(f"Running MCP server at http://{host}:{port}/mcp")
    mcp.run(transport="http", host=host, port=port)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--http', action='store_true')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()

    nest_asyncio.apply()
    if args.http:
        asyncio.run(_main_http(args.host, args.port))
    else:
        asyncio.run(_main_stdio())
```

## HTTP Implementation

### FastMCP HTTP Transport

FastMCP's `run()` method supports HTTP via Streamable HTTP protocol:

```python
mcp.run(transport="http", host="0.0.0.0", port=8000)
```

This creates an HTTP server accessible at `http://0.0.0.0:8000/mcp`.

### Integration Approach

Since Telethon client requires async initialization (`await client.start()`), we use the simpler direct `run()` call approach. This works because `nest_asyncio.apply()` is already in use, allowing synchronous calls within async contexts.

### Endpoints

When running in HTTP mode:
- **POST `/mcp`** - JSON-RPC endpoint for client requests
- **GET `/sse`** - SSE endpoint for streaming server responses
- Streamable HTTP protocol handles bidirectional communication automatically

### Request Flow

1. Client connects to `http://vps-ip:8000/sse` (keeps connection open)
2. Client sends tool calls via POST to `http://vps-ip:8000/mcp`
3. Server processes Telegram operations via Telethon
4. Server streams responses through SSE connection

## Configuration

### Command-Line Arguments

```python
parser.add_argument('--http', action='store_true',
    help='Run in HTTP mode instead of stdio')
parser.add_argument('--host',
    default=os.getenv('MCP_HTTP_HOST', '0.0.0.0'),
    help='HTTP server host')
parser.add_argument('--port', type=int,
    default=int(os.getenv('MCP_HTTP_PORT', '8000')),
    help='HTTP server port')
```

Command-line arguments override environment variables.

### Environment Variables

Add to `.env`:

```bash
# Existing
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890
TELEGRAM_SESSION_STRING=your_session_string

# New (optional)
MCP_HTTP_HOST=0.0.0.0
MCP_HTTP_PORT=8000
```

### Usage Examples

```bash
# Stdio mode (default, for Claude Desktop)
python main.py
uv run main.py

# HTTP mode with defaults
python main.py --http
uv run main.py --http

# HTTP mode with custom port
python main.py --http --port 9000

# HTTP mode with custom host and port
python main.py --http --host 127.0.0.1 --port 8000
```

## Documentation Updates

### README.md Changes

Add new section: **"HTTP Transport (Remote Access)"**
- Explain HTTP transport for remote/VPS deployment
- Command-line usage examples
- MCP client connection: `http://your-vps-ip:8000/mcp`
- Environment variables documentation

Update **"Running the Server"** section:
```bash
# Local mode (stdio) - for Claude Desktop/Cursor
uv run main.py

# Remote mode (HTTP) - for VPS deployment
uv run main.py --http --port 8000
```

### CLAUDE.md Changes

Update **"Running the Server"**:
```bash
# Run locally with stdio (default)
uv run main.py

# Run with HTTP transport (remote access)
uv run main.py --http --host 0.0.0.0 --port 8000

# Custom port
uv run main.py --http --port 9000
```

Update **"Architecture"** section:
- Dual transport support (stdio and HTTP)
- HTTP uses Streamable HTTP protocol
- Command-line arguments for transport selection
- New environment variables: `MCP_HTTP_HOST`, `MCP_HTTP_PORT`

## Error Handling

Existing error infrastructure works for both transports. Add HTTP-specific error handling:

```python
async def _main_http(host: str, port: int):
    try:
        await client.start()
        mcp.run(transport="http", host=host, port=port)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Error: Port {port} is already in use", file=sys.stderr)
        else:
            print(f"Error starting HTTP server: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

## Testing

### Test File: `server_test.py`

New integration test file for transport testing:

**TestStdioTransport:**
- `test_stdio_mode_starts` - Verify server starts without arguments
- `test_stdio_backward_compatibility` - Ensure Claude Desktop integration works

**TestHttpTransport:**
- `test_http_mode_starts` - Verify `--http` flag starts server
- `test_http_endpoint_accessible` - Check `/mcp` endpoint responds
- `test_custom_port` - Verify `--port` argument
- `test_custom_host` - Verify `--host` argument

**TestErrorHandling:**
- `test_port_already_in_use` - Graceful handling of occupied ports
- `test_invalid_port` - Validation for invalid ports
- `test_telegram_client_failure` - Handle Telegram auth failures

**TestToolFunctionality:**
- `test_send_message_stdio` - Core tool works in stdio mode
- `test_send_message_http` - Core tool works in HTTP mode

### Test Documentation: `test.md`

Update test files section:

```markdown
### `test_validation.py`
Tests input validation decorator system for chat_id/user_id normalization and edge cases.

### `test_tools.py`
Comprehensive unit tests for all 86 MCP tools with proper mocking and functional coverage.

### `server_test.py`
Integration tests for stdio and HTTP transport modes, server startup, and deployment scenarios.
```

### Testing Plan

1. **Local stdio testing** - Verify backward compatibility with Claude Desktop
2. **Local HTTP testing** - Test `http://localhost:8000/mcp`
3. **VPS HTTP testing** - Test from remote client to VPS
4. **Tool functionality** - Test core tools (send_message, get_chats) in both modes
5. **Error scenarios** - Verify error handling for port conflicts, auth failures

## Dependencies

No new dependencies required. FastMCP already includes HTTP transport support. All packages in `pyproject.toml` are sufficient.

## Implementation Notes

- Keep both `_main_stdio()` and `_main_http()` functions cleanly separated
- Use `nest_asyncio.apply()` (already in codebase) for async/sync compatibility
- Maintain all existing stdio functionality unchanged
- HTTP mode uses FastMCP's built-in Streamable HTTP transport
- Authentication can be added later as a separate feature

## VPS Deployment

```bash
# Clone repository on VPS
git clone <repo-url>
cd telegram-mcp

# Set up environment
uv sync
cp .env.example .env
# Edit .env with your credentials

# Run in HTTP mode
uv run main.py --http --host 0.0.0.0 --port 8000

# Optional: Set up as systemd service for auto-restart
```

Ensure firewall allows port 8000:
```bash
sudo ufw allow 8000/tcp
```

## Future Enhancements

- Authentication (API keys, bearer tokens)
- HTTPS/TLS support
- Rate limiting
- Multiple concurrent sessions
- Health check endpoint (`/health`)
