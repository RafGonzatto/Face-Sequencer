"""Assemble modular OpenAPI spec fragments into a single source of truth.

This script serves as the single source of truth for generating both:
- openapi.yaml - The main OpenAPI specification
- openapi_schemas.json - The JSON Schema representation

Usage:
    # Generate both files with a single command:
    python build_openapi.py --json-schema

    # Only output YAML spec to stdout:
    python build_openapi.py
"""
from __future__ import annotations

import sys
import logging
from pathlib import Path
import json
import yaml
import hashlib
import argparse
from typing import Optional, Dict, Any, Tuple

ROOT = Path(__file__).parent
PARTS = {
    'paths': ROOT / 'openapi' / 'paths',
    'components': ROOT / 'openapi' / 'components'
}

def load_yaml_files(directory: Path):
    merged = {}
    for p in sorted(directory.glob('*.yaml')):
        with p.open('r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        # Paths files map path->operations directly; components files map componentName->schema
        for k, v in data.items():
            if k in merged and isinstance(v, dict):
                # merge nested dicts (shallow)
                merged[k].update(v)
            else:
                if k not in merged:
                    merged[k] = v
                else:
                    # Overwrite primitive or non-dict
                    merged[k] = v
    return merged

def build_spec(version_override: Optional[str] = None):
    paths = load_yaml_files(PARTS['paths'])
    schemas = load_yaml_files(PARTS['components'])
    spec = {
        'openapi': '3.0.3',
        'info': {
            'title': 'Face Sequencer Pro API',
            'version': version_override or '0.2.0',
            'description': 'Modular OpenAPI specification (assembled)'
        },
        'servers': [{'url': 'http://localhost:5000'}],
        'paths': paths,
        'components': {
            'schemas': schemas
        }
    }
    return spec

def export_json_schema(spec, out_path: Path):
    """Export components.schemas as a JSON Schema draft-07 compliant file.

    Each OpenAPI schema is embedded under $defs; StandardResponse becomes root sample.
    """
    components = spec.get('components', {}).get('schemas', {})
    bundle = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://example.com/face-sequencer/schemas.json",
        "$defs": components,
        "$ref": "#/$defs/StandardResponse"
    }
    out_path.write_text(json.dumps(bundle, indent=2), encoding='utf-8')


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def get_schema_version() -> str:
    """Determine the schema version from git or fallback to default."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip() or "0.2.0"
    except (subprocess.SubprocessError, FileNotFoundError):
        # Fallback if git command fails or git not available
        return "0.2.0"


def generate_schemas(version_override: Optional[str] = None, 
                     output_yaml: bool = True, 
                     output_json: bool = True,
                     print_hash: bool = False) -> Tuple[Optional[Path], Optional[Path]]:
    """Generate OpenAPI schema files from fragments.
    
    Returns:
        Tuple containing paths to generated yaml and json files (if requested)
    """
    version = version_override or get_schema_version()
    logging.info(f"Building OpenAPI schema version {version}")
    
    spec = build_spec(version_override=version)
    yaml_path = None
    json_path = None
    
    if output_yaml:
        yaml_path = Path('openapi.yaml')
        yaml_path.write_text(yaml.dump(spec, sort_keys=False, allow_unicode=True), encoding='utf-8')
        logging.info(f"Generated {yaml_path}")
    
    if output_json:
        json_path = Path('openapi_schemas.json')
        export_json_schema(spec, json_path)
        logging.info(f"Generated {json_path}")
    
    if print_hash:
        if yaml_path:
            print(f'openapi.yaml sha256: {_sha256(yaml_path)}')
        if json_path:
            print(f'openapi_schemas.json sha256: {_sha256(json_path)}')
            
    return yaml_path, json_path


def main():
    parser = argparse.ArgumentParser(description='Generate OpenAPI schema files')
    parser.add_argument('--version', help='Override schema version')
    parser.add_argument('--json-schema', action='store_true', 
                       help='Generate both YAML spec and JSON schema bundle')
    parser.add_argument('--yaml-only', action='store_true',
                       help='Generate only YAML spec file')
    parser.add_argument('--json-only', action='store_true',
                       help='Generate only JSON schema bundle')
    parser.add_argument('--print-hash', action='store_true',
                       help='Print SHA256 hash of generated files')
    parser.add_argument('--stdout', action='store_true',
                       help='Output YAML spec to stdout instead of file')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Set logging level')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Determine output modes
    output_yaml = not args.json_only and not args.stdout
    output_json = args.json_schema or args.json_only
    
    if args.stdout:
        # Legacy behavior: output YAML to stdout
        spec = build_spec(version_override=args.version)
        yaml.dump(spec, sys.stdout, sort_keys=False, allow_unicode=True)
    else:
        # Generate files
        generate_schemas(
            version_override=args.version,
            output_yaml=output_yaml,
            output_json=output_json,
            print_hash=args.print_hash
        )

if __name__ == '__main__':
    main()
