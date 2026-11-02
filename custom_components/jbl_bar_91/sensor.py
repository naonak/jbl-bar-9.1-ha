"""Sound mode, Bluetooth details and soundbar diagnostics."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import JblBarConfigEntry, JblBarCoordinator
from .entity import JblBarEntity


def _memory(doc: dict[str, Any]) -> float | None:
    memory = (doc.get("system") or {}).get("memory") or {}
    total = memory.get("total_bytes") or 0
    return round(100 * memory.get("used_bytes", 0) / total, 1) if total else None


@dataclass(frozen=True, kw_only=True)
class Description(SensorEntityDescription):
    value: Callable[[dict[str, Any]], Any]


DIAG = EntityCategory.DIAGNOSTIC
SENSORS = [
    Description(key="sound_mode", device_class=SensorDeviceClass.ENUM, options=["standard", "smart", "unknown"],
                icon="mdi:auto-fix", value=lambda d: (d.get("mode") or "Unknown").lower()),
    Description(key="bluetooth_device", icon="mdi:cellphone", value=lambda d: (d.get("bluetooth") or {}).get("peer_name")),
    Description(key="bluetooth_audio", icon="mdi:bluetooth-audio", value=lambda d: (d.get("bluetooth") or {}).get("audio")),
    Description(key="cpu", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT,
                entity_category=DIAG, icon="mdi:cpu-32-bit", value=lambda d: (d.get("system") or {}).get("cpu_percent")),
    Description(key="memory", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT,
                entity_category=DIAG, icon="mdi:memory", value=_memory),
    Description(key="temperature", device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                state_class=SensorStateClass.MEASUREMENT, entity_category=DIAG, value=lambda d: (d.get("system") or {}).get("temperature_c")),
    Description(key="wifi_signal", device_class=SensorDeviceClass.SIGNAL_STRENGTH, native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
                state_class=SensorStateClass.MEASUREMENT, entity_category=DIAG, entity_registry_enabled_default=False,
                value=lambda d: (d.get("wifi") or {}).get("signal_dbm")),
    Description(key="uptime", device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.SECONDS,
                entity_category=DIAG, entity_registry_enabled_default=False, value=lambda d: d.get("uptime")),
]


async def async_setup_entry(hass: HomeAssistant, entry: JblBarConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    add(JblBarSensor(entry.runtime_data, description) for description in SENSORS)


class JblBarSensor(JblBarEntity, SensorEntity):
    entity_description: Description

    def __init__(self, coordinator: JblBarCoordinator, description: Description) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value(self.state_doc)
