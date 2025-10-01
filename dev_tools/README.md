# Dev Tools

Utility, diagnostic, and demo scripts for the Face Sequencer Pro project.

## Layout

```
dev_tools/
├── debug/                # Former root debug_* scripts (manual diagnostics)
├── demos/                # High-level demonstration scripts (trimmed or examples)
├── reorganize_files.py   # Automation to enforce file layout rules
├── README.md             # (this file)
└── ... (future helpers)
```

## Conventions

- Place new one-off exploratory scripts in `debug/` with clear names (e.g. `audio_latency_probe.py`).
- Place reusable or showcase demonstration code in `demos/`.
- Keep side effects under `if __name__ == "__main__":` guards.
- Avoid adding heavyweight dependencies that are not already in the main requirements files.
- Prefer small, focused scripts over large multi-purpose ones.

## Root Hygiene Enforcement

The CI workflow includes a Root File Hygiene job that fails if new root files match these patterns:

- `simple_*.py`
- `*_demo.py`
- `*_test.py`
- `*_fix.py`

If you need to add something matching one of those suffixes/prefixes, put it in `dev_tools/` (or `tests/` for actual tests) instead of the repository root.

Run the layout reorganizer manually:

```
python dev_tools/reorganize_files.py          # dry run
python dev_tools/reorganize_files.py --apply  # apply moves
```

or on Windows (batch wrapper):

```
reorganize_files.bat --apply --verbose
```

## Future Ideas

- Add performance profiling helpers (`perf/` subfolder)
- Integrate flamegraph generation script
- Expand demos with full enhanced alignment example (currently trimmed)

Contributions welcome—follow guidelines in the top-level `CONTRIBUTING.md`.
