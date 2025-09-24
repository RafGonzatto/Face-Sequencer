@echo off
echo Checking OpenAPI schema consistency...
python check_schema_consistency.py
if %ERRORLEVEL% neq 0 (
    echo Schema files are out of sync!
    echo Run 'python build_openapi.py --json-schema' to update.
    exit /b %ERRORLEVEL%
)
echo Schema files are consistent.