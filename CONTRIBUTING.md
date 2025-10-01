# Contributing Guide

Thank you for considering contributing! This project is migrating toward a modular
Flask blueprint architecture to improve clarity, testability, and runtime
initialization control.

## Blueprint Pattern

Place new route groups in a `<domain>_endpoints.py` file exporting a single
`<domain>_bp = Blueprint('<domain>', __name__)` object. Register blueprints in
`app.py` only after core configuration and heavy optional initialization.

Example structure:

```python
# foo_endpoints.py
from flask import Blueprint, jsonify
from api_responses import success_response

foo_bp = Blueprint('foo', __name__)

@foo_bp.route('/api/foo/ping', methods=['GET'])
def foo_ping():
    return jsonify(success_response('Foo OK'))
```

Then in `app.py` blueprint block:

```python
from foo_endpoints import foo_bp
app.register_blueprint(foo_bp)
```

## Error Response Contract

Use `success_response(...)` for successful JSON payloads and `error_response(...)`
for errors. Do not handcraft partial dictionaries—this keeps the OpenAPI schema
stable and tests green.

## Testing Guidelines

- Set `UNIT_TEST_MODE=1` to bypass heavy model/audio initialization.
- Avoid direct mutation of `app.view_functions`; prefer blueprint updates.
- When adding new endpoints, consider adding minimal contract tests under `tests/`.

## Debug & Test File Organization

- Place new ad-hoc investigation scripts inside `dev_tools/debug/` and name them descriptively (avoid `final` / `new` / `fix2`).
- Keep execution logic under a `main()` and guard with `if __name__ == '__main__':`.
- Never leave large one-off debug scripts at the repository root.
- Root scanning CI (planned) plus `dev_tools/reorganize_files.py` enforce this layout.

### Adding a New Test

1. Create the file under `tests/` prefixed with `test_`.
2. For performance / timing stress tests, prefer `tests/perf/`.
3. Keep test runtime minimal; long-running flows should be marked or skipped by default.

## Current Blueprints

| Domain    | File                    | Tag       | Purpose                                     |
| --------- | ----------------------- | --------- | ------------------------------------------- |
| util      | `util_endpoints.py`     | util      | Diagnostic & error demo endpoints           |
| audio     | `audio_endpoints.py`    | audio     | Upload, markers (alignment wrappers coming) |
| export    | `export_endpoints.py`   | export    | Video/JSON export + retry + SSE             |
| models    | `model_endpoints.py`    | models    | Model lifecycle & dynamic aliasing          |
| sequence  | `sequence_endpoints.py` | sequence  | Frame CRUD & preview                        |
| system    | `system_endpoints.py`   | system    | Health & cache stats                        |
| project   | (in `app.py`)           | project   | Project save/load (to be extracted)         |
| templates | (in `app.py`)           | templates | Template listing/apply (to be extracted)    |

When adding a new blueprint, append it here and add an OpenAPI fragment under `openapi/paths/` with a matching `tags: [...]` entry.

## OpenAPI Schema Updates

If your change affects public responses or adds new endpoints:

1. Update or add schema fragments under `openapi/paths` or `openapi/components`.
2. Include a meaningful `tags: [your_tag]` on each new path operation.
3. Run: `python build_openapi.py --json-schema`.
4. If CI drift guard fails, regenerate and commit the updated spec artifacts.

### Export Task Metadata

`ExportTask` includes: `status, progress, filename, path, error, message, quality_preset, crf, preset, fps, started_at, frame_count, encode_duration_ms`.
If you add more fields ensure you: (a) update `openapi/components/schemas.yaml`, (b) populate them in `export_endpoints.py`, (c) extend tests if stability matters.

## Code Style

- Prefer readable, small functions.
- Keep external dependencies minimal.
- Follow existing naming conventions (snake_case for functions, UpperCamelCase for classes).

Happy hacking!
