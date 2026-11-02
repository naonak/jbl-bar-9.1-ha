"""Base entity."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JblBarCoordinator


EQ_NOT_INSTALLED = "EQ support is not installed"


def eq_installed(doc: dict[str, Any] | None) -> bool:
    """True when the remote was built with the Front EQ helper.

    The remote only reports EQ as available while the bar is on, in Standard
    mode, with a supported audio route, so entities are created whenever the
    helper exists and are unavailable the rest of the time.
    """
    eq = (doc or {}).get("eq")
    return isinstance(eq, dict) and eq.get("error") != EQ_NOT_INSTALLED


def advanced_controls(doc: dict[str, Any] | None) -> bool:
    """True when the remote has the advanced controls (Smart Mode, audio sync).

    Both shipped together; the audio sync value is the only visible marker.
    """
    return "av_sync_ms" in ((doc or {}).get("sound") or {})


class JblBarEntity(CoordinatorEntity[JblBarCoordinator]):
    """Entity backed by the remote's state document."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: JblBarCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        assert entry is not None and entry.unique_id is not None
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_translation_key = None if key == "media_player" else key.rsplit("_", 1)[0] if key.startswith("eq_band_") else key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name="JBL Bar 9.1",
            manufacturer="JBL",
            model="Bar 9.1 True Wireless Surround",
            configuration_url=f"http://{coordinator.client.host}",
        )

    @property
    def state_doc(self) -> dict[str, Any]:
        return self.coordinator.data or {}

    @property
    def sound(self) -> dict[str, Any]:
        return self.state_doc.get("sound") or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self.state_doc.get("available"))

    @property
    def eq_ready(self) -> bool:
        return bool((self.state_doc.get("eq") or {}).get("available"))

    @property
    def awake(self) -> bool:
        return self.coordinator.awake
