"""State coordinator: event stream while the bar is on, light polling otherwise."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import aclosing
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JblBarClient, JblBarError, JblBarRefused
from .const import DOMAIN, LOGGER

POLL_INTERVAL = timedelta(seconds=15)
# Seconds between wake checks while the bar sleeps, and stream reconnect delays.
IDLE_CHECK = 5
RECONNECT_MIN = 5
RECONNECT_MAX = 60

type JblBarConfigEntry = ConfigEntry["JblBarCoordinator"]


class JblBarCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Keep the latest remote state.

    While the bar is on, the remote's event stream pushes every change. The
    stream makes the remote sample the bar once per second, so it is closed in
    standby and a cheap state request every 15 s detects the wake instead.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: JblBarClient) -> None:
        super().__init__(hass, LOGGER, name=DOMAIN, config_entry=entry, update_interval=POLL_INTERVAL)
        self.client = client
        self._push_task: asyncio.Task | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.get_state()
        except JblBarError as err:
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="unreachable", translation_placeholders={"error": str(err)}) from err

    @property
    def awake(self) -> bool:
        return bool(self.data and self.data.get("available") and self.data.get("power") == "On")

    def start_push(self) -> None:
        assert self.config_entry is not None
        self._push_task = self.config_entry.async_create_background_task(
            self.hass, self._push_loop(), f"{DOMAIN} event stream {self.client.host}"
        )

    async def _push_loop(self) -> None:
        delay = RECONNECT_MIN
        while True:
            if not self.awake:
                await asyncio.sleep(IDLE_CHECK)
                continue
            try:
                # aclosing: leaving the loop must close the HTTP stream at once,
                # otherwise the remote keeps sampling the bar until GC.
                async with aclosing(self.client.events()) as stream:
                    async for state in stream:
                        delay = RECONNECT_MIN
                        self.async_set_updated_data(state)
                        if not self.awake:
                            break
            except JblBarError as err:
                LOGGER.debug("Event stream from %s ended: %s", self.client.host, err)
                delay = min(delay * 2, RECONNECT_MAX)
            await asyncio.sleep(delay)

    async def async_action(self, action: str, gains_db: list[float] | None = None) -> None:
        """Send one control and publish the confirmed state."""
        try:
            state = await self.client.action(action, gains_db)
        except JblBarRefused as err:
            if err.state:
                self.async_set_updated_data(err.state)
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="refused", translation_placeholders={"error": str(err)}
            ) from err
        except JblBarError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="unreachable", translation_placeholders={"error": str(err)}
            ) from err
        self.async_set_updated_data(state)

    async def async_step_to(self, action: str | Callable[[int], str], read: Callable[[dict[str, Any]], int | None], target: int, limit: int) -> None:
        """Repeat a cycling control until read-back reaches target (bass, levels, volume)."""
        for _ in range(limit + 1):
            current = read(self.data or {})
            if current is None:
                raise HomeAssistantError(translation_domain=DOMAIN, translation_key="unavailable")
            if current == target:
                return
            await self.async_action(action(current) if callable(action) else action)
        raise HomeAssistantError(translation_domain=DOMAIN, translation_key="not_reached")
