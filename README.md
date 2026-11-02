# JBL Bar 9.1 for Home Assistant

Control a **JBL Bar 9.1 True Wireless Surround** from Home Assistant through the soundbar's local browser remote from [kisinga/jbl-bar-9.1](https://github.com/kisinga/jbl-bar-9.1). No cloud, no extra hardware: Home Assistant talks to the remote on your LAN.

Not affiliated with JBL or Harman. Experimental, like the remote it relies on.

## Requirements

- The **browser remote** from [kisinga/jbl-bar-9.1](https://github.com/kisinga/jbl-bar-9.1#local-browser-remote) installed on the bar and reachable at `http://<bar-ip>:8080`.
- Home Assistant **2025.1** or newer.
- Home Assistant's IP address inside the remote's `allowed_cidr` (the subnet given to `tools/build_web.py --allowed-cidr`). Otherwise setup reports that the remote refused Home Assistant.

## Installation

**HACS:** HACS → ⋮ → *Custom repositories* → add this repository's URL with category *Integration*, then install **JBL Bar 9.1 (web remote)** and restart Home Assistant.

**Manual:** copy `custom_components/jbl_bar_91` into your Home Assistant `config/custom_components/` folder and restart.

Then: *Settings → Devices & services → Add integration → JBL Bar 9.1 (web remote)*, and enter the bar's IP address (`192.168.1.50` or `192.168.1.50:8080`).

## Entities

| Entity | What it does |
| --- | --- |
| Media player | Power, volume (0–32 shown as 0–100 %), mute, source (TV, HDMI, Bluetooth), play/pause/next/previous/stop when the current source supports them, now playing (title, artist, album, app) |
| Bass level | 1–5 |
| Center level | 0–5 (+0 to +12 dB), only when the remote includes the center-level control |
| Atmos height | Low, Mid, High |
| Rear speakers | Low, Mid, High, Muted (rear speakers must be undocked) |
| Front EQ preset | The remote's presets: Original, Less bass, Clear dialogue, Softer treble, Warm, Bright, Vocal focus |
| Front EQ 125 Hz … 8 kHz | −6 to 0 dB per band; each change applies the full curve |
| Night mode | Switch |
| Smart mode | Switch: on = Smart, off = Standard (the bar returns to Smart at power-on). Needs a remote with the advanced controls |
| Audio sync | Lip-sync delay, 0–250 ms in 10 ms steps, TV and HDMI inputs only (each change takes about ten seconds per 80 ms). Needs a remote with the advanced controls |
| Bluetooth pairing | Button |
| Calibrate surround | Button: starts the next step of the wireless surround calibration (both rear speakers undocked; step 1 near your listening position, step 2 at their final places; about 35 s each). Needs a remote with the setup controls |
| Pair subwoofer | Button: opens subwoofer pairing on the bar for up to three minutes; then hold the button on the back of the subwoofer until it flashes white quickly. Needs a remote with the setup controls |
| Audio format | Sensor: what the bar last showed for the incoming stream, e.g. `DOLBY SURROUND DD+` (while on). Needs a remote with the setup controls |
| Calibration, Subwoofer | Diagnostic sensors: calibration progress (Idle, Measuring, Step 1 done…) and subwoofer pairing/connection messages |
| Standard mode | Button, only with older remotes (replaced by the Smart mode switch) |
| Sound mode, Bluetooth device, Bluetooth audio | Sensors |
| Rear speakers docked, Bluetooth connected | Binary sensors |
| CPU, Memory used, Temperature, Wi-Fi signal, Uptime | Diagnostics (the last two disabled by default) |

## How it behaves

- **Live updates.** While the bar is on, the integration listens to the remote's event stream, so changes from the physical remote or the web page appear immediately. The stream makes the remote sample the bar every second, so it is closed in standby; a light state request every 15 s then detects the wake.
- **Same rules as the web page.** One control at a time. Levels that the bar can only cycle (bass, center, Atmos, rear, volume) are stepped one press at a time with read-back before the next. Switches and mute only send a toggle when the read-back state differs.
- **Refusals are shown, never retried.** If the remote refuses a control (for example a playback command the source does not support, rear levels while the speakers are docked, or another control already running), Home Assistant shows the remote's message. A stale security token after a remote restart is refreshed and the request is sent once more, because the remote rejects such requests before acting.
- **Front EQ** follows the remote: cuts only, front left/right only, and it resets when the bar restarts.

## Troubleshooting

- *The remote refused Home Assistant*: rebuild the remote with an `allowed_cidr` that includes Home Assistant's address, and use the bar's IP address rather than `jbl.local`.
- *Cannot reach the browser remote*: check `http://<bar-ip>:8080` in a browser on the same network.
- Diagnostics (*Download diagnostics* on the device page) contain the last state with the security token and names removed.

## Development

```sh
pip install pytest-homeassistant-custom-component
pytest -q
```

Tests run Home Assistant against a fake remote that enforces the real API rules (JSON content type, CSRF token, `409` refusals, event stream).

## Français

Intégration Home Assistant pour la **JBL Bar 9.1**, via la télécommande web locale de [kisinga/jbl-bar-9.1](https://github.com/kisinga/jbl-bar-9.1). Installez d'abord cette télécommande sur la barre, avec un `allowed_cidr` qui inclut l'adresse de Home Assistant. Ajoutez ensuite ce dépôt dans HACS (*Dépôts personnalisés*, catégorie *Intégration*), installez-le, redémarrez, puis ajoutez l'intégration en saisissant l'IP de la barre. L'interface est traduite en français.

## License

MIT
