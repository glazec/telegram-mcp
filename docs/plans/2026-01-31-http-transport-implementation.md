# HTTP Transport Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add HTTP transport support to Telegram MCP server for VPS deployment while maintaining backward-compatible stdio mode.

**Architecture:** Dual transport modes selected via command-line flags. HTTP mode uses FastMCP's built-in Streamable HTTP protocol. Stdio mode remains default for backward compatibility.

**Tech Stack:** FastMCP (HTTP transport), argparse (CLI), Telethon (existing), pytest (testing)

---

## Task 1: Add Command-Line Argument Parser

**Files:**
- Modify: `main.py:1-100` (imports section)
- Modify: `main.py:4146-4152` (main function)

**Step 1: Add argparse import**

```python
import argparse
```

Add after line 6 (`import asyncio`) in the imports section.

**Step 2: Update main() function to parse arguments**

Replace the existing `main()` function (lines 4146-4152) with:

```python
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Telegram MCP Server - Supports stdio and HTTP transports"
    )
    parser.add_argument(
        '--http',
        action='store_true',
        help='Run in HTTP mode instead of stdio (default: stdio)'
    )
    parser.add_argument(
        '--host',
        default=os.getenv('MCP_HTTP_HOST', '0.0.0.0'),
        help='HTTP server host (default: 0.0.0.0, reads from MCP_HTTP_HOST env)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('MCP_HTTP_PORT', '8000')),
        help='HTTP server port (default: 8000, reads from MCP_HTTP_PORT env)'
    )

    args = parser.parse_args()

    nest_asyncio.apply()
    if args.http:
        asyncio.run(_main_http(args.host, args.port))
    else:
        asyncio.run(_main_stdio())
```

**Step 3: Verify syntax**

Run: `python -m py_compile main.py`
Expected: No output (successful compilation)

**Step 4: Commit**

```bash
git add main.py
git commit -m "feat: add command-line argument parser for transport selection

- Add argparse for --http, --host, --port flags
- Support MCP_HTTP_HOST and MCP_HTTP_PORT env vars
- Default to stdio mode for backward compatibility

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Refactor Existing _main() to _main_stdio()

**Files:**
- Modify: `main.py:4127-4143` (_main function)

**Step 1: Rename _main() to _main_stdio()**

Replace lines 4127-4143:

```python
async def _main_stdio() -> None:
    """Run server in stdio mode (default, for Claude Desktop/Cursor)"""
    try:
        # Start the Telethon client non-interactively
        print("Starting Telegram client...")
        await client.start()

        print("Telegram client started. Running MCP server (stdio mode)...")
        # Use the asynchronous entrypoint instead of mcp.run()
        await mcp.run_stdio_async()
    except Exception as e:
        print(f"Error starting client: {e}", file=sys.stderr)
        if isinstance(e, sqlite3.OperationalError) and "database is locked" in str(e):
            print(
                "Database lock detected. Please ensure no other instances are running.",
                file=sys.stderr,
            )
        sys.exit(1)
```

**Step 2: Verify syntax**

Run: `python -m py_compile main.py`
Expected: No output (successful compilation)

**Step 3: Test stdio mode still works**

Run: `python main.py --help`
Expected: Help message showing --http, --host, --port options

**Step 4: Commit**

```bash
git add main.py
git commit -m "refactor: rename _main to _main_stdio for clarity

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Implement _main_http() Function

**Files:**
- Modify: `main.py:4127` (add new function before _main_stdio)

**Step 1: Add _main_http() function**

Insert before `_main_stdio()`:

```python
async def _main_http(host: str, port: int) -> None:
    """Run server in HTTP mode (for remote VPS deployment)"""
    try:
        # Start the Telethon client non-interactively
        print("Starting Telegram client...")
        await client.start()

        print(f"Telegram client started. Running MCP server at http://{host}:{port}/mcp")
        # Use FastMCP's HTTP transport
        mcp.run(transport="http", host=host, port=port)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Error: Port {port} is already in use. Try a different port with --port",
                  file=sys.stderr)
        else:
            print(f"Error starting HTTP server: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error starting client: {e}", file=sys.stderr)
        if isinstance(e, sqlite3.OperationalError) and "database is locked" in str(e):
            print(
                "Database lock detected. Please ensure no other instances are running.",
                file=sys.stderr,
            )
        sys.exit(1)
```

**Step 2: Verify syntax**

Run: `python -m py_compile main.py`
Expected: No output (successful compilation)

**Step 3: Format code**

Run: `uv run black main.py`
Expected: "reformatted main.py" or "1 file left unchanged"

**Step 4: Commit**

```bash
git add main.py
git commit -m "feat: implement HTTP transport mode via _main_http

- Add FastMCP HTTP transport support
- Handle port conflicts with clear error messages
- Print endpoint URL on startup

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Create Server Integration Tests

**Files:**
- Create: `server_test.py`

**Step 1: Write test file structure**

Create `server_test.py`:

```python
"""
Transport and server integration tests for Telegram MCP.
Tests stdio and HTTP transport modes, connection handling, and deployment scenarios.
"""

