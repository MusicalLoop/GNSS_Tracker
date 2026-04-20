# GNSS Tracker — Pico 2W + L76K + SSD1306

## File layout

```
main.py             ← entry point
config_manager.py   ← reads/writes config.json (auto-created on first boot)
gnss.py             ← UART driver + NMEA parser
display_manager.py  ← SSD1306 OLED (128×64)
button_handler.py   ← 3-button short/long press
track_logger.py     ← CSV / GPX logging to flash
stream_server.py    ← TCP NMEA / JSON stream
state.py            ← shared runtime state
wifi_helper.py      ← Pico 2W WiFi connect helper
```

## Default wiring

| Signal        | Pico GPIO |
|---------------|-----------|
| GNSS TX→RX    | GP5       |
| GNSS RX←TX    | GP4       |
| OLED SDA      | GP8       |
| OLED SCL      | GP9       |
| Button A      | GP10      |
| Button B      | GP11      |
| Button C      | GP12      |
| Button common | GND       |

All pins are configurable in `config.json`.

## Button actions

| Button | Short press        | Long press (>1 s) |
|--------|--------------------|-------------------|
| A      | Display on/off     | Show config       |
| B      | Start/stop track   | Location on/off   |
| C      | Soft reset         | Hard reset        |

## Display layout

```
┌──────────────────────────┐
│ 3D FIX            08/12  │  ← status bar: fix | sats used/in-view
│──────────────────────────│
│ Lat  53.38291            │
│ Lon  -1.46590            │
│ 12.3km/h                 │
│ 270deg  W           REC  │  ← REC shown when tracking
└──────────────────────────┘
```

Pages cycle via long-press A (or extend button_handler as needed):
- **Page 0**: Lat/Lon + speed + heading
- **Page 1**: Altitude + cardinal direction
- **Page 2**: Track status + point count
- **Page 3**: Stream IP/port + status

## First boot

`config.json` is created automatically with safe defaults.
Edit it directly on the Pico flash (via Thonny or `rshell`) or update
values via `config.set("key", value)` in the REPL.

## WiFi / streaming

1. Add to `config.json`:
   ```json
   "wifi_ssid": "YourSSID",
   "wifi_password": "YourPassword",
   "stream_enabled": true,
   "stream_port": 10110,
   "stream_format": "nmea"
   ```
2. In `main.py`, call `wifi_helper.connect(...)` before `streamer.start()`.
3. Connect any NMEA-capable app (e.g. OpenCPN, GPSd) to `<pico-ip>:10110`.
   Or set `stream_format: "json"` for plain JSON lines.

## Dependencies

Copy these to Pico flash root:
- `ssd1306.py` — from https://github.com/micropython/micropython-lib/tree/master/micropython/drivers/display/ssd1306

No other external libraries required.

## Track files

Tracks are saved to `/tracks/` on the Pico's internal flash.
Format is set by `track_format` in config (`csv` or `gpx`).
Retrieve via Thonny file browser or `rshell cp`.
