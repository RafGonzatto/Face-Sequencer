# Convenience Makefile for Face Sequencer Pro

PYTHON ?= python
PYTEST ?= $(PYTHON) -m pytest
COV_FAIL_UNDER ?= 70
COV_TARGETS ?= app.py enhanced_silence_detector.py api_responses.py audio_error_handling.py
COV_REPORT ?= $(foreach t,$(COV_TARGETS),--cov=$(t)) --cov-report=term-missing --cov-report=xml --cov-fail-under=$(COV_FAIL_UNDER)

.PHONY: help test fast-tests spec-validate lint coverage clean

help:
	@echo "Available targets:"
	@echo "  make test           - Run full primary test selection with coverage"
	@echo "  make fast-tests     - Run FAST_TESTS schema-only suite"
	@echo "  make spec-validate  - Validate openapi.yaml structure"
	@echo "  make build-spec     - Assemble modular spec into openapi.yaml"
	@echo "  make json-schema    - Build spec and export JSON Schema bundle"
	@echo "  make json-schema-hash - Build spec + JSON and print sha256 hashes"
	@echo "  make lint           - Run flake8 linting"
	@echo "  make coverage       - Open textual coverage report (after test)"
	@echo "  make clean          - Remove caches and coverage artifacts"

# Core curated suite (exclude heavy endpoints by default)
test:
	$(PYTEST) -q $(COV_REPORT) \
		tests/test_api_audio_endpoints.py \
		tests/test_openapi_contract.py \
		tests/test_sequence_schema.py \
		tests/test_enhanced_silence_detector.py

fast-tests:
	FAST_TESTS=1 $(PYTEST) -q tests/test_openapi_strict.py

spec-validate:
	$(PYTHON) - <<'EOF'
import sys, yaml, jsonschema
from pathlib import Path
spec = yaml.safe_load(Path('openapi.yaml').read_text(encoding='utf-8'))
# Minimal structural checks
assert 'openapi' in spec and spec['openapi'].startswith('3.'), 'Invalid OpenAPI version'
assert 'paths' in spec and isinstance(spec['paths'], dict), 'Missing paths section'
print('openapi.yaml basic validation passed with', len(spec['paths']), 'paths defined.')
EOF

build-spec:
	$(PYTHON) build_openapi.py > openapi.yaml
	@echo "Assembled openapi.yaml from modular fragments."

json-schema:
	$(PYTHON) build_openapi.py --json-schema
	@echo "Generated openapi.yaml and openapi_schemas.json"

json-schema-hash:
	$(PYTHON) build_openapi.py --json-schema --print-hash
	@echo "Generated spec + hashes above"

lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

coverage:
	coverage report -m || echo "Run 'make test' first to generate coverage data"

clean:
	rm -f coverage.xml
	rm -rf .pytest_cache
	find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>NUL || true
