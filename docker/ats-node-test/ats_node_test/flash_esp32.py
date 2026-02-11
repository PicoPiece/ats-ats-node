"""ESP32 firmware flashing."""
import os
import subprocess
import sys
import json
import time
from typing import Optional
from datetime import datetime
from .hardware import detect_esp32_port, try_reset_serial_port

# Debug logging
DEBUG_LOG_PATH = "/home/thait/.cursor/debug.log"

def debug_log(location: str, message: str, data: dict = None, hypothesis_id: str = None):
    """Write debug log entry."""
    try:
        log_entry = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(datetime.now().timestamp() * 1000)
        }
        with open(DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass  # Silently fail if logging doesn't work


def flash_firmware(firmware_path: str, port: Optional[str] = None) -> bool:
    """Flash ESP32 firmware."""
    if not port:
        port = detect_esp32_port()
    
    if not port:
        print("❌ ESP32 port not found", file=sys.stderr)
        print("   Ensure agent has ESP32 connected (ls /dev/ttyUSB* /dev/ttyACM*). Jenkins: pass --device or SERIAL_PORT if agent runs in Docker.", file=sys.stderr)
        return False

    if not os.path.exists(firmware_path):
        print(f"❌ Firmware not found: {firmware_path}", file=sys.stderr)
        return False

    print(f"📡 Flashing firmware to {port}...")
    
    cmd = [
        'esptool.py',
        '--chip', 'auto',
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
    
    max_attempts = 3
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            if attempt > 1:
                print(f"   Retry {attempt}/{max_attempts}...")
            flash_start = time.time()
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            flash_end = time.time()
            print("✅ Firmware flashed successfully")
            return True
        except subprocess.CalledProcessError as e:
            last_error = e
            stderr = (e.stderr or "")
            is_port_error = (
                "could not open" in stderr or "Errno 5" in stderr
                or "Input/output error" in stderr or "port is busy" in stderr
            )
            if is_port_error and attempt == 1:
                if try_reset_serial_port(port):
                    print("   🔄 Reset serial port (unbind/bind) done, retrying...", file=sys.stderr)
                    time.sleep(2)
                    continue
            if attempt < max_attempts and is_port_error:
                time.sleep(2)
                continue
            break
    
    if last_error:
        print(f"❌ Flash failed: {last_error.stderr}", file=sys.stderr)
        stderr = last_error.stderr or ""
        if "Errno 5" in stderr or "Input/output error" in stderr or "port is busy" in stderr:
            print("   Serial port I/O error. Check agent USB/udev and docs (e.g. ESP32-USB-STABILITY-FIX.md).", file=sys.stderr)
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
