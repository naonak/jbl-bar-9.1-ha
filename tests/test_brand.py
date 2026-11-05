"""Brand assets read by Home Assistant (2026.3+) and checked by the HACS action."""
from __future__ import annotations

import struct
from pathlib import Path

BRAND = Path(__file__).parents[1] / "custom_components" / "jbl_bar_91" / "brand"


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
    return struct.unpack(">II", data[16:24])


def test_brand_assets() -> None:
    assert png_size(BRAND / "icon.png") == (256, 256)
    assert png_size(BRAND / "icon@2x.png") == (512, 512)
    assert png_size(BRAND / "logo.png") == (256, 128)
    assert png_size(BRAND / "logo@2x.png") == (512, 256)
