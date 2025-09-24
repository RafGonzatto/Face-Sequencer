# Schema Versioning Strategy

## Purpose

Provide a clear, reproducible process for evolving the Face Sequencer Pro API contract with a single source of truth while preventing schema drift.

## Single Source of Truth

The canonical specification is `openapi.yaml` (assembled via `build_openapi.py` from modular fragments under `openapi/`). All derivative artifacts MUST be generated from this file:

- `openapi.yaml` – Assembled spec committed to the repo.
- `openapi_schemas.json` – JSON Schema bundle of component schemas under `$defs` for programmatic validation and client code generation.

## Version Numbering

The `info.version` field in `openapi.yaml` uses semantic versioning: MAJOR.MINOR.PATCH.

- MAJOR: Backward-incompatible changes (removed fields, renamed endpoints, changed data types, authorization model shifts).
- MINOR: Backward-compatible additions (new endpoints, optional fields, new enum values that do not break existing clients).
- PATCH: Strictly non-contractual changes (typos in descriptions, doc clarifications, internal-only schema annotations) OR bug fixes that do not modify response/request shape.

## Backward Compatibility Rules

The following changes are considered BREAKING and require a MAJOR bump:

1. Removing an endpoint or path operation.
2. Removing a required property or making a previously required property optional only if behavior changes (downgrade of requirement is usually minor unless logic changes).
3. Changing a property type or format (e.g. integer -> string, number -> object).
4. Renaming properties without providing transitional aliases.
5. Tightening validation constraints (reducing max length, increasing minimum, narrowing enum values).

The following changes are NON-BREAKING (MINOR):

1. Adding a new endpoint or operation.
2. Adding new optional properties to request or response objects.
3. Adding new enum values (clients should be resilient to unknown values – enforced by tests; if not, treat as MAJOR).
4. Adding new component schemas not referenced by existing responses.

The following changes are PATCH:

1. Description / summary edits.
2. Reordering keys.
3. Internal metadata fields under `x-` extension namespaces.

## Change Workflow

1. Modify or add modular fragments in `openapi/paths` or `openapi/components`.
2. Run: `python build_openapi.py --json-schema` to regenerate `openapi.yaml` and `openapi_schemas.json`.
3. Update version in build script (or fragment) if required by change category.
4. Run tests: `pytest -k openapi` to validate schema conformance.
5. Commit all changed artifacts in the same commit (spec + generated JSON + version bump rationale in commit message).

## Automated Validation

Existing tests perform these checks:

- `test_openapi_contract.py` – Ensures documented paths exist & envelope shape.
- `test_openapi_strict.py` – Validates live responses against expanded schemas.
- `test_sequence_schema.py` – Verifies request/response shapes of sequence endpoints.

Additional WP005 Enhancements (this commit):

- New test `test_schema_generation_fresh.py` ensures `openapi_schemas.json` matches a freshly generated version (no drift).
- Hash comparison prevents accidental manual edits to generated file.

## Regeneration Policy

Never edit `openapi_schemas.json` manually. Always regenerate via the build script. CI (future) can enforce by rebuilding and diffing.

## Client Generation (Future)

Downstream SDK generation (Python/JS) will consume `openapi.yaml`. A future script may snapshot schemas per MAJOR version under `schemas/v{MAJOR}/` to allow parallel client maintenance.

## Deprecation Process

1. Mark endpoints or fields with `x-deprecated: true` and add a description note referencing replacement.
2. Maintain for at least one MINOR release.
3. Remove only in the next MAJOR version.

## Checklist for Schema PRs

- [ ] Version bumped appropriately.
- [ ] build script executed; artifacts regenerated.
- [ ] Tests pass (`pytest -k openapi`).
- [ ] No manual edits to generated file.
- [ ] Deprecations documented (if applicable).

---

Document created during WP005 (Schema Consolidation).
