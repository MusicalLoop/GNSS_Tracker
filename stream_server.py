"""
Stream Server
Listens on a TCP port and streams NMEA sentences or JSON fix data
to any connected client (e.g. a PC running OpenCPN or a custom logger).

Only one client connection is handled at a time (Pico RAM constraint).
Requires WiFi to be connected before calling start().
"""

import socket
import json
import time


class StreamServer:
    def __init__(self, config):
        self._cfg    = config
        self._sock   = None   # listening socket
        self._client = None   # connected client socket
        self._fmt    = config.get("stream_format", "nmea")

    # -- Lifecycle ----------------------------------------------------------

    def start(self):
        """Open listening socket. WiFi must be up before calling this."""
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind((
                self._cfg.get("stream_host", "0.0.0.0"),
                self._cfg.get("stream_port", 10110),
            ))
            self._sock.listen(1)
            self._sock.setblocking(False)
            print("[Stream] Listening on port", self._cfg.get("stream_port"))
        except Exception as e:
            print("[Stream] Start error:", e)
            self._sock = None

    def stop(self):
        self._disconnect_client()
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    # -- Main send loop -----------------------------------------------------

    def send(self, fix):
        """
        Accept new connections and send fix data to current client.
        Call from main loop; non-blocking.
        """
        if not self._sock:
            return

        # Accept a waiting connection
        if not self._client:
            try:
                conn, addr = self._sock.accept()
                conn.setblocking(False)
                self._client = conn
                print("[Stream] Client connected:", addr)
            except OSError:
                pass   # no pending connection

        if not self._client:
            return

        # Build payload
        if self._fmt == "json":
            payload = self._to_json(fix) + "\r\n"
        else:
            payload = self._to_nmea(fix)

        try:
            self._client.send(payload.encode("ascii"))
        except OSError:
            print("[Stream] Client disconnected")
            self._disconnect_client()

    # -- Formatters ---------------------------------------------------------

    @staticmethod
    def _to_json(fix):
        data = {
            "utc":       fix.utc_time,
            "fix":       fix.fix_label(),
            "fix_type":  fix.fix_type,
            "sats_used": fix.sats_used,
            "sats_view": fix.sats_in_view,
            "lat":       fix.lat,
            "lon":       fix.lon,
            "alt_m":     fix.alt_m,
            "speed_kmh": fix.speed_kmh,
            "heading":   fix.heading,
            "cardinal":  fix.cardinal(),
        }
        return json.dumps(data)

    @staticmethod
    def _to_nmea(fix):
        """
        Emit a minimal $GPGGA sentence reconstructed from parsed data.
        A real implementation would pass raw sentences through unchanged;
        this is a fallback when raw buffering isn't in place.
        """
        def decdeg_to_nmea(val, is_lat):
            hem = ("N" if val >= 0 else "S") if is_lat else ("E" if val >= 0 else "W")
            val = abs(val)
            deg = int(val)
            mins = (val - deg) * 60
            fmt = "{:02d}{:07.4f}" if is_lat else "{:03d}{:07.4f}"
            return fmt.format(deg, mins), hem

        lat_s, lat_h = decdeg_to_nmea(fix.lat, True)
        lon_s, lon_h = decdeg_to_nmea(fix.lon, False)
        quality = fix.fix_type if fix.is_valid else 0
        body = "GPGGA,{},{},{},{},{},{},{:02d},,,{:.1f},M,,M,,".format(
            fix.utc_time, lat_s, lat_h, lon_s, lon_h,
            quality, fix.sats_used, fix.alt_m,
        )
        chk = 0
        for ch in body:
            chk ^= ord(ch)
        return "${body}*{chk:02X}\r\n".format(body=body, chk=chk)

    # -- Internal -----------------------------------------------------------

    def _disconnect_client(self):
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
