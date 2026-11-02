"""Night mode: toggled only when the read-back state differs."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import JblBarConfigEntry
from .entity import JblBarEntity, advanced_controls


async def async_setup_entry(hass: HomeAssistant, entry: JblBarConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    entities: list[SwitchEntity] = [JblBarNight(coordinator, "night")]
    if advanced_controls(coordinator.data):
        entities.append(JblBarSmartMode(coordinator, "smart_mode"))
    add(entities)


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


class JblBarSmartMode(JblBarEntity, SwitchEntity):
    """On = Smart Mode, off = Standard (the bar returns to Smart at power-on)."""

    _attr_icon = "mdi:auto-fix"
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool | None:
        mode = self.state_doc.get("mode")
        return None if mode not in ("Smart", "Standard") else mode == "Smart"

    @property
    def available(self) -> bool:
        return super().available and self.awake

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self.is_on is False:
            await self.coordinator.async_action("smart")

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self.is_on:
            await self.coordinator.async_action("standard")
