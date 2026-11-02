"""One-shot controls."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import JblBarConfigEntry, JblBarCoordinator
from .entity import JblBarEntity, advanced_controls

BUTTONS = {"standard_mode": ("standard", "mdi:auto-fix"), "bluetooth_pairing": ("bluetooth_pair", "mdi:bluetooth-settings")}


async def async_setup_entry(hass: HomeAssistant, entry: JblBarConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    buttons = dict(BUTTONS)
    if advanced_controls(coordinator.data):
        # The Smart mode switch replaces the one-way Standard button; drop the
        # button left over from older versions instead of keeping it orphaned.
        del buttons["standard_mode"]
        registry = er.async_get(hass)
        if old := registry.async_get_entity_id(Platform.BUTTON, DOMAIN, f"{entry.unique_id}_standard_mode"):
            registry.async_remove(old)
    add(JblBarButton(coordinator, key, action, icon) for key, (action, icon) in buttons.items())


class JblBarButton(JblBarEntity, ButtonEntity):
    def __init__(self, coordinator: JblBarCoordinator, key: str, action: str, icon: str) -> None:
        super().__init__(coordinator, key)
        self._action = action
        self._attr_icon = icon

    async def async_press(self) -> None:
        await self.coordinator.async_action(self._action)
