"""Hardware detection and access utilities."""
import os
import glob
import time
from typing import Optional, List

# Sysfs path for cp210x driver (unbind/bind to fix EIO)
CP210X_DRIVER = "/sys/bus/usb/drivers/cp210x"


def _get_usb_bus_path_for_tty(port: str) -> Optional[str]:
    """Get USB device bus path (e.g. 1-1.2) for a tty so we can unbind/bind the device."""
    if not port or not os.path.exists(port):
        return None
    base = os.path.basename(port)  # ttyUSB0
    device_link = os.path.join("/sys/class/tty", base, "device")
    if not os.path.exists(device_link):
        return None
    try:
        real = os.path.realpath(device_link)
        # real is .../1-1.2:1.0/ttyUSB0 or .../1-1.2:1.0; interface is 1-1.2:1.0, device is 1-1.2
        parent = os.path.dirname(real)       # .../1-1.2:1.0
        device_dir = os.path.dirname(parent) # .../1-1.2
        return os.path.basename(device_dir)
    except Exception:
        return None


def try_reset_serial_port(port: str) -> bool:
    """
    Unbind and bind the USB serial driver for the given port (e.g. /dev/ttyUSB0).
    Can fix [Errno 5] Input/output error when the device is stuck.
    Requires root. Returns True if unbind+bind was performed.
    """
    bus_path = _get_usb_bus_path_for_tty(port)
    if not bus_path or ":" in bus_path:
        return False
    unbind = os.path.join(CP210X_DRIVER, "unbind")
    bind = os.path.join(CP210X_DRIVER, "bind")
    if not os.path.exists(unbind) or not os.path.exists(bind):
        return False
    try:
        with open(unbind, "w") as f:
            f.write(bus_path)
        time.sleep(2)
        with open(bind, "w") as f:
            f.write(bus_path)
        time.sleep(2)
        return True
    except (OSError, PermissionError):
        return False


def detect_esp32_port() -> Optional[str]:
    """Detect ESP32 USB serial port. Set SERIAL_PORT to force a specific port."""
    env_port = os.environ.get("SERIAL_PORT", "").strip()
    if env_port and os.path.exists(env_port):
        return env_port
    # Common ESP32 USB serial ports
    ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']
    for port in ports:
        if os.path.exists(port):
            return port
    # Try to find any USB serial device
    usb_ports = sorted(glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*'))
    if usb_ports:
        return usb_ports[0]
    return None


def check_gpio_access() -> bool:
    """Check if GPIO access is available."""
    return os.path.exists('/sys/class/gpio') or os.path.exists('/dev/gpiomem')
