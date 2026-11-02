"""Client for the JBL Bar 9.1 browser remote API (kisinga/jbl-bar-9.1).

Only the remote's fixed endpoints are used: GET /api/state, GET /api/events
and POST /api/action with its CSRF token. One control runs at a time. A
refused control (409) is reported and never retried; a 403 caused by a stale
token refreshes it and sends the same request once more, because the server
rejects stale tokens before acting.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import aiohttp

STATE_TIMEOUT = aiohttp.ClientTimeout(total=10)
ACTION_TIMEOUT = aiohttp.ClientTimeout(total=40)
# The remote sends a keepalive comment every 15 s.
EVENTS_TIMEOUT = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=45)


class JblBarError(Exception):
    """The remote could not be reached or answered unexpectedly."""


class JblBarForbidden(JblBarError):
    """The remote rejected this client (outside its trusted subnet)."""


class JblBarRefused(JblBarError):
    """The remote refused a control (HTTP 409)."""

    def __init__(self, message: str, state: dict[str, Any] | None) -> None:
        super().__init__(message)
        self.state = state


def normalize_host(host: str) -> str:
    """Accept "10.0.0.35", "10.0.0.35:8080" or "http://10.0.0.35:8080/"."""
    host = host.strip().removeprefix("http://").rstrip("/")
    return host if ":" in host else f"{host}:8080"


class JblBarClient:
    """Talk to one soundbar."""

    def __init__(self, session: aiohttp.ClientSession, host: str) -> None:
        self._session = session
        self.host = normalize_host(host)
        self._base = f"http://{self.host}"
        self._csrf: str | None = None
        self._lock = asyncio.Lock()

    def _remember(self, state: dict[str, Any]) -> dict[str, Any]:
        if isinstance(state.get("csrf"), str):
            self._csrf = state["csrf"]
        return state

    async def get_state(self) -> dict[str, Any]:
        try:
            async with self._session.get(f"{self._base}/api/state", timeout=STATE_TIMEOUT) as resp:
                if resp.status == 403:
                    raise JblBarForbidden(await resp.text())
                if resp.status != 200:
                    raise JblBarError(f"state request returned HTTP {resp.status}")
                return self._remember(await resp.json(content_type=None))
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise JblBarError(str(err) or type(err).__name__) from err

    async def action(self, action: str, gains_db: list[float] | None = None, value: int | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"action": action}
        if gains_db is not None:
            payload["gains_db"] = gains_db
        if value is not None:
            payload["value"] = value
        async with self._lock:
            for attempt in (1, 2):
                if not self._csrf:
                    await self.get_state()
                try:
                    async with self._session.post(
                        f"{self._base}/api/action",
                        data=json.dumps(payload),
                        headers={"Content-Type": "application/json", "X-CSRF-Token": self._csrf or ""},
                        timeout=ACTION_TIMEOUT,
                    ) as resp:
                        if resp.status == 200:
                            return self._remember(await resp.json(content_type=None))
                        if resp.status == 403 and attempt == 1:
                            self._csrf = None
                            continue
                        if resp.status == 409:
                            body = await resp.json(content_type=None)
                            state = body.get("state") if isinstance(body.get("state"), dict) else None
                            if state:
                                self._remember(state)
                            raise JblBarRefused(str(body.get("error") or "control refused"), state)
                        raise JblBarError(f"{action} returned HTTP {resp.status}: {(await resp.text()).strip()}")
                except (aiohttp.ClientError, TimeoutError, ValueError) as err:
                    raise JblBarError(str(err) or type(err).__name__) from err
        raise JblBarError(f"{action} was refused twice by the token check")

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        """Yield each state pushed on the remote's event stream."""
        try:
            async with self._session.get(
                f"{self._base}/api/events", timeout=EVENTS_TIMEOUT, headers={"Accept": "text/event-stream"}
            ) as resp:
                if resp.status != 200:
                    raise JblBarError(f"event stream returned HTTP {resp.status}")
                data: list[str] = []
                async for raw in resp.content:
                    line = raw.decode("utf-8", "replace").rstrip("\r\n")
                    if line.startswith("data:"):
                        data.append(line[5:].lstrip())
                    elif not line and data:
                        state = json.loads("\n".join(data))
                        data = []
                        if isinstance(state, dict):
                            yield self._remember(state)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise JblBarError(str(err) or type(err).__name__) from err
