"""
Session Manager for Multi-Tenant Telegram MCP Server

Handles storage and retrieval of Telegram session strings for multiple users.
Sessions are stored in sessions.json with the format:
{
    "user@example.com": {
        "session_string": "...",
        "created_at": "ISO-8601 timestamp",
        "phone": "+1234567890"
    }
}
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import fcntl
import time

# SESSIONS_STORAGE_PATH: directory for sessions.json
#   Auto-detected: uses /data/sessions when the /data volume is present; falls back to repo root
#   Override with SESSIONS_STORAGE_PATH env var if needed
_data_volume = Path("/data")
_default_sessions_dir = _data_volume / "sessions" if _data_volume.exists() else Path(__file__).parent
_sessions_dir = Path(os.environ.get("SESSIONS_STORAGE_PATH", str(_default_sessions_dir)))
_sessions_dir.mkdir(parents=True, exist_ok=True)
SESSIONS_FILE = _sessions_dir / "sessions.json"


class SessionManager:
    """Manages Telegram session strings for multiple users."""

    def __init__(self, sessions_file: Path = SESSIONS_FILE):
        self.sessions_file = sessions_file
        self._ensure_sessions_file()

    def _ensure_sessions_file(self):
        """Create sessions.json if it doesn't exist."""
        if not self.sessions_file.exists():
            self._write_sessions({})

    def _read_sessions(self) -> Dict[str, Any]:
        """Read sessions from file with file locking."""
        max_retries = 5
        retry_delay = 0.1

        for attempt in range(max_retries):
            try:
                with open(self.sessions_file, "r") as f:
                    # Acquire shared lock for reading
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        data = json.load(f)
                        return data
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
            except BlockingIOError:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise

        return {}

    def _write_sessions(self, data: Dict[str, Any]):
        """Write sessions to file with file locking."""
        max_retries = 5
        retry_delay = 0.1

        for attempt in range(max_retries):
            try:
                with open(self.sessions_file, "w") as f:
                    # Acquire exclusive lock for writing
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        json.dump(data, f, indent=2)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return
            except BlockingIOError:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise

    def get_session(self, email: str) -> Optional[str]:
        """
        Retrieve session string for a user.

        Args:
            email: User's email address

        Returns:
            Session string if exists, None otherwise
        """
        sessions = self._read_sessions()
        user_data = sessions.get(email)
        if user_data:
            return user_data.get("session_string")
        return None

    def save_session(self, email: str, session_string: str, phone: str):
        """
        Save a new session for a user.

        Args:
            email: User's email address
            session_string: Telegram session string
            phone: Phone number used for authentication
        """
        sessions = self._read_sessions()
        sessions[email] = {
            "session_string": session_string,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "phone": phone,
        }
        self._write_sessions(sessions)

    def delete_session(self, email: str):
        """
        Delete a user's session.

        Args:
            email: User's email address
        """
        sessions = self._read_sessions()
        if email in sessions:
            del sessions[email]
            self._write_sessions(sessions)

    def session_exists(self, email: str) -> bool:
        """
        Check if a session exists for a user.

        Args:
            email: User's email address

        Returns:
            True if session exists, False otherwise
        """
        return self.get_session(email) is not None

    def list_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        List all sessions (without session strings for security).

        Returns:
            Dictionary of email -> {created_at, phone}
        """
        sessions = self._read_sessions()
        return {
            email: {
                "created_at": data.get("created_at"),
                "phone": data.get("phone"),
            }
            for email, data in sessions.items()
        }

    def get_any_session(self) -> tuple[Optional[str], Optional[str]]:
        """
        Get the first available session from sessions.json.

        Returns:
            Tuple of (email, session_string) or (None, None) if no sessions exist
        """
        sessions = self._read_sessions()
        if sessions:
            # Return the first session (arbitrary order)
            email = next(iter(sessions))
            return email, sessions[email].get("session_string")
        return None, None


# Global instance
session_manager = SessionManager()
