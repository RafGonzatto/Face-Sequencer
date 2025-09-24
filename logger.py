# logger.py - Centralized logging system
"""
Provides a centralized logging system with standardized format for all components.
"""

import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging format
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Configure file handler to write logs to file
file_handler = logging.FileHandler(
    f'logs/face_sequencer_{datetime.now().strftime("%Y%m%d")}.log',
    encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# Configure console handler for terminal output
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# Root logger configuration
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Keep track of loggers we've created
_loggers = {}

def get_logger(name: str) -> logging.Logger:
    """
    Get or create a named logger with consistent formatting.
    
    Args:
        name: Name for the logger, typically the module name
        
    Returns:
        Configured logger instance
    """
    if name in _loggers:
        return _loggers[name]
    
    logger = logging.getLogger(name)
    _loggers[name] = logger
    return logger

def log_exception(logger: logging.Logger, exc: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an exception with full stack trace and optional context information.
    
    Args:
        logger: Logger instance to use
        exc: Exception to log
        context: Optional dictionary of contextual information
    """
    exc_info = sys.exc_info()
    if context:
        context_str = ', '.join(f"{k}={v}" for k, v in context.items())
        logger.error(f"Exception: {exc.__class__.__name__}: {str(exc)} | Context: {context_str}", exc_info=exc_info)
    else:
        logger.error(f"Exception: {exc.__class__.__name__}: {str(exc)}", exc_info=exc_info)
    
    # Ensure the exception is fully logged
    if exc_info[2]:
        tb_lines = traceback.format_exception(*exc_info)
        logger.debug(''.join(tb_lines))

# Configure specific loggers for major components
api_logger = get_logger('api')
audio_logger = get_logger('audio')
video_logger = get_logger('video')
app_logger = get_logger('app')
task_logger = get_logger('task')

__all__ = [
    'get_logger',
    'log_exception',
    'api_logger',
    'audio_logger',
    'video_logger',
    'app_logger',
    'task_logger',
]