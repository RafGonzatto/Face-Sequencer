# Configuration Management Guide

## Overview

This guide describes the centralized configuration system implemented in the Face Sequencer application. The configuration system allows for modifying application behavior through environment variables or a configuration file without changing code.

## Why Centralized Configuration?

Previously, the application used hardcoded values scattered across different modules, making it difficult to:

1. Change configuration values without code changes
2. Ensure consistent configuration across components
3. Override configuration for different environments
4. Document configuration options

The new approach provides a centralized configuration system with:

- Environment variable support
- Default values
- Documentation for each configuration parameter
- Type validation and conversion
- Hierarchical organization

## Configuration Structure

The configuration is organized in these categories:

| Category         | Description                                           |
| ---------------- | ----------------------------------------------------- |
| paths            | File system paths for various application directories |
| server           | Web server settings (host, port, debug mode)          |
| limits           | Various limits and thresholds                         |
| audio            | Audio processing parameters                           |
| features         | Feature flags to enable/disable functionality         |
| project_defaults | Default settings for new projects                     |
| logging          | Logging configuration                                 |

## Using the Configuration

### In Python Code

```python
from config import config

# Access configuration values
upload_dir = config.paths.upload_folder()
max_file_size = config.limits.max_upload_size()

# Check if a feature is enabled
if config.features.enhanced_alignment():
    # Use enhanced alignment
```

## Environment Variables

All configuration parameters can be overridden with environment variables. The environment variables follow the pattern:

```
FACE_SEQ_[SECTION]_[PARAMETER]
```

Examples:

| Environment Variable       | Description                 | Default Value |
| -------------------------- | --------------------------- | ------------- |
| FACE_SEQ_SERVER_PORT       | Web server port             | 5000          |
| FACE_SEQ_AUDIO_SAMPLE_RATE | Audio sample rate (Hz)      | 16000         |
| FACE_SEQ_UPLOAD_FOLDER     | Path for file uploads       | ./uploads     |
| FACE_SEQ_MAX_UPLOAD_SIZE   | Maximum upload size (bytes) | 209715200     |

## Configuration File

You can also use a configuration file by setting the `FACE_SEQ_CONFIG_FILE` environment variable to point to a JSON file. By default, the application will look for `config.json` in the application directory.

Example config.json:

```json
{
  "server": {
    "host": "localhost",
    "port": 8080,
    "debug": true
  },
  "audio": {
    "sample_rate": 22050,
    "high_pass_cutoff": 100
  }
}
```

## Audio Processing Configuration

| Parameter        | Description                   | Default | Environment Variable       |
| ---------------- | ----------------------------- | ------- | -------------------------- |
| sample_rate      | Audio sample rate in Hz       | 16000   | FACE_SEQ_AUDIO_SAMPLE_RATE |
| high_pass_cutoff | High-pass filter cutoff (Hz)  | 80      | FACE_SEQ_HIGH_PASS_CUTOFF  |
| preemphasis_coef | Pre-emphasis coefficient      | 0.97    | FACE_SEQ_PREEMPHASIS_COEF  |
| trim_top_db      | Audio trimming threshold (dB) | 30      | FACE_SEQ_TRIM_TOP_DB       |
| normalize_level  | Audio normalization level     | 0.95    | FACE_SEQ_NORMALIZE_LEVEL   |

### Silence Detection Parameters

| Parameter                | Description                   | Default | Environment Variable              |
| ------------------------ | ----------------------------- | ------- | --------------------------------- |
| silence_frame_length_ms  | Frame length in ms            | 25.0    | FACE_SEQ_SILENCE_FRAME_LENGTH_MS  |
| silence_frame_shift_ms   | Frame shift in ms             | 10.0    | FACE_SEQ_SILENCE_FRAME_SHIFT_MS   |
| silence_energy_threshold | Energy threshold (dB)         | -3.0    | FACE_SEQ_SILENCE_ENERGY_THRESHOLD |
| silence_zcr_threshold    | Zero crossing rate threshold  | 0.1     | FACE_SEQ_SILENCE_ZCR_THRESHOLD    |
| silence_noise_floor      | Noise floor energy level (dB) | -5.0    | FACE_SEQ_SILENCE_NOISE_FLOOR      |
| silence_energy_ceiling   | Energy ceiling level (dB)     | -1.0    | FACE_SEQ_SILENCE_ENERGY_CEILING   |

## Project Default Settings

| Parameter      | Description                             | Default | Environment Variable            |
| -------------- | --------------------------------------- | ------- | ------------------------------- |
| frame_duration | Default frame duration (ms)             | 80      | FACE_SEQ_DEFAULT_FRAME_DURATION |
| pause_duration | Default pause duration (ms)             | 120     | FACE_SEQ_DEFAULT_PAUSE_DURATION |
| fps            | Default frames per second               | 30      | FACE_SEQ_DEFAULT_FPS            |
| quality        | Default video quality (lower is better) | 18      | FACE_SEQ_DEFAULT_QUALITY        |
| preset         | Default video encoding preset           | medium  | FACE_SEQ_DEFAULT_PRESET         |

## Best Practices

1. **Don't Use Hardcoded Values**: Always use the config module for parameters
2. **Document New Config Values**: Add descriptions for new configuration parameters
3. **Provide Reasonable Defaults**: Choose sensible defaults that work for most cases
4. **Add Validation**: When needed, add validation to prevent invalid configurations
