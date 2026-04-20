# GNSS Tracker

Raspberry Pi Pico 2W + Waveshare Pico-GPS-L76K + 0.96" SSD1306 OLED

---

## File layout

| File | Purpose |
|------|---------|
| main.py | Entry point - main loop |
| config_manager.py | Reads/writes config.json, creates it on first boot |
| gnss.py | UART driver, NMEA parser, raw sentence buffer |
| display_manager.py | SSD1306 OLED driver, all display pages |
| button_handler.py | 3-button short/long press with debounce |
| track_logger.py | CSV / GPX track logging to flash |
| stream_server.py | TCP server for NMEA or JSON streaming |
| state.py | Shared runtime state (not persisted) |
| wifi_helper.py | Pico 2W WiFi connect helper |
| logger.py | Configurable debug logger |

### External dependency

Copy `ssd1306.py` to the Pico flash root before running.
Source: https://github.com/micropython/micropython-lib/tree/master/micropython/drivers/display/ssd1306

---

## Wiring

### GNSS Module (Waveshare Pico-GPS-L76K)

The L76K is a Pico HAT that plugs directly onto the Pico headers.
UART is routed to GP0/GP1 on this board.

| Signal | Pico GPIO | Pico Pin |
|--------|-----------|----------|
| GNSS TX -> Pico RX | GP1 | Pin 2 |
| GNSS RX <- Pico TX | GP0 | Pin 1 |

### OLED Display (0.96" SSD1306 128x64)

| OLED Pin | Pico GPIO | Pico Pin |
|----------|-----------|----------|
| SDA | GP8 | Pin 11 |
| SCL | GP9 | Pin 12 |
| VCC | 3V3 | Pin 36 |
| GND | GND | Pin 38 |

### Buttons

Each button connects between its GPIO pin and GND.
The Pico's internal pull-up resistors are used - no external resistors needed.

| Button | GPIO | Pico Pin | Short Press | Long Press (>1s) |
|--------|------|----------|-------------|-----------------|
| A | GP14 | Pin 19 | Display on/off | Show config screen |
| B | GP15 | Pin 20 | Start/stop track | Location on/off |
| C | GP16 | Pin 21 | Soft reset | Hard reset |

All button GND legs can share a single GND pin (pins 3, 8, 13, 18, 23, 28, 33 or 38).

#### Breadboard wiring

```
Pico Pin 19 (GP14) --- BTN_A leg 1    BTN_A leg 2 --- GND rail
Pico Pin 20 (GP15) --- BTN_B leg 1    BTN_B leg 2 --- GND rail
Pico Pin 21 (GP16) --- BTN_C leg 1    BTN_C leg 2 --- GND rail
```

#### Button test (run in REPL before full deployment)

```python
import machine, time
a = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)
b = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)
c = machine.Pin(16, machine.Pin.IN, machine.Pin.PULL_UP)
while True:
    if a.value() == 0: print("BTN A")
    if b.value() == 0: print("BTN B")
    if c.value() == 0: print("BTN C")
    time.sleep(0.1)
```

---

## Display layout

The display has a permanent status bar at the top that alternates between
a time row and a date row every `status_alt_s` seconds (default 10).

### Status bar - time row

```
19:27:34 3D 11/11
```

| Field | Description |
|-------|-------------|
| HH:MM:SS | Current time, GMT or BST auto-adjusted |
| 3D / 2D / (/) | Fix type. (/) means no fix |
| nn/nn | Satellites used / satellites in view |

### Status bar - date row

```
19/04/26 3D 11/11
```

| Field | Description |
|-------|-------------|
| DD/MM/YY | Current date |
| 3D / 2D / (/) | Fix type |
| nn/nn | Satellites used / in view |

BST is automatically applied when the GPS date falls within British Summer
Time (last Sunday in March to last Sunday in October).

### Display pages

Four pages cycle via the config button (Button A long press shows config;
to cycle pages a short press of A toggles the display - this can be extended
to add page cycling as needed).

#### Page 0 - Main (default)

```
19:27:34 3D 11/11     <- status bar
--------------------------
La 55.02986           <- latitude
Lo -1.54938           <- longitude
Spd: N/A              <- speed (N/A below min_speed_kmh threshold)
Hdg: N/A              <- heading + cardinal (N/A below min_heading_kmh)
Alt:79m          REC  <- altitude + REC indicator when recording
```

#### Page 1 - Altitude detail

```
19/04/26 3D 11/11
--------------------------
Alt: 79.1m
Hdg: 42d
     NE
```

#### Page 2 - Track status

```
19:27:34 3D 11/11
--------------------------
Track: ACTIVE
Loc: ON
Pts: 42
```

#### Page 3 - Stream status

```
19/04/26 3D 11/11
--------------------------
Stream: ON
0.0.0.0:10110
Fmt: nmea
```

#### Config screen (Button A long press)

```
-- CONFIG --
Stream: OFF
Port: 10110
Log: csv
Units: metric
```

Displayed for `config_display_s` seconds then returns to normal.

---

## Configuration reference

All settings are stored in `config.json` on the Pico flash.
The file is created automatically on first boot with the defaults below.
Edit it directly in Thonny or via mpremote.

> Note: saved values in config.json always override defaults in
> config_manager.py. If you change a default in code, delete config.json
> and reboot to regenerate it.

### GNSS

| Key | Default | Description |
|-----|---------|-------------|
| gnss_uart_id | 0 | UART bus (0 or 1) |
| gnss_tx_pin | 0 | Pico TX pin (connects to module RX) |
| gnss_rx_pin | 1 | Pico RX pin (connects to module TX) |
| gnss_baudrate | 9600 | UART baud rate |
| gnss_timeout_s | 5 | UART timeout in seconds |

