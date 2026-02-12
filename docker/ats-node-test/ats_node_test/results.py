"""Test result generation and output."""
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


def write_summary(results_dir: str, summary: Dict[str, Any]) -> None:
    """Write ats-summary.json (overwrites any file written by test runner so artifact reflects executor result)."""
    path = Path(results_dir) / "ats-summary.json"
    status = summary.get('status', 'UNKNOWN')
    with open(path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Summary written: {path} (status={status})")


def write_junit(results_dir: str, tests: List[Dict[str, Any]]) -> None:
    """Write junit.xml."""
    path = Path(results_dir) / "junit.xml"
    
    total = len(tests)
    failures = sum(1 for t in tests if t.get('status') == 'FAIL')
    
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="ATS Hardware Tests" tests="{total}" failures="{failures}">
'''
    
    for test in tests:
        name = test.get('name', 'unknown')
        status = test.get('status', 'UNKNOWN')
        failure_msg = test.get('failure', '')
        
        xml += f'    <testcase name="{name}" classname="HardwareTest">\n'
        if status == 'FAIL':
            xml += f'      <failure>{failure_msg}</failure>\n'
        xml += '    </testcase>\n'
    
    xml += '''  </testsuite>
</testsuites>
'''
    
    with open(path, 'w') as f:
        f.write(xml)
    print(f"✅ JUnit XML written: {path}")


def write_metrics(results_dir: str, tests: List[Dict[str, Any]],
                   manifest: Dict[str, Any], duration: float = 0.0) -> None:
    """Write metrics.json for Prometheus exporter.

    The metrics exporter (metrics_exporter.py) reads this file on each
    Prometheus scrape and exposes the values at /metrics.
    """
    path = Path(results_dir) / "metrics.json"

    passed = sum(1 for t in tests if t.get('status') == 'PASS')
    failed = sum(1 for t in tests if t.get('status') == 'FAIL')
    fw_version = manifest.get('build', {}).get('build_number', 'unknown')

    # Read previous totals so counters accumulate across runs
    prev_pass = 0
    prev_fail = 0
    if path.exists():
        try:
            with open(path, 'r') as f:
                prev = json.load(f)
                prev_pass = prev.get('ats_test_pass_total', 0)
                prev_fail = prev.get('ats_test_fail_total', 0)
        except Exception:
            pass

    # Also try the host metrics file (mounted by Jenkins/Docker)
    host_metrics = os.getenv('HOST_METRICS_FILE', '')
    if host_metrics and Path(host_metrics).exists():
        try:
            with open(host_metrics, 'r') as f:
                prev = json.load(f)
                prev_pass = max(prev_pass, prev.get('ats_test_pass_total', 0))
                prev_fail = max(prev_fail, prev.get('ats_test_fail_total', 0))
        except Exception:
            pass

    metrics = {
        'ats_test_pass_total': prev_pass + passed,
        'ats_test_fail_total': prev_fail + failed,
        'ats_test_duration_seconds': round(duration, 2),
        'ats_fw_version': str(fw_version),
        'ats_test_last_run_timestamp': int(time.time()),
        'ats_test_in_progress': 0,
    }

    with open(path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"✅ Metrics written: {path}")
    print(f"   pass={metrics['ats_test_pass_total']}, "
          f"fail={metrics['ats_test_fail_total']}, "
          f"fw={metrics['ats_fw_version']}")

    # If HOST_METRICS_FILE is set, also write there directly
    if host_metrics:
        try:
            os.makedirs(os.path.dirname(host_metrics), exist_ok=True)
            with open(host_metrics, 'w') as f:
                json.dump(metrics, f, indent=2)
            print(f"✅ Host metrics updated: {host_metrics}")
        except Exception as e:
            print(f"⚠️  Could not write host metrics: {e}")


def write_meta(results_dir: str, manifest: Dict[str, Any], exit_code: int) -> None:
    """Write meta.yaml with execution metadata."""
    path = Path(results_dir) / "meta.yaml"
    
    meta = {
        'execution': {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'exit_code': exit_code,
            'status': 'PASS' if exit_code == 0 else 'FAIL'
        },
        'manifest': {
            'version': manifest.get('manifest_version'),
            'build_number': manifest.get('build', {}).get('build_number'),
            'device_target': manifest.get('device', {}).get('target')
        }
    }
    
    import yaml
    with open(path, 'w') as f:
        yaml.dump(meta, f, default_flow_style=False)
    print(f"✅ Meta written: {path}")
