"""Diagnostics: the latest state document without its CSRF token."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import JblBarConfigEntry

REDACT = {"csrf", "peer_name", "name", "ssid", "ip", "hostname"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: JblBarConfigEntry) -> dict[str, Any]:
    return {"host": entry.data.get("host"), "state": async_redact_data(entry.runtime_data.data or {}, REDACT)}
