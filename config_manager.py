"""
Config Manager
Creates config.json on first boot; reads it on subsequent boots.
"""

import json
import os

CONFIG_FILE = "config.json"

DEFAULTS = {
    # GNSS
    "gnss_uart_id":     0,
    "gnss_tx_pin":      12,
    "gnss_rx_pin":      13,
    "gnss_baudrate":    9600,
    "gnss_timeout_s":   5,

    # Display
    "display_i2c_id":   0,
    "display_sda_pin":  8,
    "display_scl_pin":  9,
    "display_i2c_freq": 400000,
    "display_width":    128,
    "display_height":   64,
    "display_address":  0x3C,
    "display_rotate":   False,

    # Buttons (GPIO pin numbers)
    # Button A: short=display toggle, long=setup/config
    # Button B: short=track toggle,   long=location toggle
    # Button C: short=soft reset,     long=hard reset
    "btn_a_pin":        10,
    "btn_b_pin":        11,
    "btn_c_pin":        12,
    "btn_debounce_ms":  50,
    "btn_long_ms":      1000,

    # Track logging
    "track_dir":        "/tracks",
    "track_format":     "csv",
    "track_interval_s": 5,

    # GPS data streaming
    "stream_enabled":   False,
    "stream_host":      "0.0.0.0",
    "stream_port":      10110,
    "stream_format":    "nmea",

    # WiFi
    "wifi_ssid":        "",
    "wifi_password":    "",

    # Display content
    "show_speed":       True,
    "show_altitude":    True,
    "show_heading":     True,
    "show_cardinal":    True,
    "min_speed_kmh":    2.0,
    "min_heading_kmh":  2.0,
    "coord_format":     "dd",
    "units":            "metric",

    # Logging
    # 0=OFF, 1=ERROR, 2=WARN, 3=INFO, 4=DEBUG
    "debug_level":      3,
    "config_display_s":  15,
}


class ConfigManager:
    def __init__(self):
        self._data = {}
        self._load()

    def get(self, key, fallback=None):
        return self._data.get(key, fallback)

    def set(self, key, value):
        self._data[key] = value
        self._save()

    def all(self):
        return dict(self._data)

    def _load(self):
        if CONFIG_FILE in os.listdir():
            try:
                with open(CONFIG_FILE, "r") as f:
                    saved = json.load(f)
                self._data = dict(DEFAULTS)
                self._data.update(saved)
                print("[Config] Loaded", CONFIG_FILE)
                return
            except Exception as e:
                print("[Config] Read error:", e, "- rebuilding defaults")

        self._data = dict(DEFAULTS)
        self._save()
        print("[Config] Created", CONFIG_FILE, "with defaults")

    def _save(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self._data, f)
        except Exception as e:
            print("[Config] Save error:", e)
