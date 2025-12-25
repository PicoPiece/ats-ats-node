"""Manifest loader and validator for ATS v1 schema."""
import yaml
from pathlib import Path
from typing import Dict, Any


class ManifestError(Exception):
    """Manifest validation or loading error."""
    pass


def load_manifest(manifest_path: str) -> Dict[str, Any]:
    """Load and validate ats-manifest.yaml v1."""
    path = Path(manifest_path)
    if not path.exists():
        raise ManifestError(f"Manifest not found: {manifest_path}")
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    if not data:
        raise ManifestError("Manifest is empty")
    
    if data.get('manifest_version') != 1:
        raise ManifestError(f"Unsupported manifest version: {data.get('manifest_version')}")
    
    # Validate required fields
    required = ['build', 'device', 'test_plan', 'timestamps']
    for field in required:
        if field not in data:
            raise ManifestError(f"Missing required field: {field}")
    
    return data


def get_artifact_name(manifest: Dict[str, Any]) -> str:
    """Extract firmware artifact name from manifest."""
    return manifest['build']['artifact']['name']


def get_device_target(manifest: Dict[str, Any]) -> str:
    """Extract device target from manifest."""
    return manifest['device']['target']


def get_test_plan(manifest: Dict[str, Any]) -> list:
    """Extract test plan from manifest."""
    return manifest['test_plan']
