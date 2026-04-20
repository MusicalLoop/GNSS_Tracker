"""
Debug Logger
Configurable log levels for all modules.

Levels (set debug_level in config.json):
  0 = OFF   - no output at all
  1 = ERROR - only errors
  2 = WARN  - errors + warnings
  3 = INFO  - normal operational messages (default)
  4 = DEBUG - verbose, including raw NMEA sentences

Usage:
  from logger import Logger
  log = Logger("GNSS")
  log.debug("raw sentence: " + sentence)
  log.info("UART started")
  log.warn("checksum failed")
  log.error("UART init failed: " + str(e))
"""

import time

OFF   = 0
ERROR = 1
WARN  = 2
INFO  = 3
DEBUG = 4

LEVEL_NAMES = {OFF: "OFF", ERROR: "ERROR", WARN: "WARN", INFO: "INFO", DEBUG: "DEBUG"}

# Global level - set once from config, read by all Logger instances
_level = INFO


def set_level(level):
    global _level
    _level = level
    if _level > OFF:
        _print("Logger", INFO, "Log level set to {}".format(LEVEL_NAMES.get(level, str(level))))


def _print(tag, level, msg):
    t = time.localtime()
    ts = "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
    print("[{}] [{}] [{}] {}".format(ts, LEVEL_NAMES[level], tag, msg))


class Logger:
    def __init__(self, tag):
        self._tag = tag

    def error(self, msg):
        if _level >= ERROR:
            _print(self._tag, ERROR, msg)

    def warn(self, msg):
        if _level >= WARN:
            _print(self._tag, WARN, msg)

    def info(self, msg):
        if _level >= INFO:
            _print(self._tag, INFO, msg)

    def debug(self, msg):
        if _level >= DEBUG:
            _print(self._tag, DEBUG, msg)
