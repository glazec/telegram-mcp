# Test Documentation

This document provides comprehensive information about the test suite for the Telegram MCP server.

## Overview

The test suite provides coverage for all **86 tools** exposed by the Telegram MCP server. Tests are organized by functional category to make it easy to run and maintain specific subsets of tests.

## Test Files

### `test_validation.py`
Tests for the input validation decorator system:
- Valid/invalid chat_id and user_id formats
- Integer ID validation (range checking)
- String ID validation (username patterns)
- List validation for bulk operations
- Edge cases and error handling

**Test count:** 12 tests

### `test_tools.py`
Comprehensive tests for all 86 MCP tools organized into 17 test classes:

1. **TestChatTools** (5 tests)
   - `test_get_chats` - Paginated chat list retrieval
   - `test_get_messages` - Message retrieval from chats
   - `test_send_message` - Sending messages
   - `test_list_chats` - Filtered chat listing
   - `test_get_chat` - Specific chat details

2. **TestChannelTools** (2 tests)
   - `test_subscribe_public_channel` - Joining channels
   - `test_create_channel` - Creating new channels

3. **TestContactTools** (11 tests)
   - Contact listing, searching, and ID retrieval
   - Adding, deleting, blocking, and unblocking contacts
   - Importing and exporting contacts
   - Blocked user management

4. **TestGroupTools** (10 tests)
   - Group creation and member management
   - Admin promotion/demotion
   - User banning/unbanning
   - Admin and banned user listing

5. **TestMessageTools** (11 tests)
   - Message listing, forwarding, editing, deleting
   - Pinning/unpinning messages
   - Marking as read
   - Reply functionality
   - Media info and message context
   - Pinned message retrieval

6. **TestInlineButtonTools** (2 tests)
   - Listing inline keyboard buttons
   - Pressing inline buttons

7. **TestFileTools** (4 tests)
   - File sending and media downloading
   - Voice message and sticker sending

8. **TestProfileTools** (6 tests)
   - User profile retrieval and updates
   - Profile photo management
   - User photos and status retrieval

9. **TestPrivacyTools** (6 tests)
   - Privacy settings management
   - Chat muting/unmuting
   - Chat archiving/unarchiving

10. **TestChatEditingTools** (3 tests)
    - Chat title editing
    - Chat photo management

11. **TestInviteTools** (4 tests)
    - Invite link generation and retrieval
    - Joining chats via invite links
    - Import/export of chat invites

12. **TestSearchTools** (3 tests)
    - Public chat searching
    - Message searching within chats
    - Username resolution

13. **TestMediaTools** (3 tests)
    - Sticker set retrieval
    - GIF searching and sending

14. **TestBotTools** (2 tests)
    - Bot information retrieval
    - Bot command configuration

15. **TestHistoryTools** (2 tests)
    - Chat history retrieval
    - Recent actions logging

16. **TestTopicTools** (1 test)
    - Forum topic listing

17. **TestContactRelationshipTools** (3 tests)
    - Direct chat discovery
    - Contact chat listing
    - Last interaction retrieval

18. **TestPollTools** (1 test)
    - Poll creation

19. **TestReactionTools** (3 tests)
    - Sending and removing reactions
    - Reaction retrieval

20. **TestDraftTools** (3 tests)
    - Draft saving, retrieval, and clearing

21. **TestFolderTools** (7 tests)
    - Folder listing and creation
    - Adding/removing chats from folders
    - Folder deletion and reordering

**Test count:** 86 tests

## Running Tests

### Prerequisites

Ensure you have the testing dependencies installed:

```bash
uv sync
```

The `pyproject.toml` already includes `pytest>=9.0.2` in dependencies.

### Run All Tests

```bash
# Run all tests with verbose output
uv run pytest test_validation.py test_tools.py -v

# Run with test discovery
uv run pytest -v
```

### Run Specific Test Files

```bash
# Run only validation tests
uv run pytest test_validation.py -v

# Run only tool tests
uv run pytest test_tools.py -v
```

### Run Specific Test Classes

```bash
# Run only chat-related tests
uv run pytest test_tools.py::TestChatTools -v

# Run only folder management tests
uv run pytest test_tools.py::TestFolderTools -v

# Run only contact tests
uv run pytest test_tools.py::TestContactTools -v
```

### Run Specific Individual Tests

```bash
# Run a single test
uv run pytest test_tools.py::TestChatTools::test_send_message -v

# Run multiple specific tests
uv run pytest test_tools.py::TestChatTools::test_send_message test_tools.py::TestGroupTools::test_create_group -v
```

### Test Output Options

```bash
# Show print statements during tests
uv run pytest -v -s

# Stop at first failure
uv run pytest -v -x

# Show local variables on failure
uv run pytest -v -l

# Run in parallel (requires pytest-xdist)
uv run pytest -v -n auto
```

## Test Coverage

### Measuring Coverage

To measure test coverage, install pytest-cov:

```bash
uv add --dev pytest-cov
```

Then run tests with coverage:

```bash
# Generate coverage report
uv run pytest test_tools.py test_validation.py --cov=main --cov-report=term-missing

# Generate HTML coverage report
uv run pytest test_tools.py test_validation.py --cov=main --cov-report=html

# Open HTML report (macOS)
open htmlcov/index.html
```

### Current Coverage

- **Validation system:** 100% coverage via `test_validation.py`
- **Tool functions:** 100% coverage via `test_tools.py` (86/86 tools)
- **Helper functions:** Indirectly tested via tool tests

## Test Architecture

### Mocking Strategy

