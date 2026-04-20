"""
Button Handler
3 physical buttons with debounce + short/long press detection.

Button map (configurable in config.json):
  BTN_A  short -> DISPLAY_TOGGLE     long -> SETUP
  BTN_B  short -> TRACK_TOGGLE       long -> LOCATION_TOGGLE
  BTN_C  short -> SOFT_RESET         long -> HARD_RESET
"""

import machine
import time
from logger import Logger

log = Logger("Buttons")


class _Button:
    def __init__(self, pin_num, debounce_ms, long_ms):
        self._pin        = machine.Pin(pin_num, machine.Pin.IN, machine.Pin.PULL_UP)
        self._debounce   = debounce_ms
        self._long_ms    = long_ms
        self._pressed_at = None
        self._last_state = 1

    def poll(self):
        state = self._pin.value()
        now   = time.ticks_ms()
        if state == 0 and self._last_state == 1:
            self._pressed_at = now
        elif state == 1 and self._last_state == 0:
            if self._pressed_at is not None:
                held = time.ticks_diff(now, self._pressed_at)
                self._pressed_at = None
                if held >= self._debounce:
                    self._last_state = state
                    return "long" if held >= self._long_ms else "short"
        self._last_state = state
        return None


class ButtonHandler:
    def __init__(self, config):
        d = config.get("btn_debounce_ms", 50)
        l = config.get("btn_long_ms", 1000)
        self._a = _Button(config.get("btn_a_pin", 10), d, l)
        self._b = _Button(config.get("btn_b_pin", 11), d, l)
        self._c = _Button(config.get("btn_c_pin", 12), d, l)
        self._map = {
            "a": ("DISPLAY_TOGGLE",  "SETUP"),
            "b": ("TRACK_TOGGLE",    "LOCATION_TOGGLE"),
            "c": ("SOFT_RESET",      "HARD_RESET"),
        }
        log.info("Buttons init: A=GP{} B=GP{} C=GP{}".format(
            config.get("btn_a_pin", 10),
            config.get("btn_b_pin", 11),
            config.get("btn_c_pin", 12),
        ))

    def poll(self):
        for btn_key, btn_obj in [("a", self._a), ("b", self._b), ("c", self._c)]:
            result = btn_obj.poll()
            if result:
                short_evt, long_evt = self._map[btn_key]
                evt = short_evt if result == "short" else long_evt
                log.debug("Button {} {} -> {}".format(btn_key.upper(), result, evt))
                return evt
        return None
