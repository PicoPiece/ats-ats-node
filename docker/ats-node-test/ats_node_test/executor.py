"""Main test execution orchestrator."""
import argparse
import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime

from .manifest import load_manifest, get_artifact_name, get_device_target, get_test_plan
from .hardware import detect_esp32_port, check_gpio_access
from .flash_esp32 import flash_firmware, reset_esp32
from .results import write_summary, write_junit, write_meta

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


def test_uart_read_directly(port: str, timeout: int = 5) -> Tuple[bool, str]:
    """Test UART read directly to debug boot messages."""
    try:
        import serial
        import time
        
        print(f"🔍 [DEBUG] Testing direct UART read from {port}...")
        # #region agent log
        debug_log("executor.py:test_uart_read", "Before direct UART read", {
            "port": port,
            "timeout": timeout
        }, "F")
        # #endregion
        
        ser = serial.Serial(port, 115200, timeout=timeout)
        time.sleep(0.1)  # Small delay for port to stabilize
        
        # Flush buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Read for specified timeout
        start_time = time.time()
        data = b""
        while time.time() - start_time < timeout:
            if ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting)
                data += chunk
                # #region agent log
                debug_log("executor.py:test_uart_read", "UART data chunk received", {
                    "chunk_length": len(chunk),
                    "total_length": len(data),
                    "chunk_preview": chunk[:100].decode('utf-8', errors='ignore')
                }, "F")
                # #endregion
            time.sleep(0.1)
        
        ser.close()
        
        data_str = data.decode('utf-8', errors='ignore')
        success = len(data) > 0
        
        print(f"🔍 [DEBUG] UART read result: {len(data)} bytes")
        if data_str:
            print(f"🔍 [DEBUG] First 200 chars: {data_str[:200]}")
            # Check for common ESP32 boot patterns
            patterns = ['rst:', 'ets Jun', 'ESP-IDF', 'Guru Meditation', 'boot:', 'I (', 'E (', 'W (']
            found_patterns = [p for p in patterns if p in data_str]
            if found_patterns:
                print(f"✅ [DEBUG] Found boot patterns: {', '.join(found_patterns)}")
            else:
                print(f"⚠️  [DEBUG] No common boot patterns found")
        
        # #region agent log
        debug_log("executor.py:test_uart_read", "After direct UART read", {
            "success": success,
            "data_length": len(data),
            "data_preview": data_str[:500],
            "found_patterns": found_patterns if data_str else []
        }, "F")
        # #endregion
        
        return success, data_str
    except ImportError:
        print("⚠️  [DEBUG] pyserial not available for direct UART test")
        return False, ""
    except Exception as e:
        print(f"❌ [DEBUG] Direct UART read failed: {e}")
        # #region agent log
        debug_log("executor.py:test_uart_read", "Direct UART read exception", {
            "error": str(e),
            "error_type": type(e).__name__
        }, "F")
        # #endregion
        return False, str(e)


def run_test_runner(workspace: str, manifest: Dict[str, Any], results_dir: str) -> List[Dict[str, Any]]:
    """Invoke test runner (ats-test-esp32-demo) and collect results."""
    # Test runner is expected to be in workspace
    # It should read manifest and output results
    test_runner_path = Path(workspace) / "ats-test-esp32-demo" / "agent" / "run_tests.sh"
    
    tests = []
    
    # CRITICAL: Test UART read directly BEFORE test runner to verify ESP32 is actually booting
    port = os.environ.get('SERIAL_PORT', '/dev/ttyUSB0')
    if os.path.exists(port):
        print("\n🔍 [DEBUG] Pre-flight UART check before test runner...")
        uart_success, uart_data = test_uart_read_directly(port, timeout=3)
        if uart_success:
            print(f"✅ [DEBUG] UART is readable, got {len(uart_data)} bytes")
        else:
            print(f"⚠️  [DEBUG] UART read returned no data - ESP32 may not be booting")
    
    if test_runner_path.exists():
        import subprocess
        print(f"🧪 Running test runner: {test_runner_path}")
        
        # Test runner should output to results_dir
        # Pass manifest path as argument
        manifest_path = Path(workspace) / "ats-manifest.yaml"
        env = os.environ.copy()
        env['TEST_REPORT_DIR'] = results_dir
        env['RESULTS_DIR'] = results_dir
        env['WORKSPACE'] = workspace
        env['SERIAL_PORT'] = port
        
        # #region agent log
        debug_log("executor.py:run_test_runner", "Before subprocess.run", {
            "test_runner_path": str(test_runner_path),
            "manifest_path": str(manifest_path),
            "port": port,
            "uart_precheck_success": uart_success if 'uart_success' in locals() else None
        }, "D")
        # #endregion
        
        try:
            result = subprocess.run(
                [str(test_runner_path), str(manifest_path)],
                cwd=Path(workspace) / "ats-test-esp32-demo",
                env=env,
                capture_output=True,
                text=True
            )
            
            # #region agent log
            debug_log("executor.py:run_test_runner", "After subprocess.run", {
                "returncode": result.returncode,
                "stdout_length": len(result.stdout),
                "stderr_length": len(result.stderr),
                "stdout_preview": result.stdout[:500] if result.stdout else None,
                "stderr_preview": result.stderr[:500] if result.stderr else None
            }, "D")
            # #endregion
            
            # Print test runner output
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            
            # Parse test results from test runner output
            # For now, create basic test entries
            tests.append({
                'name': 'test_execution',
                'status': 'PASS' if result.returncode == 0 else 'FAIL',
                'failure': result.stderr if result.returncode != 0 else ''
            })
        except Exception as e:
            # #region agent log
            debug_log("executor.py:run_test_runner", "Subprocess exception", {
                "error": str(e),
                "error_type": type(e).__name__
            }, "D")
            # #endregion
            tests.append({
                'name': 'test_execution',
                'status': 'FAIL',
                'failure': str(e)
            })
    else:
        print(f"⚠️  Test runner not found: {test_runner_path}")
        print("   Creating placeholder test result")
        tests.append({
            'name': 'test_execution',
            'status': 'SKIP',
            'failure': 'Test runner not found'
        })
    
    return tests


