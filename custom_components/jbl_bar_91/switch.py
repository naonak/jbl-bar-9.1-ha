"""Night mode: toggled only when the read-back state differs."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import JblBarConfigEntry
from .entity import JblBarEntity


async def async_setup_entry(hass: HomeAssistant, entry: JblBarConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    add([JblBarNight(entry.runtime_data, "night")])


class JblBarNight(JblBarEntity, SwitchEntity):
    _attr_icon = "mdi:weather-night"

    @property
    def is_on(self) -> bool | None:
        return self.sound.get("night")

    async def _set(self, on: bool) -> None:
        if self.is_on is not None and self.is_on != on:
            await self.coordinator.async_action("night_toggle")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)
