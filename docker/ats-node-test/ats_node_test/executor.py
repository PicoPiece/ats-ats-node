"""Main test execution orchestrator."""
import argparse
import sys
import os
from pathlib import Path
from typing import Dict, Any, List

from .manifest import load_manifest, get_artifact_name, get_device_target, get_test_plan
from .hardware import detect_esp32_port, check_gpio_access
from .flash_esp32 import flash_firmware, reset_esp32
from .results import write_summary, write_junit, write_meta


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
        if not flash_firmware(str(artifact_path)):
            print("❌ Flash failed", file=sys.stderr)
            exit_code = 1
        else:
            print("✅ Flash successful")
    else:
        print(f"⚠️  Unknown device target: {device_target}")
        exit_code = 1
    
    # Step 2: Run tests
    if exit_code == 0:
        print("\n🧪 Running tests...")
        tests = run_test_runner(args.workspace, manifest, args.results_dir)
        
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
