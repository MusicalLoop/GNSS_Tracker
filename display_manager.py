"""
Display Manager
Drives a 0.96" SSD1306 OLED (128x64) over I2C.
Requires: ssd1306.py from MicroPython drivers (copy to Pico flash).

Layout (128x64):
  Row 0-10  : Status bar - fix label | sats used/in-view
  Row 11    : Separator line
  Row 12-63 : Content area (varies by page)
"""

import machine
import time
from ssd1306 import SSD1306_I2C
from logger import Logger

log = Logger("Display")

PAGE_MAIN   = 0
PAGE_ALT    = 1
PAGE_TRACK  = 2
PAGE_STREAM = 3


class DisplayManager:
    def __init__(self, config):
        self._cfg  = config
        self._oled = self._init_oled()
        self._page = PAGE_MAIN
        self._on   = True

    def off(self):
        if self._oled:
            self._oled.poweroff()
        self._on = False

    def on(self):
        if self._oled:
            self._oled.poweron()
        self._on = True

    def update(self, fix, state):
        if not self._on or not self._oled:
            return
        self._oled.fill(0)
        self._draw_status_bar(fix)
        self._draw_separator()
        if self._page == PAGE_MAIN:
            self._draw_main(fix, state)
        elif self._page == PAGE_ALT:
            self._draw_alt(fix)
        elif self._page == PAGE_TRACK:
            self._draw_track(state)
        elif self._page == PAGE_STREAM:
            self._draw_stream()
        self._oled.show()

    def next_page(self):
        self._page = (self._page + 1) % 4

    def show_splash(self):
        if not self._oled:
            return
        self._oled.fill(0)
        self._text("GNSS TRACKER", 14, 20)
        self._text("Initialising...", 8, 40)
        self._oled.show()

    def show_config_menu(self, config):
        if not self._oled:
            return
        self._oled.fill(0)
        self._text("-- CONFIG --", 20, 0)
        self._text("Stream: " + ("ON" if config.get("stream_enabled") else "OFF"), 0, 16)
        self._text("Port: " + str(config.get("stream_port")), 0, 26)
        self._text("Log: " + config.get("track_format", " "), 0, 36)
        self._text("Units: " + config.get("units", " "), 0, 46)
        self._oled.show()

    def show_message(self, line1, line2=""):
        if not self._oled:
            return
        self._oled.fill(0)
        self._text(line1, 0, 20)
        self._text(line2, 0, 36)
        self._oled.show()

    def _draw_status_bar(self, fix):
        if fix:
            label = fix.fix_label()
            sats  = "{}/{}".format(fix.sats_used, fix.sats_in_view)
        else:
            label = "NO FIX"
            sats  = "0/0"
        # Left: fix label (max 8 chars), right: sats
        line = "{:<8}{}".format(label, sats)
        log.debug("Status bar: " + line)
        self._text(line, 0, 0)

    def _draw_separator(self):
        self._oled.hline(0, 11, self._cfg.get("display_width"), 1)

    def _draw_main(self, fix, state):
        if not fix or not fix.is_valid:
            self._text("Waiting for fix", 0, 20)
            return
        coord_fmt = self._cfg.get("coord_format", "dd")
        self._text("La " + self._fmt_coord(fix.lat, coord_fmt), 0, 14)
        self._text("Lo " + self._fmt_coord(fix.lon, coord_fmt), 0, 24)
        if self._cfg.get("show_speed"):
            min_spd = self._cfg.get("min_speed_kmh", 2.0)
            if fix.speed_kmh < min_spd:
                self._text("Spd: N/A", 0, 36)
            else:
                spd  = fix.speed_kmh if self._cfg.get("units") == "metric" else fix.speed_kmh * 0.621371
                unit = "km/h" if self._cfg.get("units") == "metric" else "mph"
                self._text("{:.1f} {}".format(spd, unit), 0, 36)
        if self._cfg.get("show_heading") and self._cfg.get("show_cardinal"):
            min_hdg = self._cfg.get("min_heading_kmh", 2.0)
            if fix.speed_kmh < min_hdg:
                self._text("Hdg: N/A", 0, 46)
            else:
                self._text("{:.0f}d {}".format(fix.heading, fix.cardinal()), 0, 46)
        if self._cfg.get("show_altitude"):
            alt  = fix.alt_m if self._cfg.get("units") == "metric" else fix.alt_m * 3.28084
            unit = "m" if self._cfg.get("units") == "metric" else "ft"
            alt_str = "Alt:{:.0f}{}".format(alt, unit)
            if state.tracking:
                alt_str = alt_str + " REC"
            self._text(alt_str, 0, 56)
        elif state.tracking:
            self._text("REC", 104, 56)

    def _draw_alt(self, fix):
        if not fix or not fix.is_valid:
            self._text("No data", 0, 20)
            return
        alt  = fix.alt_m if self._cfg.get("units") == "metric" else fix.alt_m * 3.28084
        unit = "m" if self._cfg.get("units") == "metric" else "ft"
        self._text("Alt: {:.1f}{}".format(alt, unit), 0, 14)
        self._text("Hdg: {:.0f}d".format(fix.heading), 0, 26)
        self._text("     " + fix.cardinal(), 0, 36)

    def _draw_track(self, state):
        self._text("Track: " + ("ACTIVE" if state.tracking else "IDLE"), 0, 14)
        self._text("Loc: " + ("ON" if state.location_active else "OFF"), 0, 26)
        self._text("Pts: {}".format(state.track_points), 0, 38)

    def _draw_stream(self):
        enabled = self._cfg.get("stream_enabled")
        self._text("Stream:" + ("ON" if enabled else "OFF"), 0, 14)
        self._text("{}:{}".format(
            self._cfg.get("stream_host"),
            self._cfg.get("stream_port")), 0, 26)
        self._text("Fmt:" + self._cfg.get("stream_format", "nmea"), 0, 40)

    def _text(self, s, x, y, col=1):
        self._oled.text(str(s)[:21], x, y, col)

    @staticmethod
    def _fmt_coord(val, fmt):
        if fmt == "dms":
            deg  = int(abs(val))
            mins = int((abs(val) - deg) * 60)
            secs = ((abs(val) - deg) * 60 - mins) * 60
            sign = "-" if val < 0 else ""
            return "{}{}d{}'{}\"".format(sign, deg, mins, int(secs))
        return "{:.5f}".format(val)

    def _init_oled(self):
        try:
            i2c = machine.I2C(
                self._cfg.get("display_i2c_id"),
                sda=machine.Pin(self._cfg.get("display_sda_pin")),
                scl=machine.Pin(self._cfg.get("display_scl_pin")),
                freq=self._cfg.get("display_i2c_freq"),
            )
            devices = i2c.scan()
            log.info("I2C scan found: " + str(devices))
            oled = SSD1306_I2C(
                self._cfg.get("display_width"),
                self._cfg.get("display_height"),
                i2c,
                addr=self._cfg.get("display_address"),
            )
            if self._cfg.get("display_rotate"):
                oled.rotate(True)
            log.info("OLED ready ({}x{} @ 0x{:02X})".format(
                self._cfg.get("display_width"),
                self._cfg.get("display_height"),
                self._cfg.get("display_address"),
            ))
            return oled
        except Exception as e:
            log.error("OLED init failed: " + str(e))
            return None
