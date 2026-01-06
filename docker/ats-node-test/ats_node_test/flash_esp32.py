"""ESP32 firmware flashing."""
import os
import subprocess
import sys
from typing import Optional
from .hardware import detect_esp32_port


def flash_firmware(firmware_path: str, port: Optional[str] = None) -> bool:
    """Flash ESP32 firmware."""
    if not port:
        port = detect_esp32_port()
    
    if not port:
        print("❌ ESP32 port not found", file=sys.stderr)
        return False
    
    if not os.path.exists(firmware_path):
        print(f"❌ Firmware not found: {firmware_path}", file=sys.stderr)
        return False
    
    print(f"📡 Flashing firmware to {port}...")
    
    # Auto-detect chip type - esptool will detect the connected chip
    # Flash at 0x10000 (app partition)
    # If chip type doesn't match firmware, esptool will fail (this is correct behavior)
    cmd = [
        'esptool.py',
        '--chip', 'auto',  # Auto-detect chip type (ESP32, ESP32-S2, ESP32-S3, etc.)
        '--port', port,
        '--baud', '460800',
        '--before', 'default_reset',
        '--after', 'hard_reset',
        'write_flash',
        '--flash_mode', 'dio',
        '--flash_freq', '40m',
        '--flash_size', 'detect',
        '0x10000', firmware_path
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Firmware flashed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Flash failed: {e.stderr}", file=sys.stderr)
        return False


def reset_esp32(port: Optional[str] = None) -> bool:
    """Reset ESP32."""
    if not port:
        port = detect_esp32_port()
    
    if not port:
        return False
    
    try:
        subprocess.run(['esptool.py', '--chip', 'auto', '--port', port, 'run'], 
                      check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False