All tests use the `mock_client` pytest fixture which mocks the global `TelegramClient` instance. This approach:

- Avoids actual Telegram API calls
- Enables fast, isolated unit tests
- Prevents authentication requirements during testing
- Allows testing error conditions safely

### Test Pattern

Each test follows this pattern:

```python
@pytest.mark.asyncio
async def test_function_name(self, mock_client):
    """Test description."""
    # Arrange: Set up mock responses if needed
    mock_client.some_method.return_value = expected_value

    # Act: Call the function under test
    result = await function_name(param1=value1, param2=value2)

    # Assert: Verify behavior
    assert isinstance(result, str)
    assert "expected" in result.lower()
    mock_client.some_method.assert_called_once()
```

### Environment Setup

Tests set required environment variables before importing `main.py`:

```python
os.environ["TELEGRAM_API_ID"] = "12345"
os.environ["TELEGRAM_API_HASH"] = "test_hash"
os.environ["TELEGRAM_SESSION_STRING"] = "test_session"
```

This prevents authentication errors during test imports.

## Adding New Tests

When adding new tools to `main.py`, follow these steps:

### 1. Determine the Test Class

Add tests to the appropriate test class based on functionality:
- Chat operations → `TestChatTools`
- Contacts → `TestContactTools`
- Groups → `TestGroupTools`
- Messages → `TestMessageTools`
- etc.

If no appropriate class exists, create a new one following the naming pattern `Test{Category}Tools`.

### 2. Write the Test

```python
@pytest.mark.asyncio
async def test_new_function(self, mock_client):
    """Test new_function does what it should."""
    # Set up mocks
    mock_client.telegram_method.return_value = expected_response

    # Call function
    result = await new_function(param1="test", param2=123)

    # Verify
    assert isinstance(result, str)
    assert "success" in result.lower() or "error" in result.lower()
    mock_client.telegram_method.assert_called()
```

### 3. Run and Verify

```bash
# Run your new test
uv run pytest test_tools.py::TestYourClass::test_new_function -v

# Verify coverage
uv run pytest test_tools.py --cov=main --cov-report=term-missing
```

### 4. Update Documentation

Update this file (`test.md`) with:
- New test class (if created)
- Test count updates
- Any special testing considerations

## Testing Best Practices

### ✅ Do

- Mock external dependencies (TelegramClient)
- Test both success and error cases
- Use descriptive test names and docstrings
- Verify function return types
- Check that appropriate Telethon methods are called
- Group related tests in classes
- Use fixtures for common setup

### ❌ Don't

- Make actual Telegram API calls
- Use real credentials or session strings
- Test implementation details
- Write tests dependent on test execution order
- Skip assertions
- Leave tests commented out

## Continuous Integration

To integrate tests with CI/CD:

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install uv
        uses: astral-sh/setup-uv@v1

      - name: Run tests
        run: |
          uv sync
          uv run pytest test_validation.py test_tools.py -v --cov=main --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Known Test Limitations

1. **File Operations**: Tests for `send_file`, `download_media`, `send_voice`, `send_sticker`, `set_profile_photo`, and `edit_chat_photo` use mocks but don't verify actual file I/O operations.

2. **GIF Operations**: `get_gif_search` and `send_gif` tests mock responses but don't test Telethon's inline query handling.

3. **Session Management**: Tests don't verify session string generation or file-based session handling.

4. **Network Conditions**: Tests don't simulate network failures, timeouts, or rate limiting.

5. **Telethon Internal State**: Tests don't verify Telethon's internal state management or caching behavior.

## Troubleshooting

### Import Errors

If you see errors like `ModuleNotFoundError: No module named 'main'`:

```bash
# Make sure you're in the project directory
cd /path/to/telegram-mcp

# Run tests with uv
uv run pytest -v
```

### AsyncIO Errors

If you see `RuntimeError: Event loop is closed`:

Ensure `pytest-asyncio` is installed:

```bash
uv add --dev pytest-asyncio
```

### Mock Not Working

If mocks aren't being applied:

1. Verify the mock path matches the actual import path
2. Ensure the mock is set up before the function call
3. Check that you're patching where the object is used, not where it's defined

### All Tests Failing

1. Check that environment variables are set correctly in the test file
2. Verify `uv sync` has been run
3. Ensure you're using the correct Python version (3.10+)

## Test Metrics

- **Total Tools:** 86
- **Total Tests:** 98 (86 tool tests + 12 validation tests)
- **Test Coverage:** ~100% of tool functions
- **Avg Test Execution Time:** <0.1s per test
- **Total Test Suite Time:** <10s

## Future Enhancements

Potential improvements to the test suite:

1. **Integration Tests**: Add tests that use a real test Telegram account
2. **Performance Tests**: Measure and track test execution time
3. **Error Injection**: Test more error scenarios and edge cases
4. **Async Context**: Test concurrent tool execution
5. **Rate Limiting**: Verify rate limiting behavior
6. **Session Lifecycle**: Test session creation, persistence, and cleanup
7. **Media Validation**: Add tests for media type detection and validation
8. **Pagination**: Test pagination edge cases (first page, last page, out of range)

## Contributing

When contributing tests:

1. Follow existing patterns and naming conventions
2. Add docstrings to all test functions
3. Update this documentation with new tests
4. Ensure all tests pass before submitting PR
5. Maintain >95% coverage for new code

## Questions or Issues

If you encounter issues with tests:

1. Check this documentation first
2. Review the test file docstrings
3. Look at similar existing tests for patterns
4. Open an issue on GitHub with test output

---

**Last Updated:** 2026-01-30
**Maintained By:** Telegram MCP Team
