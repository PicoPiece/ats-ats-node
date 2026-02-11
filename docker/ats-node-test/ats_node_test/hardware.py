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


def check_gpio_access() -> bool:
    """Check if GPIO access is available."""
    return os.path.exists('/sys/class/gpio') or os.path.exists('/dev/gpiomem')
