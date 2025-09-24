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

## OpenAPI Schema Updates

If your change affects public responses or adds new endpoints:

1. Update or add schema fragments under `openapi/`.
2. Run: `python build_openapi.py --json-schema`.
3. Commit updated `openapi.yaml` and `openapi_schemas.json`.

## Code Style

- Prefer readable, small functions.
- Keep external dependencies minimal.
- Follow existing naming conventions (snake_case for functions, UpperCamelCase for classes).

Happy hacking!
