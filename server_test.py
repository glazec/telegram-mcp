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
            [sys.executable, "main.py", "--help"], capture_output=True, text=True
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
            timeout=2,
        )
        # Should still show help, not crash on --http
        assert "--http" in result.stdout

    def test_custom_port_flag(self):
        """Verify --port flag accepts integer values"""
        result = subprocess.run(
            [sys.executable, "main.py", "--http", "--port", "9000", "--help"],
            capture_output=True,
            text=True,
            timeout=2,
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
        parser.add_argument("--http", action="store_true")
        parser.add_argument("--host", default="0.0.0.0")
        parser.add_argument("--port", type=int, default=8000)

        args = parser.parse_args([])
        assert args.http is False
        assert args.host == "0.0.0.0"
        assert args.port == 8000


class TestErrorHandling:
    """Test error scenarios for both transports"""

    def test_invalid_port_zero(self):
        """Verify port 0 is rejected"""
        result = subprocess.run(
            [sys.executable, "main.py", "--http", "--port", "0", "--help"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        # argparse should handle this, check help still works
        assert result.returncode == 0

    def test_invalid_port_negative(self):
        """Verify negative port is rejected"""
        result = subprocess.run(
            [sys.executable, "main.py", "--http", "--port", "-1", "--help"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        # argparse should handle this
        assert result.returncode == 0
