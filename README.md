# Face Sequencer Pro

A modern, web-based lip-sync animation tool that transforms text into animated sequences using facial expression images.

## 🚀 Quick Start

1. **Launch the application:**

   ```bash
   python launch.py
   ```

2. **Open your browser and go to:**

   ```
   http://localhost:5000
   ```

3. **For ElevenLabs audio users:**
   ```bash
   # Process ElevenLabs audio for optimal lip sync
   .\enhance_elevenlabs_audio.bat
   ```

## ✨ Features

### Modern Web Interface

- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Drag & Drop**: Easily assign images to characters by dragging files
- **Real-time Preview**: See your animation as you build it
- **Interactive Timeline**: Scrub through frames and edit durations

### Enhanced Functionality

- **Visual Character Mapping**: Grid-based interface showing all alphabet mappings
- **Smart Pause Visualization**: Animated pause indicators instead of text
- **ElevenLabs Audio Enhancement**: Optimize ElevenLabs audio for better lip sync quality
- **Audio Visualization**: Compare original and enhanced audio with waveform and spectrogram plots
- **Project Templates**: Quick-start templates for different animation styles
- **Batch Operations**: Export multiple formats simultaneously

### Professional Export Options

- **Multiple Formats**: MP4 video and JSON sequence data
- **Quality Presets**: High, Medium, and Fast export options
- **Background Processing**: Non-blocking video generation
- **Progress Tracking**: Real-time export progress monitoring

### Project Management

- **Save/Load Projects**: Complete project state persistence
- **Recent Projects**: Quick access to recently opened projects
- **Templates**: Pre-configured settings for common use cases
- **Auto-save**: Never lose your work

## 📁 Project Structure

```
Face Sequencer Pro/
├── app.py                 # Main Flask web application
├── lipanim_core.py       # Core animation functionality
├── project_templates.py  # Project templates and management
├── launch.py             # Startup script with dependency management
├── requirements.txt      # Python dependencies
├── templates/
│   └── index.html        # Main web interface
├── static/
│   ├── css/
│   │   └── styles.css    # Modern UI styles
│   └── js/
│       └── app.js        # Frontend JavaScript application
├── projects/             # Saved projects directory
└── uploads/              # Temporary files and exports
```

## 🎯 Usage Guide

### 1. Setting Up Images

- **Browse Folder**: Select a folder containing your facial expression images
- **File Naming**: Name files after the letters they represent (e.g., `A.png`, `B.jpg`)
- **Drag & Drop**: Drag images directly onto character slots in the mapping grid
- **Fallback Image**: Set a default image for unmapped characters

### 2. Creating Animation

- **Enter Text**: Type your animation text in the input area
- **Build Sequence**: Click "Build Sequence" to generate the frame timeline
- **Preview**: Use playback controls to preview your animation
- **Edit Frames**: Click frames to edit duration and properties

### 3. Export Options

- **MP4 Video**: Professional video output with quality presets
- **JSON Data**: Sequence data for integration with other tools
- **Batch Export**: Export multiple formats at once

### 4. Project Management

- **Templates**: Start with pre-configured templates
- **Save Project**: Save complete project state including settings
- **Recent Projects**: Quick access to previously worked projects
- **Auto-save**: Automatic project state preservation

## 🛠️ Technical Requirements

### System Requirements

- **Python**: 3.8 or higher
- **FFmpeg**: Required for video export (optional)
- **Web Browser**: Modern browser with JavaScript support

### Dependencies

All dependencies are automatically installed by the launch script:

- Flask (web framework)
- Pillow (image processing)
- MoviePy (video generation)
- Additional utilities

## 🎨 Customization

### Templates

Create custom templates by modifying `project_templates.py`:

- Animation settings (frame duration, FPS, quality)
- Sample text and recommended file structure
- Export presets

### Styling

Customize the interface by editing `static/css/styles.css`:

- Color scheme and typography
- Layout and spacing
- Animation effects

### Functionality

Extend features by modifying:

- `app.py`: Backend API endpoints
- `static/js/app.js`: Frontend functionality
- `lipanim_core.py`: Core animation logic

## 📊 Quality Presets

### High Quality

- **CRF**: 12 (highest quality)
- **Preset**: Slow (best compression)
- **Use Case**: Professional productions

### Medium Quality (Default)

- **CRF**: 18 (balanced quality/size)
- **Preset**: Medium (balanced speed)
- **Use Case**: General purpose animations

### Fast Export

- **CRF**: 24 (smaller file size)
- **Preset**: Fast (quick processing)
- **Use Case**: Rapid prototyping and testing

## 🔧 Troubleshooting

### Common Issues

**1. Server won't start:**

- Check if port 5000 is available
- Verify Python version (3.8+)
- Run `pip install -r requirements.txt`

**2. Video export fails:**

- Install FFmpeg from https://ffmpeg.org/
- Check image file formats (PNG, JPG supported)
- Ensure sufficient disk space

**3. Images not loading:**

- Verify image file permissions
- Check file formats (PNG, JPG, WEBP, BMP supported)
- Ensure folder path is accessible

### Performance Tips

1. **Use appropriate image sizes** (recommended: 512x512px max)
2. **Optimize image formats** (PNG for transparency, JPG for photos)
3. **Close unused browser tabs** during export
4. **Use SSD storage** for better I/O performance

## 📝 License

This project enhances the original Face Sequencer tool with a modern web interface and professional features while maintaining compatibility with existing workflows.

## 🔊 Audio Enhancement for Lip Sync

The project includes specialized tools for optimizing ElevenLabs audio files for lip-sync animation:

### Enhanced ElevenLabs Audio Processor

Process your ElevenLabs audio files for optimal lip-sync quality with a single command:

```bash
.\enhance_elevenlabs_audio.bat
```

This tool performs several optimizations:

- **High-pass filtering**: Removes low-frequency rumble that can cause false lip movements
- **Dynamic compression**: Evens out volume levels for consistent animation
- **Pre-emphasis**: Enhances consonant sounds critical for accurate viseme detection
- **Silence trimming**: Removes unnecessary silence for better timing
- **Audio normalization**: Sets optimal volume levels for processing

### Audio Comparison Visualization

The processor automatically generates visualization plots showing the before/after comparison:

- Waveform comparison
- Spectrogram analysis
- Audio statistics

### Advanced Usage

For more control over the audio processing, use the Python script directly:

```bash
python enhanced_elevenlabs_processor.py --input your_file.mp3 --output custom_output.wav --plot
```

For full documentation, see [ElevenLabs Audio Guide](elevenlabs_audio_guide.md)

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- Additional export formats (GIF, WebM)
- Cloud storage integration
- Collaborative editing features
- Mobile app companion

## 🎬 Version History

### v2.1 - Audio Enhancement Update

- Enhanced ElevenLabs audio processor
- Audio visualization with waveform and spectrogram comparison
- Improved lip-sync quality with specialized audio processing
- Comprehensive documentation for audio optimization

### v2.0 - Modern Web Interface

- Complete UI/UX redesign
- Drag & drop functionality
- Interactive timeline
- Project templates
- Enhanced export options
- Real-time preview

### v1.0 - Original Tkinter Version

- Basic desktop interface
- Core animation functionality
- MP4 and JSON export
