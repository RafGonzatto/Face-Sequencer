# ERROR_HANDLING_GUIDE.md - Error Handling Guide for Face Sequencer Pro

## Centralized Error Handling System

This guide explains the new centralized error handling system implemented in the Face Sequencer Pro application. The system provides consistent error handling, logging, and user-friendly error messages across all components.

### Key Components

1. **Logger Module (`logger.py`)**: Provides centralized logging with consistent formatting
2. **Error Handlers (`error_handlers.py`)**: Provides decorators for API endpoints
3. **Exception Middleware (`exception_middleware.py`)**: Global error handlers for Flask
4. **Audio Error Handling (`audio_error_handling.py`)**: Specialized error handling for audio processing
5. **Error Utilities (`error_utils.py`)**: Common error handling utilities for safe operations

### Basic Usage

#### 1. Importing the Logger

```python
from logger import get_logger, log_exception

# Create a module-specific logger
my_logger = get_logger('module_name')
```

#### 2. Basic Logging

```python
# Log messages with different severity levels
my_logger.debug("Detailed debug information")
my_logger.info("General information")
my_logger.warning("Warning messages")
my_logger.error("Error information")
my_logger.critical("Critical issues")
```

#### 3. Logging Exceptions

```python
try:
    # Some code that might raise an exception
    result = complex_operation()
except Exception as e:
    # Log the exception with context
    log_exception(my_logger, e, {'context': 'relevant_info'})

    # Handle the exception appropriately
    # ...
```

#### 4. Using the API Error Handler Decorator

For Flask routes:

```python
from error_handlers import handle_api_errors

@app.route('/api/some-endpoint')
@handle_api_errors()
def my_endpoint():
    # This function is now wrapped with standardized error handling
    # Any exceptions will be caught, logged, and formatted as API responses
    # ...
```

#### 5. Using Classified Errors

```python
from error_handlers import ClassifiedAPIError

def some_function():
    if invalid_input:
        raise ClassifiedAPIError(
            "Invalid parameter value",
            error_type='validation_error',
            status=400,
            details={'param': 'value'}
        )
```

#### 6. Audio-Specific Error Handling (Updated)

The legacy `AudioProcessingError` has been deprecated and replaced by the unified hierarchy in `audio_exceptions.py` (notably `AlignmentError`). Decorators still translate legacy exceptions for backward compatibility, but new code should raise `AlignmentError` directly, supplying contextual `details`.

```python
from audio_error_handling import handle_audio_errors
from audio_exceptions import AlignmentError

@app.route('/api/audio/process')
@handle_audio_errors()
def process_audio():
    if not valid_format:
        raise AlignmentError(
            "Unsupported audio format",
            details={'format': file_format, 'legacy_error_type': 'format_error'}
        )
    # proceed with processing ...
```

### Best Practices

1. **Always log exceptions**: Use `log_exception()` instead of `print()` for errors
2. **Use specific loggers**: Create loggers with meaningful names for each module
3. **Add context to logs**: Provide relevant context information in log messages
4. **Use appropriate decorators**: Use `@handle_api_errors()` for API endpoints
5. **Use classified errors**: Use `ClassifiedAPIError` or `AlignmentError` for specific error types (legacy `AudioProcessingError` only when interacting with old modules)
6. **Never silently catch exceptions**: Always log the error before handling it
7. **Use safe operation utilities**: Use `safe_operation()` and `safe_file_operation()` for operations that might fail

### Using Error Utilities

#### Safe Operations

```python
from error_utils import safe_operation

# Execute operation safely
result = safe_operation(
    some_risky_function,
    args=[arg1, arg2],
    kwargs={'param': value},
    error_message="Failed to process data",
    default_return=[]
)
```

#### Safe File Operations

```python
from error_utils import safe_file_operation
import json

# Safely read a JSON file
data = safe_file_operation(
    json.load,
    "config.json",
    open("config.json", "r"),
    error_message="Failed to read configuration file",
    default_return={}
)
```

#### Basic Error Handling Decorator

```python
from error_utils import with_error_handling

@with_error_handling
def process_data(data):
    # This function will automatically log any errors
    # but will still raise them to be handled by the caller
    return transform_data(data)
```

### Error Types

Standard error types for API responses:

- `validation_error`: Invalid input parameters (HTTP 400)
- `not_found`: Resource not found (HTTP 404)
- `timeout_error`: Operation timed out (HTTP 504)
- `unexpected_error`: Unhandled server error (HTTP 500)
- `processing_error`: Known error during processing (HTTP 400-500)

Audio-specific (alignment) categories now surfaced through `AlignmentError` with `details.legacy_error_type` when mapped:

- `upload_error`: File / request validation issues
- `format_error`: Unsupported audio format
- `corrupt_file`: File unreadable or decode failure
- `alignment_failed`: Alignment pipeline failure
- `processing_timeout`: Timeout during processing
- `no_speech_detected`: Silence / insufficient speech
- `language_unsupported`: Unsupported language
- `system_unavailable`: Subsystem unavailable (models not loaded, etc.)

Note: These appear in responses as `error_type: alignment_error` plus granular hint in `details.legacy_error_type`.

### Log Files

Logs are stored in the `logs` directory with the naming pattern `face_sequencer_YYYYMMDD.log`. Each log entry includes:

- Timestamp
- Log level
- Logger name (module)
- Message

### Summary

The centralized error handling system ensures:

1. Consistent error reporting across all components
2. Proper logging of all errors with context
3. User-friendly error messages with appropriate HTTP status codes
4. Easy debugging through comprehensive logs
5. Standardized API error responses
