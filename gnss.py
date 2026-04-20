"""
GNSS Module
Drives the Waveshare Pico-GPS-L76K via UART.
Parses GGA, RMC, GSV and GSA sentences.
"""

import machine
import time
from logger import Logger

log = Logger("GNSS")


class GNSSFix:
    def __init__(self):
        self.is_valid     = False
        self.fix_type     = 0
        self.sats_used    = 0
        self.sats_in_view = 0
        self.lat          = 0.0
        self.lon          = 0.0
        self.alt_m        = 0.0
        self.speed_kmh    = 0.0
        self.heading      = 0.0
        self.utc_time     = ""
        self.utc_date     = ""

    def fix_label(self):
        if self.fix_type == 2:
            return "2D FIX"
        elif self.fix_type == 3:
            return "3D FIX"
        else:
            return "NO FIX"

    def cardinal(self):
        dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
                "S","SSW","SW","WSW","W","WNW","NW","NNW"]
        idx = int((self.heading + 11.25) / 22.5) % 16
        return dirs[idx]


class GNSSModule:
    def __init__(self, config):
        self._cfg       = config
        self._uart      = None
        self._buf       = b""
        self._fix       = GNSSFix()
        self._sentences = 0   # total sentences received
        self._last_report_ms = 0

    def start(self):
        log.info("Starting UART id={} tx=GP{} rx=GP{} baud={}".format(
            self._cfg.get("gnss_uart_id"),
            self._cfg.get("gnss_tx_pin"),
            self._cfg.get("gnss_rx_pin"),
            self._cfg.get("gnss_baudrate"),
        ))
        try:
            self._uart = machine.UART(
                self._cfg.get("gnss_uart_id"),
                baudrate=self._cfg.get("gnss_baudrate"),
                tx=machine.Pin(self._cfg.get("gnss_tx_pin")),
                rx=machine.Pin(self._cfg.get("gnss_rx_pin")),
            )
            log.info("UART started OK")
        except Exception as e:
            log.error("UART init failed: " + str(e))
            return

        # Enable all constellations: GPS + GLONASS + BeiDou + Galileo
        time.sleep_ms(100)
        self._uart.write("$PCAS04,7*1E\r\n")
        log.info("Sent PCAS04,7 - all constellations enabled")

    def stop(self):
        if self._uart:
            self._uart.deinit()
            self._uart = None
            log.info("UART stopped")

    def update(self):
        if not self._uart:
            log.warn("update() called but UART is not running")
            return self._fix

        # Read available bytes
        n = self._uart.any()
        if n:
            log.debug("UART bytes available: {}".format(n))
            self._buf += self._uart.read(n)
        else:
            log.debug("No UART data")

        # Process complete sentences
        while b"\r\n" in self._buf:
            line, self._buf = self._buf.split(b"\r\n", 1)
            try:
                sentence = line.decode("ascii").strip()
                if sentence:
                    log.debug("RX: " + sentence)
                    if self._validate_checksum(sentence):
                        self._parse(sentence)
                        self._sentences += 1
                    else:
                        log.warn("Checksum fail: " + sentence)
            except Exception as e:
                log.warn("Decode error: " + str(e))

        # Periodic status report at INFO level every 10 seconds
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_report_ms) > 10000:
            self._last_report_ms = now
            log.info("Status: sentences={} fix_type={} sats={}/{} valid={}".format(
                self._sentences,
                self._fix.fix_type,
                self._fix.sats_used,
                self._fix.sats_in_view,
                self._fix.is_valid,
            ))
            if self._fix.is_valid:
                log.info("Position: lat={:.6f} lon={:.6f} alt={:.1f}m".format(
                    self._fix.lat, self._fix.lon, self._fix.alt_m))

        return self._fix

    def _parse(self, sentence):
        parts = sentence.split(",")
        tag   = parts[0].lstrip("$")
        if tag in ("GNGGA", "GPGGA"):
            self._parse_gga(parts)
        elif tag in ("GNRMC", "GPRMC"):
            self._parse_rmc(parts)
        elif tag in ("GPGSV", "GLGSV", "GNGSV", "GAGSV", "GBGSV", "BDGSV"):
            self._parse_gsv(parts)
        elif tag in ("GNGSA", "GPGSA"):
            self._parse_gsa(parts)
        elif tag in ("GNVTG", "GPVTG"):
            self._parse_vtg(parts)
        elif tag in ("GNZDA", "GPZDA"):
            self._parse_zda(parts)
        elif tag in ("GPTXT", "GNTXT"):
            if len(parts) >= 5:
                log.info("Module msg: " + parts[4].split("*")[0])
        elif tag in ("GNGLL", "GPGLL"):
            pass
        else:
            log.debug("Unhandled sentence type: " + tag)

    def _parse_gga(self, p):
        try:
            if len(p) < 15:
                log.warn("GGA too short: {} fields".format(len(p)))
                return
            quality = int(p[6]) if p[6] else 0
            sats    = int(p[7]) if p[7] else 0
            log.debug("GGA quality={} sats={} time={}".format(quality, sats, p[1]))
            if quality == 0:
                if self._fix.is_valid:
                    log.warn("GGA quality=0 - lost fix")
                self._fix.is_valid = False
                self._fix.fix_type = 0
            else:
                was_valid = self._fix.is_valid
                self._fix.is_valid  = True
                self._fix.lat       = self._nmea_coord(p[2], p[3])
                self._fix.lon       = self._nmea_coord(p[4], p[5])
                self._fix.sats_used = sats
                # Clamp to avoid sats_used > sats_in_view display glitch
                if self._fix.sats_in_view > 0 and self._fix.sats_used > self._fix.sats_in_view:
                    self._fix.sats_used = self._fix.sats_in_view
                self._fix.alt_m     = float(p[9]) if p[9] else 0.0
                self._fix.utc_time  = p[1]
                if not was_valid:
                    log.info("Fix acquired! lat={:.6f} lon={:.6f} sats={}".format(
                        self._fix.lat, self._fix.lon, sats))
        except Exception as e:
            log.error("GGA parse error: " + str(e))

    def _parse_rmc(self, p):
        try:
            if len(p) < 9:
                log.warn("RMC too short: {} fields".format(len(p)))
                return
            log.debug("RMC status={} speed={} heading={}".format(p[2], p[7], p[8]))
            if p[2] == "A":
                self._fix.speed_kmh = (float(p[7]) if p[7] else 0.0) * 1.852
                self._fix.heading   = float(p[8]) if p[8] else 0.0
        except Exception as e:
            log.error("RMC parse error: " + str(e))

    def _parse_gsa(self, p):
        try:
            if len(p) < 3:
                return
            mode = int(p[2]) if p[2] else 1
            if mode != self._fix.fix_type:
                log.info("Fix type changed: {} -> {}".format(
                    self._fix.fix_type, mode))
            self._fix.fix_type = mode
            log.debug("GSA mode={}".format(mode))
        except Exception as e:
            log.error("GSA parse error: " + str(e))

    def _parse_gsv(self, p):
        try:
            if len(p) >= 4 and p[3]:
                prev = self._fix.sats_in_view
                self._fix.sats_in_view = int(p[3])
                if self._fix.sats_in_view != prev:
                    log.info("Satellites in view: {}".format(self._fix.sats_in_view))
        except Exception as e:
            log.error("GSV parse error: " + str(e))

    def _parse_vtg(self, p):
        # VTG: true heading and speed - more reliable than RMC
        try:
            if len(p) < 8:
                return
            # p[1]=true track, p[5]=speed knots, p[7]=speed km/h
            if p[1]:
                self._fix.heading = float(p[1])
            if p[7]:
                self._fix.speed_kmh = float(p[7])
            log.debug("VTG heading={} speed={}km/h".format(p[1], p[7]))
        except Exception as e:
            log.error("VTG parse error: " + str(e))

    def _parse_zda(self, p):
        # ZDA: UTC date and time
        try:
            if len(p) >= 5 and p[1] and p[2] and p[3] and p[4]:
                self._fix.utc_date = "{}-{}-{}".format(p[4], p[3], p[2])
                log.debug("ZDA date={}".format(self._fix.utc_date))
        except Exception as e:
            log.error("ZDA parse error: " + str(e))

    @staticmethod
    def _nmea_coord(value, direction):
        if not value:
            return 0.0
        dot = value.index(".")
        deg  = float(value[:dot - 2])
        mins = float(value[dot - 2:]) / 60.0
        result = deg + mins
        if direction in ("S", "W"):
            result = -result
        return result

    @staticmethod
    def _validate_checksum(sentence):
        try:
            if "*" not in sentence:
                return True
            body, chk = sentence[1:].rsplit("*", 1)
            calc = 0
            for ch in body:
                calc ^= ord(ch)
            return calc == int(chk[:2], 16)
        except Exception:
            return False
