# Dependency Injection Implementation Guide for Audio Modules

## Background

This guide explains the refactoring of the audio processing modules to use the dependency injection pattern,
addressing potential circular import risks between audio modules.

## Problem Statement

The original architecture had several audio modules that directly imported each other:

- `audio_aligner.py` imported `enhanced_silence_detector.py`, `forced_alignment.py`, and `frame_synchronizer.py`
- Modules made direct instantiations of classes from other modules
- Try/except blocks were used to handle missing dependencies
- Adding new features to these modules risked creating circular import dependencies

## Solution: Dependency Injection Pattern

The new architecture follows the dependency injection pattern:

1. Components accept their dependencies through constructor parameters
2. A central factory handles component creation and dependency wiring
3. Abstract interfaces/protocols define component contracts
4. Type checking is used to verify component compatibility

## Key Components

### 1. `audio_components.py`

This new module contains:

- Protocol definitions for audio components
- `AudioComponentFactory` - a singleton factory that creates and wires components
- Lazy loading of component implementations to avoid import issues
- Global `audio_factory` instance for easy access

### 2. Updated `audio_aligner.py`

The AudioAligner class now:

- Accepts silence_detector, aligner, and frame_synchronizer through its constructor
- Uses TYPE_CHECKING imports to avoid runtime circular imports
- Uses Protocol classes for runtime type checking
- Dynamically loads components only if they aren't injected

### 3. Refactored `app.py`

The app module now:

- Imports the component factory instead of individual components
- Uses the factory to create and wire audio processing components
- Maintains backward compatibility with existing code

## How to Use the Pattern

### 1. Getting Components

```python
# Import the factory
from audio_components import audio_factory

# Get audio components with automatic dependency wiring
audio_aligner = audio_factory.get_audio_aligner()
silence_detector = audio_factory.get_silence_detector()
```

### 2. Registering Custom Components

```python
# Register a custom component implementation
audio_factory.register_component("silence_detector", my_custom_silence_detector)

# Get the audio aligner - it will use your custom component
audio_aligner = audio_factory.get_audio_aligner()
```

### 3. Creating Components with Custom Dependencies

```python
# Create a custom silence detector
my_silence_detector = CustomSilenceDetector()

# Create an audio aligner with the custom silence detector
audio_aligner = audio_factory.get_audio_aligner(silence_detector=my_silence_detector)
```

## Benefits

1. **Eliminates Circular Imports**: Components don't directly import each other at runtime
2. **Testability**: Easy to inject mock components for testing
3. **Flexibility**: Components can be swapped at runtime
4. **Decoupling**: Modules depend on interfaces, not concrete implementations
5. **Maintainability**: Easier to extend and modify without breaking existing code

## Implementation Notes

This refactoring maintains backward compatibility with existing code while enabling
a more maintainable and flexible architecture going forward.
