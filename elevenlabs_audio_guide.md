# Enhanced ElevenLabs Audio Processing Guide

## Overview

This guide explains how to use the enhanced audio processing tools for ElevenLabs audio in the Face Sequencer project. The enhanced processor improves lip sync quality by optimizing audio characteristics specifically for speech animation alignment.

## Why Audio Processing Matters for Lip Sync

High-quality lip sync animation requires properly processed audio with the following characteristics:

1. **Clear speech transients** - Sharp consonant sounds need to be preserved and enhanced
2. **Reduced background noise** - Background noise can cause false lip movements
3. **Balanced dynamics** - Even audio levels help create consistent visemes
4. **Proper timing** - Silence trimming ensures accurate animation timing
5. **Optimized frequency response** - Enhancement of speech frequencies (1-4kHz) improves phoneme detection

## Using the Enhanced ElevenLabs Processor

### Quick Start

The simplest way to use the enhanced processor is to run the included batch file:

```
enhance_elevenlabs_audio.bat
```

This will:

1. Find any ElevenLabs MP3 files in the project directory
2. Process the most recent file with optimal settings
3. Save the enhanced audio to `uploads/audio/optimized_elevenlabs.wav`
4. Create visualization plots showing the audio improvement
5. Keep a copy of the original file for comparison

### Advanced Usage

For more control, you can run the Python script directly with options:

```
python enhanced_elevenlabs_processor.py --input your_file.mp3 --output custom_output.wav --plot
```

Command-line options:

- `--input` or `-i`: Specify the input audio file path
- `--output` or `-o`: Specify the output file path
- `--plot` or `-p`: Generate audio comparison visualizations
- `--quiet` or `-q`: Run without detailed output

### Using the Enhanced Audio in Face Sequencer

After processing your audio, it will automatically be available in the Face Sequencer app:

1. Start the application using `start.bat` or `py app.py`
2. In the web interface, select "Load Audio File"
3. Choose `optimized_elevenlabs.wav` from the audio list
4. Proceed with the normal lip sync animation workflow

## Processing Features

The enhanced processor applies these improvements to your ElevenLabs audio:

1. **High-pass filtering** - Removes low-frequency rumble below 80Hz
2. **Dynamic compression** - Evens out volume levels for consistent animation
3. **Pre-emphasis filtering** - Enhances consonant sounds critical for viseme detection
4. **Silence trimming** - Removes unnecessary silence from beginning/end
5. **Optimal normalization** - Sets ideal volume levels for processing

## Comparing Original vs. Enhanced Audio

The processor saves both the original and enhanced versions of your audio:

- Original: `uploads/audio/original_elevenlabs.mp3`
- Enhanced: `uploads/audio/optimized_elevenlabs.wav`

It also generates a visualization (`uploads/audio/audio_enhancement.png`) showing waveforms and spectrograms of both versions so you can see the improvements.

## Troubleshooting

If you encounter issues with the enhanced audio processor:

1. **Missing packages**: Run `pip install librosa soundfile numpy scipy matplotlib` to install required packages
2. **File not found**: Ensure your ElevenLabs audio file is in the project root directory and starts with "ElevenLabs"
3. **Alignment issues**: Try adjusting the high-pass filter cutoff or pre-emphasis settings in the Python script
4. **Performance issues**: For faster processing, consider installing the optional librosa acceleration packages

## Technical Details

The enhanced processor performs the following operations:

1. **Sample rate conversion** to 16kHz (optimal for speech processing)
2. **High-pass filter** with 80Hz cutoff (removes unwanted low frequencies)
3. **Dynamic compression** with 3:1 ratio above 0.15 threshold (evens out levels)
4. **Pre-emphasis filter** with 0.97 coefficient (enhances consonants)
5. **Silence trimming** with 20dB threshold (removes unnecessary silence)
6. **Peak normalization** to 95% (ensures optimal level for alignment)

These settings have been carefully tuned to improve lip sync quality with ElevenLabs audio files while preserving natural speech characteristics.
