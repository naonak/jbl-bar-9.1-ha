"""One-shot controls."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import JblBarConfigEntry, JblBarCoordinator
from .entity import JblBarEntity

BUTTONS = {"standard_mode": ("standard", "mdi:auto-fix"), "bluetooth_pairing": ("bluetooth_pair", "mdi:bluetooth-settings")}


async def async_setup_entry(hass: HomeAssistant, entry: JblBarConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    add(JblBarButton(entry.runtime_data, key, action, icon) for key, (action, icon) in BUTTONS.items())


class JblBarButton(JblBarEntity, ButtonEntity):
    def __init__(self, coordinator: JblBarCoordinator, key: str, action: str, icon: str) -> None:
        super().__init__(coordinator, key)
        self._action = action
        self._attr_icon = icon

    async def async_press(self) -> None:
        await self.coordinator.async_action(self._action)
