# config.py - Centralized configuration management system
"""
This module provides a centralized configuration system for Face Sequencer Pro.
It supports loading from environment variables, configuration files, and defaults.

Usage:
    from config import config
    
    # Access configuration values
    upload_path = config.paths.upload_folder
    max_file_size = config.limits.max_upload_size
    
    # Check if feature is enabled
    if config.features.enhanced_alignment:
        # Use enhanced alignment
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union, TypeVar, Generic, cast
from dataclasses import dataclass, field, asdict
import warnings

# Base directory for the application
BASE_DIR = Path(__file__).resolve().parent

# Set up logger for this module
logger = logging.getLogger("config")

# Type for configuration value
T = TypeVar('T')


class ConfigValue(Generic[T]):
    """Represents a configuration value with metadata"""
    
    def __init__(
        self,
        default: T,
        env_var: Optional[str] = None,
        description: str = "",
        validator: Optional[callable] = None,
    ):
        self.default = default
        self.env_var = env_var
        self.description = description
        self.validator = validator
        self._value: Optional[T] = None
        self._loaded = False
    
    def get(self) -> T:
        """Get the configuration value, loading it if necessary"""
        if not self._loaded:
            self._load()
        return cast(T, self._value)
    
    def _load(self) -> None:
        """Load the configuration value from environment or use default"""
        value = self.default
        
        # Try to load from environment if env_var is specified
        if self.env_var and self.env_var in os.environ:
            env_value = os.environ[self.env_var]
            try:
                # Convert environment value to the correct type based on default
                if isinstance(self.default, bool):
                    value = env_value.lower() in ('true', 'yes', '1', 'y')
                elif isinstance(self.default, int):
                    value = int(env_value)
                elif isinstance(self.default, float):
                    value = float(env_value)
                elif isinstance(self.default, list) or isinstance(self.default, dict):
                    value = json.loads(env_value)
                else:
                    value = env_value
                
                logger.debug(f"Loaded config from environment: {self.env_var}={value}")
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning(f"Error parsing environment variable {self.env_var}: {e}")
                value = self.default
        
        # Validate the value if a validator is specified
        if self.validator:
            try:
                valid = self.validator(value)
                if not valid:
                    logger.warning(f"Validation failed for {self.env_var or 'config value'}, using default")
                    value = self.default
            except Exception as e:
                logger.warning(f"Error in validator for {self.env_var or 'config value'}: {e}")
                value = self.default
        
        self._value = value
        self._loaded = True
    
    def set(self, value: T) -> None:
        """Set the configuration value programmatically"""
        if self.validator:
            valid = self.validator(value)
            if not valid:
                raise ValueError(f"Invalid value for {self.env_var or 'config value'}")
        
        self._value = value
        self._loaded = True
    
    def __call__(self) -> T:
        """Allow the config value to be called like a function"""
        return self.get()


@dataclass
class PathConfig:
    """Path configuration for the application"""
    base_dir: ConfigValue[Path] = field(default_factory=lambda: ConfigValue(
        default=BASE_DIR,
        env_var="FACE_SEQ_BASE_DIR",
        description="Base directory for the application"
    ))
    
    static_folder: ConfigValue[Path] = field(default_factory=lambda: ConfigValue(
        default=BASE_DIR / 'static',
        env_var="FACE_SEQ_STATIC_FOLDER",
        description="Directory for static files"
    ))
    
    template_folder: ConfigValue[Path] = field(default_factory=lambda: ConfigValue(
        default=BASE_DIR / 'templates',
        env_var="FACE_SEQ_TEMPLATE_FOLDER",
        description="Directory for template files"
    ))
    
    upload_folder: ConfigValue[Path] = field(default_factory=lambda: ConfigValue(
        default=BASE_DIR / 'uploads',
        env_var="FACE_SEQ_UPLOAD_FOLDER",
        description="Directory for uploaded files"
    ))
    
    audio_folder: ConfigValue[Path] = field(default_factory=lambda: ConfigValue(
        default=BASE_DIR / 'uploads' / 'audio',
        env_var="FACE_SEQ_AUDIO_FOLDER",
        description="Directory for uploaded audio files"
    ))
    
    projects_folder: ConfigValue[Path] = field(default_factory=lambda: ConfigValue(
        default=BASE_DIR / 'projects',
        env_var="FACE_SEQ_PROJECTS_FOLDER",
        description="Directory for project files"
    ))
    
    logs_folder: ConfigValue[Path] = field(default_factory=lambda: ConfigValue(
        default=BASE_DIR / 'logs',
        env_var="FACE_SEQ_LOGS_FOLDER",
        description="Directory for log files"
    ))
    
    def ensure_directories_exist(self) -> None:
        """Ensure all configured directories exist"""
        for field_name in self.__dataclass_fields__:
            field_value = getattr(self, field_name)
            if isinstance(field_value, ConfigValue):
                path = field_value.get()
                if isinstance(path, Path):
                    os.makedirs(path, exist_ok=True)
                    logger.debug(f"Ensured directory exists: {path}")


@dataclass
class ServerConfig:
    """Server configuration settings"""
    host: ConfigValue[str] = field(default_factory=lambda: ConfigValue(
        default="0.0.0.0",
        env_var="FACE_SEQ_HOST",
        description="Host to listen on"
    ))
    
    port: ConfigValue[int] = field(default_factory=lambda: ConfigValue(
        default=5000,
        env_var="FACE_SEQ_PORT",
        description="Port to listen on"
    ))
    
    debug: ConfigValue[bool] = field(default_factory=lambda: ConfigValue(
        default=False,
        env_var="FACE_SEQ_DEBUG",
        description="Enable debug mode"
    ))


@dataclass
class LimitsConfig:
    """Limits and thresholds for the application"""
    max_upload_size: ConfigValue[int] = field(default_factory=lambda: ConfigValue(
        default=200 * 1024 * 1024,  # 200MB
        env_var="FACE_SEQ_MAX_UPLOAD_SIZE",
        description="Maximum upload file size in bytes"
    ))
    
    allowed_audio_extensions: ConfigValue[set] = field(default_factory=lambda: ConfigValue(
        default={'wav', 'mp3', 'ogg', 'flac', 'm4a', 'aac', 'webm'},
        env_var="FACE_SEQ_ALLOWED_AUDIO_EXTS",
        description="Set of allowed audio file extensions"
    ))
    
    max_projects: ConfigValue[int] = field(default_factory=lambda: ConfigValue(
        default=100,
        env_var="FACE_SEQ_MAX_PROJECTS",
        description="Maximum number of projects to store"
    ))
    
    processing_timeout: ConfigValue[int] = field(default_factory=lambda: ConfigValue(
        default=300,  # 5 minutes
        env_var="FACE_SEQ_PROCESSING_TIMEOUT",
        description="Timeout for audio processing tasks in seconds"
    ))


@dataclass
class AudioConfig:
    """Audio processing configuration settings"""
    sample_rate: ConfigValue[int] = field(default_factory=lambda: ConfigValue(
        default=16000,  # 16kHz
        env_var="FACE_SEQ_AUDIO_SAMPLE_RATE",
        description="Sample rate for audio processing"
    ))
    
    high_pass_cutoff: ConfigValue[int] = field(default_factory=lambda: ConfigValue(
        default=80,  # 80Hz
        env_var="FACE_SEQ_HIGH_PASS_CUTOFF",
        description="High-pass filter cutoff frequency in Hz"
    ))
    
    preemphasis_coef: ConfigValue[float] = field(default_factory=lambda: ConfigValue(
        default=0.97,
        env_var="FACE_SEQ_PREEMPHASIS_COEF",
        description="Pre-emphasis coefficient for audio processing"
    ))
    
    trim_top_db: ConfigValue[int] = field(default_factory=lambda: ConfigValue(
        default=30,
        env_var="FACE_SEQ_TRIM_TOP_DB",
        description="Threshold for audio trimming in dB"
    ))
    
    normalize_level: ConfigValue[float] = field(default_factory=lambda: ConfigValue(
        default=0.95,
        env_var="FACE_SEQ_NORMALIZE_LEVEL",
        description="Audio normalization level"
    ))
    
    # Silence detection settings
    silence_frame_length_ms: ConfigValue[float] = field(default_factory=lambda: ConfigValue(
        default=25.0,  # 25ms
        env_var="FACE_SEQ_SILENCE_FRAME_LENGTH_MS",
        description="Frame length in milliseconds for silence detection"
    ))
    
    silence_frame_shift_ms: ConfigValue[float] = field(default_factory=lambda: ConfigValue(
        default=10.0,  # 10ms
        env_var="FACE_SEQ_SILENCE_FRAME_SHIFT_MS",
        description="Frame shift in milliseconds for silence detection"
    ))
    
    silence_energy_threshold: ConfigValue[float] = field(default_factory=lambda: ConfigValue(
        default=-3.0,
        env_var="FACE_SEQ_SILENCE_ENERGY_THRESHOLD",
        description="Energy threshold for silence detection (dB)"
    ))
    
    silence_zcr_threshold: ConfigValue[float] = field(default_factory=lambda: ConfigValue(
        default=0.1,
        env_var="FACE_SEQ_SILENCE_ZCR_THRESHOLD",
        description="Zero-crossing rate threshold for silence detection"
    ))
    
    silence_noise_floor: ConfigValue[float] = field(default_factory=lambda: ConfigValue(
        default=-5.0,
        env_var="FACE_SEQ_SILENCE_NOISE_FLOOR",
        description="Noise floor energy level for silence detection (dB)"
    ))
    
    silence_energy_ceiling: ConfigValue[float] = field(default_factory=lambda: ConfigValue(
        default=-1.0,
        env_var="FACE_SEQ_SILENCE_ENERGY_CEILING",
        description="Energy ceiling level for silence detection (dB)"
    ))


@dataclass
class FeaturesConfig:
    """Feature flags configuration"""
    enhanced_alignment: ConfigValue[bool] = field(default_factory=lambda: ConfigValue(
        default=True,
        env_var="FACE_SEQ_ENHANCED_ALIGNMENT",
        description="Enable enhanced audio alignment features"
    ))
    
    cache_enabled: ConfigValue[bool] = field(default_factory=lambda: ConfigValue(
        default=True,
        env_var="FACE_SEQ_CACHE_ENABLED",
        description="Enable audio processing cache"
    ))
    
    metrics_enabled: ConfigValue[bool] = field(default_factory=lambda: ConfigValue(
        default=True,
        env_var="FACE_SEQ_METRICS_ENABLED",
        description="Enable performance metrics collection"
    ))


@dataclass
class ProjectDefaultsConfig:
    """Default settings for new projects"""
    frame_duration: ConfigValue[int] = field(default_factory=lambda: ConfigValue(
        default=80,
        env_var="FACE_SEQ_DEFAULT_FRAME_DURATION",
        description="Default frame duration in milliseconds"
    ))
    
    pause_duration: ConfigValue[int] = field(default_factory=lambda: ConfigValue(
        default=120,
        env_var="FACE_SEQ_DEFAULT_PAUSE_DURATION",
        description="Default pause duration in milliseconds"
    ))
    
    fps: ConfigValue[int] = field(default_factory=lambda: ConfigValue(
        default=30,
        env_var="FACE_SEQ_DEFAULT_FPS",
        description="Default frames per second"
    ))
    
    quality: ConfigValue[int] = field(default_factory=lambda: ConfigValue(
        default=18,
        env_var="FACE_SEQ_DEFAULT_QUALITY",
        description="Default video quality (lower is better)"
    ))
    
    preset: ConfigValue[str] = field(default_factory=lambda: ConfigValue(
        default="medium",
        env_var="FACE_SEQ_DEFAULT_PRESET",
        description="Default video encoding preset"
    ))


@dataclass
class LoggingConfig:
    """Logging configuration settings"""
    log_level: ConfigValue[str] = field(default_factory=lambda: ConfigValue(
        default="INFO",
        env_var="FACE_SEQ_LOG_LEVEL",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    ))
    
    log_to_file: ConfigValue[bool] = field(default_factory=lambda: ConfigValue(
        default=False,
        env_var="FACE_SEQ_LOG_TO_FILE",
        description="Whether to log to a file"
    ))
    
    log_file: ConfigValue[str] = field(default_factory=lambda: ConfigValue(
        default="face_sequencer.log",
        env_var="FACE_SEQ_LOG_FILE",
        description="Log file name"
    ))


@dataclass
class AppConfig:
    """Main application configuration"""
    paths: PathConfig = field(default_factory=PathConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    project_defaults: ProjectDefaultsConfig = field(default_factory=ProjectDefaultsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    def __post_init__(self):
        """Ensure directories exist on initialization"""
        self.paths.ensure_directories_exist()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary for serialization"""
        result = {}
        for field_name, field_val in asdict(self).items():
            if isinstance(field_val, dict):
                result[field_name] = {}
                for k, v in field_val.items():
                    if hasattr(v, "get"):
                        result[field_name][k] = v.get()
                    else:
                        result[field_name][k] = v
            else:
                if hasattr(field_val, "get"):
                    result[field_name] = field_val.get()
                else:
                    result[field_name] = field_val
        return result
    
    def load_from_file(self, file_path: Union[str, Path]) -> None:
        """Load configuration from a JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Set configuration values from file
            for section_name, section in data.items():
                if hasattr(self, section_name):
                    section_obj = getattr(self, section_name)
                    for key, value in section.items():
                        if hasattr(section_obj, key):
                            config_value = getattr(section_obj, key)
                            if hasattr(config_value, "set"):
                                config_value.set(value)
                            else:
                                setattr(section_obj, key, value)
            
            logger.info(f"Loaded configuration from {file_path}")
        except Exception as e:
            logger.warning(f"Error loading configuration from {file_path}: {e}")


# Create the global configuration instance
config = AppConfig()

# Try to load from a configuration file if present
config_file = os.environ.get('FACE_SEQ_CONFIG_FILE', BASE_DIR / 'config.json')
if os.path.exists(config_file):
    config.load_from_file(config_file)