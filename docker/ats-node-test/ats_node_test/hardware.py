"""Hardware detection and access utilities."""
import os
import glob
from typing import Optional, List


def detect_esp32_port() -> Optional[str]:
    """Detect ESP32 USB serial port."""
    # Common ESP32 USB serial ports
    ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']
    
    for port in ports:
        if os.path.exists(port):
            return port
    
    # Try to find any USB serial device
    usb_ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    if usb_ports:
        return usb_ports[0]
    
    return None


def try_reset_serial_port(port: str) -> bool:
    """Try to reset USB serial port via unbind/bind (e.g. after port busy / Errno 5)."""
    if not port or not os.path.exists(port):
        return False
    basename = os.path.basename(port)  # e.g. ttyUSB0
    try:
        # /sys/class/tty/ttyUSB0/device -> realpath gives .../1-1/1-1:1.0
        tty_sys = os.path.join("/sys/class/tty", basename, "device")
        if not os.path.exists(tty_sys):
            return False
        device_path = os.path.realpath(tty_sys)
        interface_id = os.path.basename(device_path)  # e.g. 1-1:1.0
        driver_link = os.path.join(device_path, "driver")
        if not os.path.exists(driver_link):
            return False
        driver_path = os.path.realpath(driver_link)
        unbind_path = os.path.join(driver_path, "unbind")
        bind_path = os.path.join(driver_path, "bind")
        if not os.path.exists(unbind_path) or not os.path.exists(bind_path):
            return False
        with open(unbind_path, "w") as f:
            f.write(interface_id)
        import time
        time.sleep(1.0)
        with open(bind_path, "w") as f:
            f.write(interface_id)
        return True
    except (OSError, IOError):
        return False


def check_gpio_access() -> bool:
    """Check if GPIO access is available."""
    return os.path.exists('/sys/class/gpio') or os.path.exists('/dev/gpiomem')
