"""
App State
Simple container for runtime state shared across modules.
Not persisted - reset on every boot.
"""


class AppState:
    def __init__(self):
        self.display_on      = True
        self.tracking        = False
        self.location_active = True
        self.track_points    = 0    # updated by main loop from logger.count
        self.page            = 0
        self.config_until_ms = 0    # ticks_ms() deadline for config screen, 0=not showing
