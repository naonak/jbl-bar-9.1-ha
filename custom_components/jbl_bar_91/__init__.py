"""JBL Bar 9.1 integration, through the soundbar's local browser remote."""
from __future__ import annotations

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JblBarClient
from .coordinator import JblBarConfigEntry, JblBarCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: JblBarConfigEntry) -> bool:
    client = JblBarClient(async_get_clientsession(hass), entry.data[CONF_HOST])
    coordinator = JblBarCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.start_push()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: JblBarConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
