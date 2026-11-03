"""Front EQ bands: each change applies the full five-band curve."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import AV_SYNC_CHUNK, AV_SYNC_LEGACY_CHUNK, AV_SYNC_MAX, AV_SYNC_SOURCES, AV_SYNC_STEP, EQ_BANDS
from .coordinator import JblBarConfigEntry, JblBarCoordinator
from .entity import JblBarEntity, advanced_controls, eq_installed


async def async_setup_entry(hass: HomeAssistant, entry: JblBarConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    entities: list[NumberEntity] = []
    if eq_installed(coordinator.data):
        entities.extend(JblBarEqBand(coordinator, index) for index in range(len(EQ_BANDS)))
    if advanced_controls(coordinator.data):
        entities.append(JblBarAudioSync(coordinator, "audio_sync"))
    add(entities)


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
    def available(self) -> bool:
        return super().available and self.eq_ready

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


class JblBarAudioSync(JblBarEntity, NumberEntity):
    """Lip-sync delay, set in one request (one sync session on the bar)."""

    _attr_native_min_value = 0
    _attr_native_max_value = AV_SYNC_MAX
    _attr_native_step = AV_SYNC_STEP
    _attr_native_unit_of_measurement = "ms"
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-sync-outline"

    @property
    def native_value(self) -> int | None:
        return self.sound.get("av_sync_ms")

    @property
    def available(self) -> bool:
        return super().available and self.awake and self.state_doc.get("source_state") in AV_SYNC_SOURCES

    async def async_set_native_value(self, value: float) -> None:
        target = max(0, min(AV_SYNC_MAX, int(round(value / AV_SYNC_STEP)) * AV_SYNC_STEP))
        chunk = AV_SYNC_CHUNK
        for _ in range(AV_SYNC_MAX // AV_SYNC_LEGACY_CHUNK + 2):
            current = self.sound.get("av_sync_ms")
            if current is None or current == target:
                return
            step = max(-chunk, min(chunk, target - current))
            try:
                await self.coordinator.async_action("av_sync_set", value=current + step)
            except HomeAssistantError as err:
                # Older remotes accept at most 80 ms per request: split the change.
                if chunk == AV_SYNC_LEGACY_CHUNK or "at most" not in str(err.__cause__ or err):
                    raise
                chunk = AV_SYNC_LEGACY_CHUNK
