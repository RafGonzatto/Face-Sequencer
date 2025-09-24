@echo off
echo Generating OpenAPI schema files...
python build_openapi.py --json-schema --print-hash
if %ERRORLEVEL% neq 0 (
    echo Failed to generate schema files!
    exit /b %ERRORLEVEL%
)
echo Schema files generated successfully.