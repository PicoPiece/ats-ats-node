"""Main test execution orchestrator."""
import argparse
import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, Any, List
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


def run_test_runner(workspace: str, manifest: Dict[str, Any], results_dir: str) -> List[Dict[str, Any]]:
    """Invoke test runner (ats-test-esp32-demo) and collect results."""
    # Test runner is expected to be in workspace
    # It should read manifest and output results
    test_runner_path = Path(workspace) / "ats-test-esp32-demo" / "agent" / "run_tests.sh"
    
    tests = []
    
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
        env['SERIAL_PORT'] = os.environ.get('SERIAL_PORT', '/dev/ttyUSB0')
        
        try:
            result = subprocess.run(
                [str(test_runner_path), str(manifest_path)],
                cwd=Path(workspace) / "ats-test-esp32-demo",
                env=env,
                capture_output=True,
                text=True
            )
            
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
                    print("⏳ Waiting for ESP32 to boot after explicit reset...")
                    time.sleep(2.0)  # Additional 2 second wait
                    # #region agent log
                    debug_log("executor.py:152", "After second boot wait", {
                        "second_wait_seconds": 2.0
                    }, "A")
                    # #endregion
                else:
                    print("⚠️  Reset failed, continuing anyway")
    else:
        print(f"⚠️  Unknown device target: {device_target}")
        exit_code = 1
    
    # Step 2: Run tests
    if exit_code == 0:
        print("\n🧪 Running tests...")
        # #region agent log
        debug_log("executor.py:163", "Before run_test_runner", {
            "workspace": workspace,
            "time_since_flash": time.time() - flash_start_time if device_target == 'esp32' else None
        }, "D")
        # #endregion
        test_runner_start = time.time()
        tests = run_test_runner(args.workspace, manifest, args.results_dir)
        test_runner_end = time.time()
        # #region agent log
        debug_log("executor.py:169", "After run_test_runner", {
            "test_runner_duration_seconds": test_runner_end - test_runner_start,
            "test_count": len(tests),
            "test_statuses": [t.get('status') for t in tests]
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
