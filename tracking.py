"""PostHog usage tracking — graceful no-op when POSTHOG_API_KEY is unset.

Captures tool-execution events and exceptions; never raises into the request
path. Provides a `track(event_name)` decorator for wrapping FastMCP tool
functions without per-tool boilerplate.
"""
import atexit
import functools
import logging
import os
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("telegram_mcp")

try:
    from posthog import Posthog
except ImportError:  # posthog not installed
    Posthog = None

_client = None
_initialized = False


def _get():
    global _client, _initialized
    if not _initialized:
        _initialized = True
        api_key = os.environ.get("POSTHOG_API_KEY")
        if Posthog and api_key:
            try:
                _client = Posthog(
                    api_key,
                    host=os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com"),
                )
                atexit.register(_client.flush)
            except Exception as e:  # never let tracking break startup
                logger.warning(f"PostHog init failed: {e}")
                _client = None
    return _client


def capture(event: str, distinct_id: Optional[str] = None, properties: Optional[Dict[str, Any]] = None) -> None:
    c = _get()
    if not c:
        return
    try:
        c.capture(distinct_id=distinct_id or "anonymous", event=event, properties=properties or {})
    except Exception:
        pass


def capture_exception(exc: BaseException, distinct_id: Optional[str] = None,
                      properties: Optional[Dict[str, Any]] = None) -> None:
    c = _get()
    if not c:
        return
    try:
        c.capture_exception(exc, distinct_id=distinct_id or "anonymous", properties=properties or {})
    except Exception:
        pass


def current_distinct_id() -> str:
    """Best-effort: the authenticated Google user's email, else 'anonymous'."""
    try:
        from fastmcp.server.dependencies import get_access_token
        token = get_access_token()
        if token is not None:
            return token.claims.get("email") or token.claims.get("sub") or "anonymous"
    except Exception:
        pass
    return "anonymous"


def track(event: str) -> Callable:
    """Decorator: capture success/failure for a FastMCP tool (sync or async).

    Wraps a tool function so each invocation emits one PostHog event with
    {tool, ms, success}. Exceptions are captured separately via
    capture_exception and then re-raised so the tool's normal error
    contract is preserved.

    Works for both sync and async tools — checks at decoration time and
    returns the matching wrapper shape.

    Usage:
        @mcp.tool
        @track("<server>_tool")
        async def my_tool(...):
            ...
    """
    import asyncio

    def deco(fn: Callable) -> Callable:
        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def awrapper(*args, **kwargs):
                did = current_distinct_id()
                t0 = time.perf_counter()
                try:
                    result = await fn(*args, **kwargs)
                except BaseException as e:
                    capture_exception(e, did, {"tool": fn.__name__})
                    capture(event, did, {
                        "tool": fn.__name__,
                        "ms": int((time.perf_counter() - t0) * 1000),
                        "success": False,
                    })
                    raise
                capture(event, did, {
                    "tool": fn.__name__,
                    "ms": int((time.perf_counter() - t0) * 1000),
                    "success": True,
                })
                return result
            return awrapper

        @functools.wraps(fn)
        def swrapper(*args, **kwargs):
            did = current_distinct_id()
            t0 = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
            except BaseException as e:
                capture_exception(e, did, {"tool": fn.__name__})
                capture(event, did, {
                    "tool": fn.__name__,
                    "ms": int((time.perf_counter() - t0) * 1000),
                    "success": False,
                })
                raise
            capture(event, did, {
                "tool": fn.__name__,
                "ms": int((time.perf_counter() - t0) * 1000),
                "success": True,
            })
            return result
        return swrapper
    return deco
