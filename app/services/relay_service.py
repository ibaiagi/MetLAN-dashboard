"""
Controls the dongle's V+ power line through the relay/MOSFET on the Pi 4's
GPIO header (context.md section 2: "Real hardware V+ disconnect, not
software-only" - this only ever switches the dongle's power line, never
the Pi 4's own supply).

No relay has been wired up yet (context.md section 7/11), so this module
is written to fail soft: if gpiozero can't claim the configured pin (no
hardware attached, wrong permissions, running off-Pi, etc.) the service
reports itself as unavailable instead of crashing the whole API.
"""
import time
from collections import deque
from threading import Lock

from app.config import RELAY_ACTIVE_HIGH, RELAY_GPIO_PIN, ACTION_LOG_MAX_ENTRIES

_lock = Lock()
_action_log = deque(maxlen=ACTION_LOG_MAX_ENTRIES)
_relay = None
_init_error = None


def _get_relay():
    """Lazily create the gpiozero OutputDevice, remembering any failure."""
    global _relay, _init_error
    if _relay is not None or _init_error is not None:
        return _relay
    try:
        from gpiozero import OutputDevice

        _relay = OutputDevice(
            RELAY_GPIO_PIN,
            active_high=RELAY_ACTIVE_HIGH,
            initial_value=False,  # boot with the dongle OFF - safe default
        )
    except Exception as exc:  # noqa: BLE001 - deliberately broad, hardware can fail many ways
        _init_error = str(exc)
    return _relay


def is_available() -> bool:
    return _get_relay() is not None


def unavailable_reason() -> str | None:
    _get_relay()
    return _init_error


def _log(action: str, source: str = "api"):
    _action_log.appendleft(
        {"timestamp": time.time(), "action": action, "source": source}
    )


def get_state() -> dict:
    relay = _get_relay()
    if relay is None:
        return {
            "available": False,
            "reason": _init_error,
            "state": "unknown",
            "gpio_pin": RELAY_GPIO_PIN,
        }
    return {
        "available": True,
        "state": "on" if relay.value else "off",
        "gpio_pin": RELAY_GPIO_PIN,
    }


def set_state(turn_on: bool) -> dict:
    with _lock:
        relay = _get_relay()
        if relay is None:
            return get_state()
        if turn_on:
            relay.on()
            _log("dongle power ON")
        else:
            relay.off()
            _log("dongle power OFF")
        return get_state()


def get_log() -> list:
    return list(_action_log)
