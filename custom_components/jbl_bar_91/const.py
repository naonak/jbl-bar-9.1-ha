"""Constants for the JBL Bar 9.1 integration."""
from __future__ import annotations

import logging

DOMAIN = "jbl_bar_91"
LOGGER = logging.getLogger(__package__)

# Sources the remote can select directly, keyed by the name the remote reports.
SOURCES = {"TV / ARC": ("TV", "input_tv"), "HDMI": ("HDMI", "input_hdmi"), "Bluetooth": ("Bluetooth", "input_bluetooth")}

VOLUME_MAX = 32

# Front EQ presets, identical to the browser remote's (dB cuts, 125 Hz .. 8 kHz).
EQ_PRESETS: dict[str, list[float]] = {
    "original": [0, 0, 0, 0, 0],
    "less_bass": [-4, -2, 0, 0, 0],
    "clear_dialogue": [-3, -1, 0, 0, -1],
    "softer_treble": [0, 0, 0, -2, -3],
    "warm": [0, 0, -1, -2, -3],
    "bright": [-3, -2, -1, 0, 0],
    "vocal_focus": [-4, -2, 0, -1, -2],
}
EQ_BANDS = (125, 500, 2000, 4000, 8000)

# Audio sync (lip-sync) delay: 10 ms steps up to 250 ms, only on TV/ARC (0) and
# HDMI (3). Current remotes take the whole range in one request (one sync
# session); older ones refuse more than 80 ms and the change is then split.
AV_SYNC_STEP = 10
AV_SYNC_MAX = 250
AV_SYNC_CHUNK = 250
AV_SYNC_LEGACY_CHUNK = 50
AV_SYNC_SOURCES = (0, 3)

# Center levels exposed by remotes that include the center-level control.
CENTER_DB = (0, 2.4, 4.8, 7.2, 9.6, 12)
