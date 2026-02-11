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
        print("   💡 Trên host/agent: kết nối ESP32 qua USB; kiểm tra ls /dev/ttyUSB* /dev/ttyACM*", file=sys.stderr)
        print("   💡 Jenkins: ATS node (agent) phải có ESP32 cắm USB. Nếu agent chạy trong Docker, host cần --device /dev/ttyUSB0 (hoặc SERIAL_PORT) khi start agent.", file=sys.stderr)
        return False
    
    if not os.path.exists(firmware_path):
        print(f"❌ Firmware not found: {firmware_path}", file=sys.stderr)
        return False

    # Pre-check: port exists but may return I/O error (CP2102 -32). Hint unplug/replug.
    try:
        import serial
        with serial.Serial(port, 115200, timeout=0.5) as _:
            pass
    except Exception as e:
        err_str = str(e)
        if "Errno 5" in err_str or "Input/output error" in err_str or "could not open" in err_str:
            print("   ⚠️  Port tồn tại nhưng mở bị lỗi (device CP2102 có thể đang lỗi trạng thái).", file=sys.stderr)
            print("   💡 Rút USB ESP32, đợi 10s, cắm lại rồi chạy test lại.", file=sys.stderr)
        # Continue to try esptool anyway
    except ImportError:
        pass

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
            print("   💡 Trên host chạy: ./usb-reset-stuck.sh 1-1.4 hoặc unbind/bind cp210x", file=sys.stderr)
            print("   💡 Jenkins: đảm bảo ATS agent có ESP32 cắm USB; nếu agent là container thì host phải truyền --device /dev/ttyUSB0 (hoặc port tương ứng) khi chạy agent.", file=sys.stderr)
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
