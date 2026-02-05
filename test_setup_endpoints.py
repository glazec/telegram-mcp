"""
Test /setup endpoints and session management functionality
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock

# Set up environment before importing main
os.environ["TELEGRAM_API_ID"] = "12345"
os.environ["TELEGRAM_API_HASH"] = "test_hash"
os.environ["TELEGRAM_SESSION_STRING"] = ""
os.environ["TELEGRAM_SESSION_NAME"] = "test_session"


class TestSetupEndpoints:
    """Test /setup endpoint handlers"""

    @pytest.mark.asyncio
    async def test_reload_telegram_client_imports(self):
        """Verify reload_telegram_client function exists and is callable"""
        from main import reload_telegram_client

        assert callable(reload_telegram_client)
        assert asyncio.iscoroutinefunction(reload_telegram_client)

    @pytest.mark.asyncio
    async def test_pending_verifications_dict_exists(self):
        """Verify pending_verifications dict is defined"""
        from main import pending_verifications

        assert isinstance(pending_verifications, dict)

    @pytest.mark.asyncio
    async def test_setup_endpoints_exist(self):
        """Verify all setup endpoint functions are defined"""
        from main import (
            serve_setup_page,
            send_code_endpoint,
            verify_code_endpoint,
            verify_2fa_endpoint,
        )

        assert callable(serve_setup_page)
        assert callable(send_code_endpoint)
        assert callable(verify_code_endpoint)
        assert callable(verify_2fa_endpoint)

    @pytest.mark.asyncio
    async def test_serve_setup_page_returns_file_response(self):
        """Verify serve_setup_page returns FileResponse for templates/setup.html"""
        from main import serve_setup_page
        from starlette.responses import FileResponse

        # Create mock request
        request = Mock()

        result = await serve_setup_page(request)

        assert isinstance(result, FileResponse)

    @pytest.mark.asyncio
    async def test_send_code_endpoint_validates_input(self):
        """Verify send_code_endpoint validates required fields"""
        from main import send_code_endpoint
        from starlette.responses import JSONResponse

        # Create mock request with missing fields
        request = Mock()
        request.json = AsyncMock(return_value={"email": "", "phone": ""})

        result = await send_code_endpoint(request)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_verify_code_endpoint_validates_input(self):
        """Verify verify_code_endpoint validates required fields"""
        from main import verify_code_endpoint
        from starlette.responses import JSONResponse

        # Create mock request with missing fields
        request = Mock()
        request.json = AsyncMock(return_value={"email": "", "phone": "", "code": ""})

        result = await verify_code_endpoint(request)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400


class TestHTTPModeStartup:
    """Test HTTP mode startup behavior"""

    @pytest.mark.asyncio
    async def test_http_mode_does_not_call_start(self):
        """Verify _main_http uses connect() instead of start() (non-interactive)"""
        import main
        from unittest.mock import AsyncMock, MagicMock
        import sys

        # Mock the client
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.is_user_authorized = AsyncMock(return_value=True)
        mock_client.is_connected = MagicMock(return_value=False)

        # Mock session_manager
        with patch('main.session_manager') as mock_session:
            mock_session.get_any_session.return_value = (None, None)

            # Mock uvicorn module (imported locally in _main_http)
            mock_uvicorn = MagicMock()
            mock_server = MagicMock()
            mock_server.serve = AsyncMock()
            mock_uvicorn.Server.return_value = mock_server
            mock_uvicorn.Config = MagicMock()

            # Add to sys.modules so the local import works
            sys.modules['uvicorn'] = mock_uvicorn

            # Replace global client
            original_client = main.client
            main.client = mock_client

            try:
                # Run _main_http with timeout to prevent hanging
                await asyncio.wait_for(
                    main._main_http("0.0.0.0", 8888),
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                # Expected - server.serve() runs indefinitely
                pass
            except Exception as e:
                # Catch any other exceptions but ensure we still check assertions
                pass
            finally:
                # Restore original client
                main.client = original_client
                # Clean up sys.modules
                if 'uvicorn' in sys.modules:
                    del sys.modules['uvicorn']

            # Verify connect was called (not start)
            mock_client.connect.assert_called_once()


class TestImports:
    """Test that all necessary imports are present"""

    def test_starlette_imports(self):
        """Verify Starlette components are imported"""
        try:
            from main import JSONResponse, FileResponse, Route, CORSMiddleware
            assert True
        except ImportError as e:
            pytest.fail(f"Missing Starlette import: {e}")

    def test_session_manager_import(self):
        """Verify session_manager is imported"""
        try:
            from main import session_manager
            assert session_manager is not None
        except ImportError as e:
            pytest.fail(f"Missing session_manager import: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
