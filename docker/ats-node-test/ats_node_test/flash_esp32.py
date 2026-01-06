"""ESP32 firmware flashing."""
import os
import subprocess
import sys
import json
import time
from typing import Optional
from datetime import datetime
from .hardware import detect_esp32_port

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
        # #region agent log
        debug_log("flash_esp32.py:42", "Before esptool subprocess", {
            "cmd": cmd,
            "port": port,
            "firmware_path": firmware_path
        }, "C")
        # #endregion
        flash_start = time.time()
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        flash_end = time.time()
        flash_duration = flash_end - flash_start
        # #region agent log
        debug_log("flash_esp32.py:50", "After esptool subprocess", {
            "flash_duration_seconds": flash_duration,
            "flash_success": True,
            "stdout_length": len(result.stdout),
            "stderr_length": len(result.stderr),
            "has_hard_reset": "--after hard_reset" in " ".join(cmd)
        }, "C")
        # #endregion
        print("✅ Firmware flashed successfully")
        # #region agent log
        debug_log("flash_esp32.py:59", "Flash complete, checking serial port release", {
            "port": port,
            "time_after_flash": time.time() - flash_end
        }, "C")
        # #endregion
        return True
    except subprocess.CalledProcessError as e:
        # #region agent log
        debug_log("flash_esp32.py:65", "Flash failed", {
            "error": str(e),
            "stderr": e.stderr[:200] if e.stderr else None,
            "returncode": e.returncode
        }, "C")
        # #endregion
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
