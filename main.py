"""
GNSS Tracker - Main Entry Point
Hardware: Raspberry Pi Pico 2W + Waveshare Pico-GPS-L76K + 0.96" OLED
"""

import time
import machine
from config_manager import ConfigManager
from logger import Logger, set_level
from gnss import GNSSModule
from display_manager import DisplayManager
from button_handler import ButtonHandler
from track_logger import TrackLogger
from stream_server import StreamServer
from state import AppState

# Init config first (creates config.json on first boot)
config = ConfigManager()

# Apply log level from config before anything else starts
set_level(config.get("debug_level", 3))

log = Logger("Main")
log.info("GNSS Tracker starting")

# Init hardware
state    = AppState()
gnss     = GNSSModule(config)
display  = DisplayManager(config)
buttons  = ButtonHandler(config)
logger   = TrackLogger(config)
streamer = StreamServer(config)


def main():
    display.show_splash()
    time.sleep(1)

    gnss.start()

    if config.get("stream_enabled"):
        streamer.start()

    log.info("Main loop running")

    while True:
        fix = gnss.update()

        event = buttons.poll()

        if event:
            log.debug("Button event: " + event)

        if event == "DISPLAY_TOGGLE":
            state.display_on = not state.display_on
            log.info("Display: {}".format("ON" if state.display_on else "OFF"))
            if not state.display_on:
                display.off()
            else:
                display.on()

        elif event == "TRACK_TOGGLE":
            if not state.tracking:
                logger.start_track()
                state.tracking = True
                log.info("Track recording started")
            else:
                logger.stop_track()
                state.tracking = False
                log.info("Track recording stopped")

        elif event == "LOCATION_TOGGLE":
            state.location_active = not state.location_active
            log.info("Location active: {}".format(state.location_active))

        elif event == "SOFT_RESET":
            log.warn("Soft reset requested")
            do_soft_reset()

        elif event == "HARD_RESET":
            log.warn("Hard reset requested")
            do_hard_reset()

        elif event == "SETUP":
            hold_ms = config.get("config_display_s", 15) * 1000
            state.config_until_ms = time.ticks_add(time.ticks_ms(), hold_ms)
            log.info("Showing config menu for {}s".format(config.get("config_display_s", 15)))
            display.show_config_menu(config)

        if state.tracking and fix and fix.is_valid:
            logger.log(fix)
            state.track_points = logger.count

        if config.get("stream_enabled") and fix:
            streamer.send(fix)

        if state.display_on:
            if state.config_until_ms and time.ticks_diff(state.config_until_ms, time.ticks_ms()) > 0:
                # Config screen is active - redraw it to keep it visible
                display.show_config_menu(config)
            else:
                if state.config_until_ms:
                    log.info("Config menu dismissed")
                    state.config_until_ms = 0
                display.update(fix, state)

        time.sleep(0.2)


def do_soft_reset():
    gnss.stop()
    logger.close()
    streamer.stop()
    time.sleep(0.5)
    gnss.start()
    if config.get("stream_enabled"):
        streamer.start()
    log.info("Soft reset complete")


def do_hard_reset():
    log.warn("Hard reset - rebooting now")
    time.sleep(0.2)
    machine.reset()


main()
