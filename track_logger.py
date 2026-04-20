"""
Track Logger
Writes track points to /tracks/ on the Pico flash.
Supports CSV and minimal GPX format.
"""

import os
import time
from logger import Logger

log = Logger("Logger")


def _ensure_dir(path):
    try:
        os.mkdir(path)
    except OSError:
        pass


def _timestamp_filename():
    t = time.localtime()
    return "{:04d}{:02d}{:02d}_{:02d}{:02d}{:02d}".format(
        t[0], t[1], t[2], t[3], t[4], t[5])


class TrackLogger:
    def __init__(self, config):
        self._cfg      = config
        self._file     = None
        self._fmt      = config.get("track_format", "csv")
        self._interval = config.get("track_interval_s", 5)
        self._last_log = 0
        self._count    = 0
        _ensure_dir(config.get("track_dir", "/tracks"))
        log.info("Track logger ready, format={} interval={}s".format(
            self._fmt, self._interval))

    @property
    def count(self):
        return self._count

    def start_track(self):
        self.close()
        self._count = 0
        name = _timestamp_filename()
        path = "{}/{}.{}".format(self._cfg.get("track_dir", "/tracks"), name, self._fmt)
        try:
            self._file = open(path, "w")
            if self._fmt == "csv":
                self._file.write("utc,lat,lon,alt_m,speed_kmh,heading,sats\r\n")
            elif self._fmt == "gpx":
                self._file.write(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<gpx version="1.1" creator="PicoGNSS">\n'
                    '<trk><n>{}</n><trkseg>\n'.format(name))
            self._file.flush()
            log.info("Track file opened: " + path)
        except Exception as e:
            log.error("Failed to open track file: " + str(e))
            self._file = None

    def log(self, fix):
        if not self._file:
            return
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_log) < self._interval * 1000:
            return
        self._last_log = now
        self._count   += 1
        try:
            if self._fmt == "csv":
                self._file.write("{},{:.6f},{:.6f},{:.1f},{:.2f},{:.1f},{}\r\n".format(
                    fix.utc_time, fix.lat, fix.lon,
                    fix.alt_m, fix.speed_kmh, fix.heading, fix.sats_used))
            elif self._fmt == "gpx":
                self._file.write(
                    '<trkpt lat="{:.6f}" lon="{:.6f}">'
                    '<ele>{:.1f}</ele>'
                    '<time>{}</time>'
                    '</trkpt>\n'.format(fix.lat, fix.lon, fix.alt_m, fix.utc_time))
            self._file.flush()
            log.debug("Logged point #{}: lat={:.6f} lon={:.6f}".format(
                self._count, fix.lat, fix.lon))
        except Exception as e:
            log.error("Write error: " + str(e))

    def stop_track(self):
        self.close()

    def close(self):
        if self._file:
            try:
                if self._fmt == "gpx":
                    self._file.write("</trkseg></trk></gpx>\n")
                self._file.close()
                log.info("Track closed ({} points)".format(self._count))
            except Exception as e:
                log.error("Close error: " + str(e))
            self._file = None
