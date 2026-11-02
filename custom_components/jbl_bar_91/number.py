"""Front EQ bands: each change applies the full five-band curve."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import EQ_BANDS
from .coordinator import JblBarConfigEntry, JblBarCoordinator
from .entity import JblBarEntity


async def async_setup_entry(hass: HomeAssistant, entry: JblBarConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    if ((coordinator.data or {}).get("eq") or {}).get("available"):
        add(JblBarEqBand(coordinator, index) for index in range(len(EQ_BANDS)))


def current_curve(doc: dict) -> list[float]:
    eq = doc.get("eq") or {}
    gains = eq.get("gains_db") or []
    if not eq.get("enabled") or len(gains) != len(EQ_BANDS):
        return [0.0] * len(EQ_BANDS)
    return [float(g) for g in gains]


class JblBarEqBand(JblBarEntity, NumberEntity):
    _attr_native_min_value = -6
    _attr_native_max_value = 0
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = "dB"
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:equalizer"

    def __init__(self, coordinator: JblBarCoordinator, index: int) -> None:
        super().__init__(coordinator, f"eq_band_{index}")
        self._index = index
        frequency = EQ_BANDS[index]
        self._attr_translation_placeholders = {"band": f"{frequency // 1000} kHz" if frequency >= 1000 else f"{frequency} Hz"}

    @property
    def native_value(self) -> float:
        return current_curve(self.state_doc)[self._index]

    async def async_set_native_value(self, value: float) -> None:
        curve = current_curve(self.state_doc)
        curve[self._index] = round(value * 2) / 2
        if any(curve):
            await self.coordinator.async_action("eq_apply", curve)
        else:
            await self.coordinator.async_action("eq_reset")
