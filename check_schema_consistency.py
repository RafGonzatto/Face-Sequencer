"""
Schema consistency checker for CI/CD pipelines.

This script:
1. Regenerates the OpenAPI schema files
2. Checks if there are any differences with the committed versions
3. Reports if the schema files are out of sync
"""
import sys
import hashlib
import subprocess
import json
from pathlib import Path

def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        # Read in 64kb chunks
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    """Main entry point."""
    print("Checking OpenAPI schema consistency...")
    
    # Original files
    yaml_path = Path('openapi.yaml')
    json_path = Path('openapi_schemas.json')
    
    if not yaml_path.exists() or not json_path.exists():
        print("ERROR: Schema files don't exist. Run 'python build_openapi.py --json-schema' first.")
        return 1
    
    # Store original hashes
    yaml_original_hash = calculate_file_hash(yaml_path)
    json_original_hash = calculate_file_hash(json_path)
    
    # Create temporary copies
    temp_yaml = yaml_path.with_suffix('.yaml.tmp')
    temp_json = json_path.with_suffix('.json.tmp')
    
    try:
        # Create backup copies
        yaml_path.rename(temp_yaml)
        json_path.rename(temp_json)
        
        # Regenerate files
        subprocess.run(['python', 'build_openapi.py', '--json-schema'], 
                      check=True, capture_output=True, text=True)
        
        # Calculate new hashes
        yaml_new_hash = calculate_file_hash(yaml_path)
        json_new_hash = calculate_file_hash(json_path)
        
        # Check if files have changed
        yaml_changed = yaml_original_hash != yaml_new_hash
        json_changed = json_original_hash != json_new_hash
        
        if yaml_changed or json_changed:
            print("❌ ERROR: Schema files are out of sync!")
            if yaml_changed:
                print(f"  - openapi.yaml has changed (old: {yaml_original_hash[:8]}..., new: {yaml_new_hash[:8]}...)")
            if json_changed:
                print(f"  - openapi_schemas.json has changed (old: {json_original_hash[:8]}..., new: {json_new_hash[:8]}...)")
            print("Run 'python build_openapi.py --json-schema' to update the files.")
            return 1
        else:
            print("✅ Schema files are up to date!")
            return 0
    
    finally:
        # Clean up and restore original files
        if yaml_path.exists():
            yaml_path.unlink()
        if json_path.exists():
            json_path.unlink()
        
        if temp_yaml.exists():
            temp_yaml.rename(yaml_path)
        if temp_json.exists():
            temp_json.rename(json_path)

if __name__ == "__main__":
    sys.exit(main())