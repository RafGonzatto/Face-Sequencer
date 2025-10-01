#!/usr/bin/env python
"""
Reorganize debug_*.py and test_*.py files.

Features:
- Moves root-level debug_*.py into dev_tools/debug/ (creates directory)
- Moves root-level test_*.py into tests/ (or subfolders) using simple heuristics
- Detects duplicates against existing files in target locations (hash compare)
  * If identical: deletes the root duplicate
  * If different: moves to a *_conflicts folder for manual review
- Categorizes performance-related tests into tests/perf/ if name contains 'perf' or 'performance'
- Produces a JSON log (reorganize_log.json) with all actions
- Supports dry-run (default) or apply mode (--apply) to execute changes

Usage:
  python dev_tools/reorganize_files.py        # dry run
  python dev_tools/reorganize_files.py --apply
  python dev_tools/reorganize_files.py --apply --verbose

Exit codes:
  0 success
  1 unexpected error

Safe to re-run: idempotent for already processed files.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT / 'tests'
PERF_DIR = TESTS_DIR / 'perf'
DEBUG_TARGET_DIR = ROOT / 'dev_tools' / 'debug'
CONFLICT_TESTS_DIR = TESTS_DIR / '_migrated_conflicts'
CONFLICT_DEBUG_DIR = DEBUG_TARGET_DIR / '_conflicts'
LOG_FILE = ROOT / 'reorganize_log.json'

INCLUDE_PREFIX_TEST = 'test_'
INCLUDE_PREFIX_DEBUG = 'debug_'

PERF_KEYWORDS = {'perf', 'performance'}


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def discover_files(prefix: str, exclude_dirs: List[Path]) -> List[Path]:
    """Return root-level (ROOT only, not subdirs) files starting with prefix, excluding those in excluded dirs."""
    results = []
    for p in ROOT.iterdir():
        if not p.is_file():
            continue
        if p.name.startswith(prefix) and p.suffix == '.py':
            # skip if path in excluded
            if any(str(p).startswith(str(ex)) for ex in exclude_dirs):
                continue
            results.append(p)
    return sorted(results)


def classify_test_target(file_name: str) -> Path:
    lower = file_name.lower()
    if any(k in lower for k in PERF_KEYWORDS):
        return PERF_DIR / file_name
    return TESTS_DIR / file_name


def ensure_dirs():
    for d in [TESTS_DIR, PERF_DIR, DEBUG_TARGET_DIR, CONFLICT_TESTS_DIR, CONFLICT_DEBUG_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def process_tests(files: List[Path], apply: bool, verbose: bool) -> List[Dict[str, Any]]:
    actions = []
    for f in files:
        target = classify_test_target(f.name)
        target_parent = target.parent
        target_parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            src_hash = hash_file(f)
            tgt_hash = hash_file(target)
            if src_hash == tgt_hash:
                action = {
                    'type': 'delete_duplicate_test',
                    'source': str(f.relative_to(ROOT)),
                    'target': str(target.relative_to(ROOT)),
                    'hash': src_hash
                }
                actions.append(action)
                if apply:
                    f.unlink()
                if verbose:
                    print(f"[TEST][DUPLICATE] {f.name} identical to {target.relative_to(ROOT)} -> delete root copy")
            else:
                conflict_target = CONFLICT_TESTS_DIR / f.name
                action = {
                    'type': 'move_conflict_test',
                    'source': str(f.relative_to(ROOT)),
                    'target': str(conflict_target.relative_to(ROOT)),
                    'reason': 'hash_mismatch'
                }
                actions.append(action)
                if apply:
                    conflict_target.parent.mkdir(parents=True, exist_ok=True)
                    f.replace(conflict_target)
                if verbose:
                    print(f"[TEST][CONFLICT] {f.name} differs -> moved to {conflict_target.relative_to(ROOT)}")
        else:
            action = {
                'type': 'move_test',
                'source': str(f.relative_to(ROOT)),
                'target': str(target.relative_to(ROOT))
            }
            actions.append(action)
            if apply:
                f.replace(target)
            if verbose:
                print(f"[TEST][MOVE] {f.name} -> {target.relative_to(ROOT)}")
    return actions


def process_debug(files: List[Path], apply: bool, verbose: bool) -> List[Dict[str, Any]]:
    actions = []
    for f in files:
        target = DEBUG_TARGET_DIR / f.name
        if target.exists():
            src_hash = hash_file(f)
            tgt_hash = hash_file(target)
            if src_hash == tgt_hash:
                action = {
                    'type': 'delete_duplicate_debug',
                    'source': str(f.relative_to(ROOT)),
                    'target': str(target.relative_to(ROOT)),
                    'hash': src_hash
                }
                actions.append(action)
                if apply:
                    f.unlink()
                if verbose:
                    print(f"[DEBUG][DUPLICATE] {f.name} identical -> delete root copy")
            else:
                conflict_target = CONFLICT_DEBUG_DIR / f.stem / f.name
                action = {
                    'type': 'move_conflict_debug',
                    'source': str(f.relative_to(ROOT)),
                    'target': str(conflict_target.relative_to(ROOT)),
                    'reason': 'hash_mismatch'
                }
                actions.append(action)
                if apply:
                    conflict_target.parent.mkdir(parents=True, exist_ok=True)
                    f.replace(conflict_target)
                if verbose:
                    print(f"[DEBUG][CONFLICT] {f.name} differs -> {conflict_target.relative_to(ROOT)}")
        else:
            action = {
                'type': 'move_debug',
                'source': str(f.relative_to(ROOT)),
                'target': str(target.relative_to(ROOT))
            }
            actions.append(action)
            if apply:
                f.replace(target)
            if verbose:
                print(f"[DEBUG][MOVE] {f.name} -> {target.relative_to(ROOT)}")
    return actions


def write_log(all_actions: List[Dict[str, Any]], apply: bool):
    log_entry = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'mode': 'apply' if apply else 'dry-run',
        'actions': all_actions
    }
    existing: Dict[str, Any] | None = None
    if LOG_FILE.exists():
        try:
            existing = json.loads(LOG_FILE.read_text(encoding='utf-8'))
        except Exception:
            existing = None
    if existing and isinstance(existing, dict) and 'history' in existing:
        existing['history'].append(log_entry)
        LOG_FILE.write_text(json.dumps(existing, indent=2), encoding='utf-8')
    else:
        LOG_FILE.write_text(json.dumps({'history': [log_entry]}, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Reorganize debug/test files.')
    parser.add_argument('--apply', action='store_true', help='Execute changes (default is dry-run)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()

    ensure_dirs()
    # Exclude directories from root-level scanning
    exclude = [TESTS_DIR, DEBUG_TARGET_DIR]

    root_test_files = discover_files(INCLUDE_PREFIX_TEST, exclude)
    root_debug_files = discover_files(INCLUDE_PREFIX_DEBUG, exclude)

    if args.verbose:
        print(f"Discovered {len(root_test_files)} root test files and {len(root_debug_files)} root debug files")

    actions: List[Dict[str, Any]] = []
    actions.extend(process_tests(root_test_files, args.apply, args.verbose))
    actions.extend(process_debug(root_debug_files, args.apply, args.verbose))

    write_log(actions, args.apply)

    summary = {
        'mode': 'apply' if args.apply else 'dry-run',
        'total_actions': len(actions),
        'by_type': {}
    }
    for a in actions:
        summary['by_type'].setdefault(a['type'], 0)
        summary['by_type'][a['type']] += 1

    print("\n=== Reorganization Summary ===")
    print(json.dumps(summary, indent=2))
    print(f"Log written to {LOG_FILE.relative_to(ROOT)}")
    if not args.apply:
        print("(Dry run: re-run with --apply to perform these actions)")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Aborted by user")
        raise SystemExit(130)
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise SystemExit(1)
