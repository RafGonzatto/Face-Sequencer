# error_utils.py - Common error handling utilities
"""
Utility functions for standardized error handling across the application.
"""

import sys
import traceback
from typing import Dict, Any, Optional, Callable, TypeVar, List, Union, Tuple

from app.core.utils.logger import get_logger, log_exception

# Create logger for this module
utils_logger = get_logger('error.utils')

# Type variable for return type
T = TypeVar('T')

def safe_operation(operation: Callable[..., T], 
                   args: List = None, 
                   kwargs: Dict[str, Any] = None, 
                   error_message: str = "Operation failed", 
                   default_return: Optional[T] = None,
                   log_error: bool = True,
                   raise_error: bool = False,
                   logger_name: str = None) -> Union[T, Optional[T]]:
    """
    Execute an operation safely with proper error handling.
    
    Args:
        operation: The function to execute
        args: List of positional arguments for the function
        kwargs: Dict of keyword arguments for the function
        error_message: Message to log if the operation fails
        default_return: Value to return if the operation fails
        log_error: Whether to log the error (default True)
        raise_error: Whether to re-raise the exception after logging
        logger_name: Custom logger name to use
        
    Returns:
        The result of the operation or the default value if it fails
        
    Raises:
        Exception: If raise_error is True and an exception occurs
    """
    args = args or []
    kwargs = kwargs or {}
    
    # Get appropriate logger
    logger = get_logger(logger_name) if logger_name else utils_logger
    
    try:
        return operation(*args, **kwargs)
    except Exception as e:
        if log_error:
            context = {
                'operation': operation.__name__,
                'args': str(args),
                'kwargs': str(kwargs),
                'error': str(e)
            }
            log_exception(logger, e, context)
            
        if raise_error:
            raise
            
        return default_return

def safe_file_operation(operation: Callable[..., T],
                       filepath: str,
                       *args,
                       error_message: str = "File operation failed",
                       default_return: Optional[T] = None) -> Union[T, Optional[T]]:
    """
    Safely execute a file operation with proper error handling.
    
    Args:
        operation: The file operation function to execute
        filepath: The path to the file being operated on
        *args: Additional arguments for the operation
        error_message: Message to log if the operation fails
        default_return: Value to return if the operation fails
        
    Returns:
        The result of the operation or the default value if it fails
    """
    file_logger = get_logger('file.operations')
    
    try:
        return operation(filepath, *args)
    except Exception as e:
        context = {
            'operation': operation.__name__,
            'filepath': filepath,
            'error': str(e)
        }
        log_exception(file_logger, e, context)
        return default_return

def with_error_handling(func: Callable) -> Callable:
    """
    Simple decorator to add basic error handling to any function.
    Logs errors but does not prevent them from propagating.
    
    Args:
        func: The function to wrap with error handling
        
    Returns:
        Wrapped function with error handling
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Create a logger for the calling module
            logger = get_logger(func.__module__)
            
            # Log the exception with function context
            context = {
                'function': func.__name__,
                'args_count': len(args),
                'kwargs_keys': list(kwargs.keys()) if kwargs else None
            }
            log_exception(logger, e, context)
            
            # Re-raise the exception
            raise
    return wrapper