def main():
    parser = argparse.ArgumentParser(description='ATS Node Test Executor')
    parser.add_argument('--manifest', required=True, help='Path to ats-manifest.yaml')
    parser.add_argument('--results-dir', required=True, help='Results output directory')
    parser.add_argument('--workspace', required=True, help='Workspace directory')
    
    args = parser.parse_args()
    
    print("🚀 [ATS Node Executor] Starting")
    
    # Load manifest
    try:
        manifest = load_manifest(args.manifest)
        print(f"✅ Manifest loaded: {manifest['build']['build_number']}")
    except Exception as e:
        print(f"❌ Failed to load manifest: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get artifact and device info
    artifact_name = get_artifact_name(manifest)
    device_target = get_device_target(manifest)
    test_plan = get_test_plan(manifest)
    
    artifact_path = Path(args.workspace) / artifact_name
    
    print(f"📦 Artifact: {artifact_name}")
    print(f"🎯 Device: {device_target}")
    print(f"📋 Test plan: {', '.join(test_plan)}")
    
    # Create results directory
    os.makedirs(args.results_dir, exist_ok=True)
    
    exit_code = 0
    flash_start_time = None
    
    # Step 1: Flash firmware
    if device_target == 'esp32':
        print("\n🔌 Flashing firmware...")
        # #region agent log
        debug_log("executor.py:112", "Before flash_firmware", {
            "artifact_path": str(artifact_path),
            "port": detect_esp32_port()
        }, "A")
        # #endregion
        flash_start_time = time.time()
        if not flash_firmware(str(artifact_path)):
            print("❌ Flash failed", file=sys.stderr)
            exit_code = 1
        else:
            flash_end_time = time.time()
            flash_duration = flash_end_time - flash_start_time
            print("✅ Flash successful")
            # #region agent log
            debug_log("executor.py:116", "After flash_firmware", {
                "flash_duration_seconds": flash_duration,
                "flash_success": True
            }, "A")
            # #endregion
            
            # CRITICAL: ESP32 needs time to boot after reset
            # esptool does --after hard_reset, but we need to wait for boot
            print("\n⏳ Waiting for ESP32 to boot after reset...")
            boot_wait_start = time.time()
            # #region agent log
            debug_log("executor.py:123", "Before boot wait", {
                "wait_start_time": boot_wait_start
            }, "A")
            # #endregion
            
            # Wait for ESP32 boot (typically 1-3 seconds)
            # Also ensures serial port is released by esptool
            time.sleep(3.0)  # 3 second boot delay
            
            boot_wait_end = time.time()
            boot_wait_duration = boot_wait_end - boot_wait_start
            print(f"✅ Boot wait complete ({boot_wait_duration:.2f}s)")
            # #region agent log
            debug_log("executor.py:132", "After boot wait", {
                "wait_duration_seconds": boot_wait_duration,
                "wait_complete": True
            }, "A")
            # #endregion
            
            # Optional: Explicit reset to ensure clean boot state
            port = detect_esp32_port()
            if port:
                print(f"🔄 Performing explicit reset on {port}...")
                # #region agent log
                debug_log("executor.py:139", "Before explicit reset", {
                    "port": port
                }, "E")
                # #endregion
                reset_start = time.time()
                reset_success = reset_esp32(port)
                reset_end = time.time()
                reset_duration = reset_end - reset_start
                # #region agent log
                debug_log("executor.py:145", "After explicit reset", {
                    "reset_success": reset_success,
                    "reset_duration_seconds": reset_duration
                }, "E")
                # #endregion
                if reset_success:
                    print("✅ Reset successful")
                    # Wait again after explicit reset
                    # CRITICAL: ESP32 boot messages appear within first 1-2 seconds after reset
                    # We need to wait just enough for boot to start, but not too long to miss messages
                    print("⏳ Waiting for ESP32 to boot after explicit reset...")
                    # #region agent log
                    debug_log("executor.py:203", "Before second boot wait", {
                        "wait_seconds": 2.0,
                        "note": "Boot messages appear in first 1-2s after reset"
                    }, "A")
                    # #endregion
                    time.sleep(2.0)  # Additional 2 second wait
                    # #region agent log
                    debug_log("executor.py:210", "After second boot wait", {
                        "second_wait_seconds": 2.0,
                        "total_wait_since_flash": time.time() - flash_start_time
                    }, "A")
                    # #endregion
                    
                    # Flush serial buffer to ensure clean read
                    # This ensures we don't read stale data from previous operations
                    print("🔄 Flushing serial buffer...")
                    try:
                        import serial
                        # Open serial port with common ESP32 baud rates
                        # Try 115200 first (most common), then 9600
                        for baud in [115200, 9600]:
                            try:
                                ser = serial.Serial(port, baud, timeout=0.5)
                                ser.reset_input_buffer()  # Flush input buffer
                                ser.reset_output_buffer()  # Flush output buffer
                                ser.close()
                                print(f"✅ Serial buffer flushed at {baud} baud")
                                # #region agent log
                                debug_log("executor.py:223", "Serial buffer flushed", {
                                    "port": port,
                                    "baud": baud
                                }, "B")
                                # #endregion
                                break
                            except (serial.SerialException, OSError):
                                continue
                    except ImportError:
                        print("⚠️  pyserial not available, skipping buffer flush")
                        # #region agent log
                        debug_log("executor.py:235", "Serial flush skipped - pyserial not available", {}, "B")
                        # #endregion
                    except Exception as e:
                        print(f"⚠️  Could not flush serial buffer: {e}")
                        # #region agent log
                        debug_log("executor.py:240", "Serial flush failed", {
                            "error": str(e)
                        }, "B")
                        # #endregion
                else:
                    print("⚠️  Reset failed, continuing anyway")
    else:
        print(f"⚠️  Unknown device target: {device_target}")
        exit_code = 1
    
    # Step 2: Run tests
    if exit_code == 0:
        # CRITICAL TIMING: ESP32 boot messages appear within first 1-3 seconds after reset
        # Test runner must start reading UART IMMEDIATELY after boot wait
        # If we wait too long, boot messages will be missed
        if device_target == 'esp32' and flash_start_time:
            time_since_flash = time.time() - flash_start_time
            print(f"\n⏱️  Time since flash: {time_since_flash:.2f}s")
            # #region agent log
            debug_log("executor.py:240", "Before run_test_runner - timing check", {
                "workspace": args.workspace,
                "time_since_flash": time_since_flash,
                "note": "Boot messages window: 0-3s after reset"
            }, "D")
            # #endregion
            
            # If too much time has passed, boot messages may have been missed
            # In this case, we should do another reset to trigger fresh boot messages
            if time_since_flash > 8.0:  # More than 8 seconds since flash
                print("⚠️  Too much time has passed since flash, performing fresh reset for boot messages...")
                port = detect_esp32_port()
                if port:
                    reset_esp32(port)
                    time.sleep(1.0)  # Short wait for boot to start
                    print("✅ Fresh reset complete, test runner should catch boot messages now")
                    # #region agent log
                    debug_log("executor.py:253", "Fresh reset for boot messages", {
                        "time_since_flash_before_reset": time_since_flash,
                        "reset_reason": "Too much time passed, boot messages may be missed"
                    }, "D")
                    # #endregion
        
        print("\n🧪 Running tests...")
        # #region agent log
        debug_log("executor.py:260", "Before run_test_runner", {
            "workspace": args.workspace,
            "time_since_flash": time.time() - flash_start_time if device_target == 'esp32' and flash_start_time else None
        }, "D")
        # #endregion
        test_runner_start = time.time()
        tests = run_test_runner(args.workspace, manifest, args.results_dir)
        test_runner_end = time.time()
        # #region agent log
        debug_log("executor.py:267", "After run_test_runner", {
            "test_runner_duration_seconds": test_runner_end - test_runner_start,
            "test_count": len(tests),
            "test_statuses": [t.get('status') for t in tests],
            "time_since_flash_when_test_started": test_runner_start - flash_start_time if device_target == 'esp32' and flash_start_time else None
        }, "D")
        # #endregion
        
        # Check if any test failed
        if any(t.get('status') == 'FAIL' for t in tests):
            exit_code = 1
    else:
        tests = [{'name': 'test_execution', 'status': 'SKIP', 'failure': 'Flash failed'}]
    
    # Step 3: Write results
    print("\n📊 Writing results...")
    write_summary(args.results_dir, {
        'status': 'PASS' if exit_code == 0 else 'FAIL',
        'tests': tests,
        'manifest': {
            'build_number': manifest['build']['build_number'],
            'device_target': device_target
        }
    })
    write_junit(args.results_dir, tests)
    write_meta(args.results_dir, manifest, exit_code)
    
    print(f"\n✅ Execution complete (exit code: {exit_code})")
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