On startup the tracker sends `$PCAS04,7*1E` to enable all constellations
(GPS + GLONASS + BeiDou + Galileo).

### Display

| Key | Default | Description |
|-----|---------|-------------|
| display_i2c_id | 0 | I2C bus (0 or 1) |
| display_sda_pin | 8 | SDA GPIO pin |
| display_scl_pin | 9 | SCL GPIO pin |
| display_i2c_freq | 400000 | I2C frequency in Hz |
| display_width | 128 | OLED width in pixels |
| display_height | 64 | OLED height in pixels |
| display_address | 0x3C | I2C address (use 0x3D if 0x3C not found) |
| display_rotate | false | Rotate display 180 degrees |
| display_splash_time | 7 | Seconds to show splash screen on boot |

### Buttons

| Key | Default | Description |
|-----|---------|-------------|
| btn_a_pin | 14 | Button A GPIO pin |
| btn_b_pin | 15 | Button B GPIO pin |
| btn_c_pin | 16 | Button C GPIO pin |
| btn_debounce_ms | 50 | Debounce time in milliseconds |
| btn_long_ms | 1000 | Long press threshold in milliseconds |

### Track logging

| Key | Default | Description |
|-----|---------|-------------|
| track_dir | /tracks | Directory on Pico flash for track files |
| track_format | csv | File format: csv or gpx |
| track_interval_s | 5 | Minimum seconds between logged points |

Track files are named by timestamp, e.g. `20260419_192734.csv`.

CSV columns: `utc, lat, lon, alt_m, speed_kmh, heading, sats`

GPX files include `<ele>` (altitude) and `<time>` tags per track point.

Retrieve track files with mpremote:
```bash
mpremote connect /dev/ttyACM0 cp :tracks/20260419_192734.csv .
```

### GPS data streaming

| Key | Default | Description |
|-----|---------|-------------|
| stream_enabled | false | Enable TCP streaming |
| stream_host | 0.0.0.0 | Bind address (0.0.0.0 = all interfaces) |
| stream_port | 10110 | TCP port (10110 is NMEA standard) |
| stream_format | nmea | Output format: nmea or json |

Streaming requires WiFi. When enabled, raw NMEA sentences are buffered
as they arrive from the module and sent directly to the connected client.
No sentence reconstruction is performed.

Only one client connection is supported at a time.

Connect with netcat:
```bash
nc <pico-ip> 10110
```

Log to file while watching:
```bash
nc <pico-ip> 10110 | tee track.nmea
```

JSON mode sends one object per update cycle:
```json
{
  "utc_time": "192734.000",
  "utc_date": "2026-04-19",
  "fix": "3D FIX",
  "fix_type": 3,
  "sats_used": 11,
  "sats_view": 11,
  "lat": 55.029860,
  "lon": -1.549380,
  "alt_m": 79.1,
  "speed_kmh": 0.0,
  "heading": 42.03,
  "cardinal": "NE",
  "valid": true
}
```

### WiFi

| Key | Default | Description |
|-----|---------|-------------|
| wifi_ssid | "" | WiFi network name |
| wifi_password | "" | WiFi password |

WiFi is only used when `stream_enabled` is true.

### Display content

| Key | Default | Description |
|-----|---------|-------------|
| show_speed | true | Show speed on main page |
| show_altitude | true | Show altitude on main page |
| show_heading | true | Show heading on main page |
| show_cardinal | true | Show cardinal direction with heading |
| min_speed_kmh | 2.0 | Show N/A for speed below this value |
| min_heading_kmh | 2.0 | Show N/A for heading when speed below this value |
| coord_format | dd | Coordinate format: dd (decimal) or dms |
| units | metric | Units: metric (km/h, m) or imperial (mph, ft) |

Speed and heading display N/A below their thresholds to suppress GPS
drift when stationary.

### Status bar

| Key | Default | Description |
|-----|---------|-------------|
| status_alt_s | 10 | Seconds between time and date rows |

### Debug logging

| Key | Default | Description |
|-----|---------|-------------|
| debug_level | 3 | Log verbosity (see below) |
| config_display_s | 15 | Seconds to show config screen on long press |

Log levels:

| Value | Level | Output |
|-------|-------|--------|
| 0 | OFF | No output |
| 1 | ERROR | Failures only |
| 2 | WARN | Errors and warnings |
| 3 | INFO | Normal operation (recommended for production) |
| 4 | DEBUG | Every NMEA sentence and all events |

---

## First boot

1. Copy all `.py` files and `ssd1306.py` to the Pico flash root
2. `config.json` is created automatically on first boot with all defaults
3. Edit `config.json` in Thonny to set WiFi credentials and any pin changes
4. Reboot

## Updating files with mpremote

```bash
# Install mpremote
pip install mpremote

# Find port
mpremote connect list

# Copy all files
mpremote connect /dev/ttyACM0 cp -r gnss_tracker/. :

# Copy a single updated file
mpremote connect /dev/ttyACM0 cp gnss_tracker/gnss.py :gnss.py

# Delete config to regenerate with new defaults
mpremote connect /dev/ttyACM0 rm :config.json

# Open REPL
mpremote connect /dev/ttyACM0 repl
```

## I2C scan (if OLED not found)

```python
import machine
i2c = machine.I2C(0, sda=machine.Pin(8), scl=machine.Pin(9), freq=100000)
print(i2c.scan())
# Returns list of addresses e.g. [60] = 0x3C
```

If the scan returns an empty list, check wiring. If it returns `[61]`
(0x3D) update `display_address` in config.json.

## Soft vs hard reset

| Action | Button | Effect |
|--------|--------|--------|
| Soft reset | C short | Restarts GNSS and streamer, keeps config |
| Hard reset | C long | Full machine.reset(), equivalent to power cycle |
