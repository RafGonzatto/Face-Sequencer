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

### API Documentation & Schema Management

- **OpenAPI Specification**: Comprehensive API documentation available at `/docs`
- **Single Source of Truth**: All API schemas are generated from modular fragments
- **Automated Schema Generation**: Consistent schema generation for YAML and JSON versions
- **Schema Validation**: Runtime schema validation ensures API response consistency

#### Managing API Schemas

The project uses a single source of truth for API schemas:

```bash
# Generate both OpenAPI YAML and JSON Schema files:
python build_openapi.py --json-schema

# Or use the convenience script:
./generate_schemas.bat
```

Schema files are automatically regenerated when accessing the API docs if the
source fragments have changed.

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
├── app.py                      # Main Flask web application
├── launch.py                   # Startup script with dependency management
├── dev_tools/
│   ├── reorganize_files.py     # Automation for relocating debug/test scripts
│   └── debug/                  # Former root debug_*.py scripts (manual diagnostics)
├── tests/                      # All test_*.py (unit/integration/e2e)
│   └── perf/                   # Performance / smoke perf tests (if any)
├── templates/                  # Jinja2 templates (modularized base + partials)
├── static/                     # Frontend assets (css/js)
├── projects/                   # Saved projects directory
├── uploads/                    # Temporary files and exports
└── requirements.txt            # Python dependencies
```

> Note: Legacy root-level `debug_*.py` and `test_*.py` files are now automatically
> migrated via `reorganize_files.bat`. New debug helpers should live in
> `dev_tools/debug/` and new tests directly under `tests/`.

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

## 🧪 Test & CI Harness

Automated end-to-end tests rely on a lightweight frontend test harness:

- File: `static/js/test_harness.js`
- Activation: server injects `window.__TEST_MODE__ = true` when either `TEST_MODE` (backend test mode) or `FRONTEND_TEST_MODE` is set.
- Provides:
  - Early `window.videoEditor` stub so Selenium tests can monkey‑patch before the full editor loads.
  - A guaranteed `.partial-transcript-panel` element the tests wait for.
  - Helper `window.__updateTestTranscriptPanel(msg)` utility.

Environment flags:

| Variable             | Purpose                                                                   |
| -------------------- | ------------------------------------------------------------------------- |
| `TEST_MODE`          | Broad backend test mode (skips heavy inits) and enables frontend harness. |
| `FRONTEND_TEST_MODE` | Enables only the frontend harness without broader backend shortcuts.      |

Harness loads only when test mode script is injected; there is no webdriver heuristic.

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

**CRF**: 15 (high quality, optimized for animation edges)

### Medium Quality (Default)

**CRF**: 20 (balanced quality/size for lip-sync sequences)

### Fast Export

**CRF**: 26 (smaller file size, acceptable for previews)

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

## 🧩 Modularization & Blueprints

The application is migrating from a monolithic `app.py` to a modular blueprint
structure for clearer separation of concerns and improved test reliability.

Current blueprint modules:

- `util_endpoints.py` (`util_bp`): Utility / diagnostic endpoints (e.g. `/api/util/error-demo-v2`).
- `audio_endpoints.py` (`audio_bp`): Audio upload, markers and (moving toward) alignment wrappers.
- `export_endpoints.py` (`export_bp`): JSON & video export initiation, status polling, retry, SSE progress streaming.
- `model_endpoints.py` (`model_bp`): Model lifecycle (preload/list/stats/unload) plus dynamic alias registration.
- `sequence_endpoints.py` (`sequence_bp`): Sequence frame CRUD & frame preview endpoints.
- `system_endpoints.py` (`system_bp`): Health and cache stats endpoints.

Rationale:

1. Avoid brittle import-time side effects and route rebinding hacks.
2. Allow late registration after optional heavy initialization (e.g. audio
   alignment) while keeping tests lightweight via `UNIT_TEST_MODE`.
3. Encourage future grouping (e.g. `audio_bp`, `export_bp`, `project_bp`).

Migration Guidance:

- Add new logical domains as `<domain>_endpoints.py` with `<domain>_bp = Blueprint(...)`.
- Register in the blueprint block near the bottom of `app.py` (after heavy init) to preserve test determinism.
- Avoid direct mutation of `app.view_functions`; rely on blueprint registration.
- For backward-compatible evolution, add a `*-v2` route and delegate the legacy route.

Testing Impact:

- Previous test-only rebinding fixtures have been removed—the blueprint ensures
  deterministic view function binding.
- Set `UNIT_TEST_MODE=1` (already handled in tests) to bypass heavy audio
  initialization during imports for faster test cycles.

OpenAPI Tagging:

All endpoints are now tagged (`audio`, `export`, `models`, `sequence`, `system`, `util`, `project`, `templates`) to aid grouped documentation views.

Export Task Metadata Enhancements:

`/api/export/video` and `/api/export/retry/<task_id>` now record additional fields:

```
quality_preset, crf, preset, fps, started_at, frame_count, encode_duration_ms
```

These appear in `ExportStatusResponse.task` and in SSE progress payload final state.

Future Candidates:

- Additional export formats (GIF, WebM)
- Cloud storage integration
- Collaborative editing features
- Mobile app companion

Feel free to open a PR if you start modularizing another logical area.

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

## Development

### Error Handling System

Face Sequencer Pro implements a comprehensive centralized error handling system. The system provides:

- **Centralized Logging**: All errors are logged to daily log files in the `logs` directory
- **Standardized API Responses**: Consistent error format for API endpoints
- **Graceful Recovery**: Fall back mechanisms for critical operations
- **User-Friendly Messages**: Clear error messages with recommendations

For detailed information, see [ERROR_HANDLING_GUIDE.md](ERROR_HANDLING_GUIDE.md).
