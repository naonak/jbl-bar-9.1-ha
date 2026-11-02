"""Rear speaker docking and Bluetooth connection."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import JblBarConfigEntry
from .entity import JblBarEntity


async def async_setup_entry(hass: HomeAssistant, entry: JblBarConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    add([JblBarRearDocked(coordinator, "rear_docked"), JblBarBluetooth(coordinator, "bluetooth_connected")])


class JblBarRearDocked(JblBarEntity, BinarySensorEntity):
    _attr_icon = "mdi:speaker-wireless"

    @property
    def is_on(self) -> bool | None:
        return self.sound.get("rear_docked")


class JblBarBluetooth(JblBarEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self) -> bool | None:
        return (self.state_doc.get("bluetooth") or {}).get("connected", False)
