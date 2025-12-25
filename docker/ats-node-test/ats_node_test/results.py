"""Test result generation and output."""
import json
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


def write_summary(results_dir: str, summary: Dict[str, Any]) -> None:
    """Write ats-summary.json."""
    path = Path(results_dir) / "ats-summary.json"
    with open(path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Summary written: {path}")


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