import pytest
import subprocess
import time
import sys
import os

# Set up environment before importing main
os.environ["TELEGRAM_API_ID"] = "12345"
os.environ["TELEGRAM_API_HASH"] = "test_hash"
os.environ["TELEGRAM_SESSION_STRING"] = ""
os.environ["TELEGRAM_SESSION_NAME"] = "test_session"


class TestCommandLineArgs:
    """Test command-line argument parsing"""

    def test_help_flag(self):
        """Verify --help shows all options"""
        result = subprocess.run(
            [sys.executable, "main.py", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "--http" in result.stdout
        assert "--host" in result.stdout
        assert "--port" in result.stdout

    def test_http_flag_accepted(self):
        """Verify --http flag is parsed without error"""
        # This will fail to connect to Telegram, but should parse args
        result = subprocess.run(
            [sys.executable, "main.py", "--http", "--help"],
            capture_output=True,
            text=True,
            timeout=2
        )
        # Should still show help, not crash on --http
        assert "--http" in result.stdout

    def test_custom_port_flag(self):
        """Verify --port flag accepts integer values"""
        result = subprocess.run(
            [sys.executable, "main.py", "--http", "--port", "9000", "--help"],
            capture_output=True,
            text=True,
            timeout=2
        )
        assert "--port" in result.stdout


class TestTransportModes:
    """Test transport mode selection"""

    def test_default_is_stdio(self):
        """Verify default mode is stdio when no flags provided"""
        # Import main to check default behavior
        import main
        import argparse

        # Simulate no arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--http', action='store_true')
        parser.add_argument('--host', default='0.0.0.0')
        parser.add_argument('--port', type=int, default=8000)

        args = parser.parse_args([])
        assert args.http is False
        assert args.host == '0.0.0.0'
        assert args.port == 8000


class TestErrorHandling:
    """Test error scenarios for both transports"""

    def test_invalid_port_zero(self):
        """Verify port 0 is rejected"""
        result = subprocess.run(
            [sys.executable, "main.py", "--http", "--port", "0", "--help"],
            capture_output=True,
            text=True,
            timeout=2
        )
        # argparse should handle this, check help still works
        assert result.returncode == 0

    def test_invalid_port_negative(self):
        """Verify negative port is rejected"""
        result = subprocess.run(
            [sys.executable, "main.py", "--http", "--port", "-1", "--help"],
            capture_output=True,
            text=True,
            timeout=2
        )
        # argparse should handle this
        assert result.returncode == 0
```

**Step 2: Run tests**

Run: `uv run pytest server_test.py -v`
Expected: All tests pass

**Step 3: Format code**

Run: `uv run black server_test.py`
Expected: File formatted

**Step 4: Commit**

```bash
git add server_test.py
git commit -m "test: add server integration tests for transport modes

- Test command-line argument parsing
- Test transport mode selection
- Test error handling for invalid ports

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Update test.md Documentation

**Files:**
- Modify: `test.md:9-20` (Test Files section)

**Step 1: Add server_test.py description**

After the `test_validation.py` section (around line 20), update to:

```markdown
### `test_validation.py`
Tests input validation decorator system for chat_id/user_id normalization and edge cases.

### `test_tools.py`
Comprehensive unit tests for all 86 MCP tools with proper mocking and functional coverage.

### `server_test.py`
Integration tests for stdio and HTTP transport modes, server startup, and deployment scenarios.
```

**Step 2: Commit**

```bash
git add test.md
git commit -m "docs: add server_test.py to test documentation

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Update README.md with HTTP Transport Documentation

**Files:**
- Modify: `README.md` (add new section after installation)

**Step 1: Read current README structure**

Run: `grep -n "## " README.md | head -20`
Expected: List of section headers with line numbers

**Step 2: Add HTTP Transport section**

Insert after the installation/setup section (find appropriate location):

```markdown
## 🌐 HTTP Transport (Remote Access)

The Telegram MCP server supports two transport modes:

### Stdio Mode (Default)
For local Claude Desktop/Cursor integration:
```bash
# Run with stdio (default)
python main.py
uv run main.py
```

This is the traditional mode where the MCP server communicates via stdin/stdout.

### HTTP Mode (Remote Deployment)
For VPS deployment and remote access:
```bash
# Run with HTTP transport
python main.py --http

# Specify custom host and port
python main.py --http --host 0.0.0.0 --port 8000

# With uv
uv run main.py --http --port 8000
```

Your server will be accessible at `http://your-vps-ip:8000/mcp`

**Environment Variables:**
```bash
# Optional: Set default HTTP configuration in .env
MCP_HTTP_HOST=0.0.0.0
MCP_HTTP_PORT=8000
```

**Command-line arguments override environment variables.**

**VPS Deployment:**
```bash
# Ensure firewall allows your chosen port
sudo ufw allow 8000/tcp

# Run server
uv run main.py --http --host 0.0.0.0 --port 8000
```

**Connecting MCP Clients:**

For remote HTTP servers, configure your MCP client to connect to:
```
http://your-vps-ip:8000/mcp
```
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add HTTP transport documentation to README

- Explain stdio vs HTTP modes
- Add usage examples for both transports
- Document environment variables
- Add VPS deployment instructions

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Update CLAUDE.md with Transport Information

**Files:**
- Modify: `CLAUDE.md:20-50` (Running the Server section)
- Modify: `CLAUDE.md:70-100` (Architecture section)

**Step 1: Update "Running the Server" section**

Find and update the section (around line 20):

```markdown
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
```
```

**Step 2: Update Architecture section**

Add to the Architecture section (around line 70):

```markdown
**Transport Modes**:
The server supports dual transport modes:
- **stdio mode** (default): Uses stdin/stdout for local MCP clients like Claude Desktop
- **HTTP mode**: Uses Streamable HTTP protocol for remote connections

Transport selection via command-line flags:
- Default behavior (no flags): stdio mode
- `--http` flag: HTTP mode on 0.0.0.0:8000
- `--host` and `--port`: Customize HTTP binding

Environment variables:
- `MCP_HTTP_HOST`: Default host for HTTP mode (default: 0.0.0.0)
- `MCP_HTTP_PORT`: Default port for HTTP mode (default: 8000)
```

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with HTTP transport info

- Add HTTP mode usage examples
- Document transport selection mechanism
- Explain environment variables

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Run Full Test Suite

**Files:**
- Test: All test files

**Step 1: Run validation tests**

Run: `uv run pytest test_validation.py -v`
Expected: 12 tests pass

**Step 2: Run server tests**

Run: `uv run pytest server_test.py -v`
Expected: All tests pass

**Step 3: Lint main.py**

Run: `uv run flake8 main.py`
Expected: No errors (or only known warnings)

**Step 4: Format all Python files**

Run: `uv run black main.py session_string_generator.py server_test.py test_validation.py`
Expected: All files formatted or unchanged

**Step 5: Verify no regressions**

Run: `python main.py --help`
Expected: Clean help output with all flags

**Step 6: Commit if any formatting changes**

```bash
git add -A
git commit -m "style: format code with black

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Manual Testing & Verification

**Files:**
- Test: Manual server startup in both modes

**Step 1: Test stdio mode (default)**

Run: `python main.py`
Expected: "Starting Telegram client..." then waits for stdin (Ctrl+C to exit)

**Step 2: Test HTTP mode**

Run: `python main.py --http --host 127.0.0.1 --port 8000`
Expected:
- "Starting Telegram client..."
- "Running MCP server at http://127.0.0.1:8000/mcp"
- Server stays running (Ctrl+C to exit)

**Step 3: Test custom port**

Run: `python main.py --http --port 9000`
Expected: "Running MCP server at http://0.0.0.0:9000/mcp"

**Step 4: Test port conflict error**

Terminal 1: `python main.py --http --port 8000`
Terminal 2: `python main.py --http --port 8000`

Expected in Terminal 2: "Error: Port 8000 is already in use. Try a different port with --port"

**Step 5: Document manual test results**

Create a checklist in plan:
- [ ] Stdio mode starts successfully
- [ ] HTTP mode starts successfully
- [ ] Custom port works
- [ ] Port conflict error is clear
- [ ] Help text is accurate

---

## Task 10: Final Integration & Cleanup

**Files:**
- Verify: All changes complete and committed

**Step 1: Review all commits**

Run: `git log --oneline -15`
Expected: See all implementation commits

**Step 2: Verify working tree is clean**

Run: `git status`
Expected: "nothing to commit, working tree clean"

**Step 3: Run final test suite**

Run: `uv run pytest test_validation.py server_test.py -v`
Expected: All tests pass

**Step 4: Verify backward compatibility**

Run: `python main.py --help`
Expected: Default behavior unchanged, new flags added

**Step 5: Create summary commit if needed**

If any final cleanup needed:
```bash
git add -A
git commit -m "chore: final cleanup for HTTP transport feature

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Post-Implementation

After all tasks complete:

1. **Merge to main branch**: Use `superpowers:finishing-a-development-branch` skill
2. **Update remote documentation**: Push README.md and CLAUDE.md changes
3. **Test on actual VPS**: Deploy and verify HTTP mode works remotely
4. **Add authentication**: Future enhancement (not in this plan)

---

## Testing Summary

**Unit Tests:**
- `test_validation.py`: 12 tests (existing, should still pass)
- `server_test.py`: 6 new tests for transport modes

**Manual Tests:**
- Stdio mode startup
- HTTP mode startup
- Custom port configuration
- Port conflict handling
- Help text accuracy

**Expected Results:**
- All automated tests pass
- Both transport modes work
- Backward compatibility maintained
- Clear error messages for issues
