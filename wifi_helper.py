"""
WiFi Helper (Pico 2W)
Connect to WiFi; required before StreamServer.start().
Call connect() during boot if stream_enabled is True.
"""

import network
import time


def connect(ssid, password, timeout_s=20):
    """
    Connect to WiFi. Returns (True, ip) on success, (False, "") on failure.
    Add your credentials to config.json:
        "wifi_ssid": "MyNetwork",
        "wifi_password": "secret"
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return True, wlan.ifconfig()[0]

    print("[WiFi] Connecting to", ssid)
    wlan.connect(ssid, password)

    deadline = time.time() + timeout_s
    while not wlan.isconnected():
        if time.time() > deadline:
            print("[WiFi] Timeout")
            return False, ""
        time.sleep(0.5)

    ip = wlan.ifconfig()[0]
    print("[WiFi] Connected, IP:", ip)
    return True, ip


def ip():
    wlan = network.WLAN(network.STA_IF)
    return wlan.ifconfig()[0] if wlan.isconnected() else "0.0.0.0"
