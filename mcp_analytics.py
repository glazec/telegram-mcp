"""PostHog MCP analytics instrumentation."""
import atexit
import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_analytics = None
_client = None
_initialized = False


def _project_api_key() -> str:
    return (
        os.environ.get("POSTHOG_PROJECT_API_KEY")
        or os.environ.get("POSTHOG_API_KEY")
        or ""
    ).strip()


def _current_user_id() -> str | None:
    try:
        from fastmcp.server.dependencies import get_access_token

        token = get_access_token()
        if token is not None:
            return token.claims.get("sub") or token.claims.get("email")
    except Exception:
        return None
    return None


def _flush_analytics() -> None:
    if _analytics is None:
        return
    try:
        asyncio.run(_analytics.flush())
    except Exception as exc:
        logger.warning("PostHog MCP analytics flush failed: %s", exc)


def instrument_mcp(mcp: Any, service_name: str) -> Any | None:
    """Wrap a FastMCP server with official PostHog MCP analytics."""
    global _analytics, _client, _initialized
    if _initialized:
        return _analytics
    _initialized = True

    api_key = _project_api_key()
    if not api_key:
        return None

    try:
        from posthog import Posthog
        from posthog.mcp import instrument
        from posthog.mcp.types import MCPAnalyticsOptions, UserIdentity

        _client = Posthog(
            project_api_key=api_key,
            host=os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com"),
            enable_exception_autocapture=True,
            disable_geoip=True,
            super_properties={"service": service_name},
        )

        def identify(_request: Any, _extra: Any) -> UserIdentity | None:
            distinct_id = _current_user_id()
            if not distinct_id:
                return None
            return UserIdentity(distinct_id=distinct_id)

        def event_properties(_request: Any, _extra: Any) -> dict[str, str]:
            return {"service": service_name}

        _analytics = instrument(
            mcp,
            _client,
            MCPAnalyticsOptions(
                identify=identify,
                event_properties=event_properties,
                logger=logger.warning,
            ),
        )
        atexit.register(_client.shutdown)
        atexit.register(_flush_analytics)
    except Exception as exc:
        logger.warning("PostHog MCP analytics init failed: %s", exc)
        _analytics = None
    return _analytics
