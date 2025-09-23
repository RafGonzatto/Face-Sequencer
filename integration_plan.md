# integration_plan.md - Audio-Driven Animation Integration

## Overview

Plan to integrate audio-driven timing into the existing Face Sequencer Pro system, maintaining compatibility with current character mapping while adding sophisticated audio synchronization.

## Phase 1: Backend Integration (2-3 days)

### 1.1 Add Audio Processing Dependencies

```bash
pip install whisperx webrtcvad librosa torch torchaudio
```

### 1.2 Extend Flask API (app.py)

#### New Endpoints:

```python
@app.route('/api/audio/upload', methods=['POST'])
def upload_audio():
    """Upload and store audio file for alignment"""

@app.route('/api/audio/align', methods=['POST'])
def align_audio():
    """Align uploaded audio with project text"""

@app.route('/api/audio/preview/<task_id>', methods=['GET'])
def preview_alignment():
    """Get alignment preview before applying to project"""

@app.route('/api/sequence/build-from-audio', methods=['POST'])
def build_sequence_from_audio():
    """Build animation sequence using audio timing"""
```

#### Modified Project Schema:

```python
# Extend existing project structure
project_schema = {
    # ... existing fields ...
    "audio_file": Optional[str],           # Path to uploaded audio
    "audio_alignment": Optional[Dict],     # AlignmentResult data
    "timing_mode": str,                    # "manual" | "audio_driven"
    "audio_settings": {
        "language": "pt-BR",               # pt-BR | en-US
        "granularity": "word",             # word | phoneme
        "min_confidence": 0.5,             # Alignment threshold
        "pause_min_ms": 80                 # Minimum pause duration
    }
}
```

### 1.3 Audio Processing Integration

#### Modified lipanim_core.py:

```python
def build_sequence_from_audio(alignment_result, letter_map, fallback=None):
    """Build sequence using audio alignment timing"""
    seq = []

    for token in alignment_result.tokens:
        if token.type == "gap":
            # Add pause frame with exact audio timing
            seq.append({
                "char": " ",
                "img": None,
                "ms": token.end_ms - token.start_ms,
                "audio_sync": True,
                "confidence": token.confidence
            })
        else:
            # Add character frame with audio timing
            for char in token.text:
                key = char.upper()
                img = letter_map.get(key) or fallback
                if img:
                    seq.append({
                        "char": char,
                        "img": img,
                        "ms": (token.end_ms - token.start_ms) / len(token.text),
                        "audio_sync": True,
                        "confidence": token.confidence,
                        "viseme": token.viseme
                    })

    return seq
```

## Phase 2: Frontend Integration (3-4 days)

### 2.1 Audio Upload Component (HTML)

```html
<!-- Add to templates/index.html in Configuration panel -->
<div class="section audio-section" id="audioSection" style="display: none;">
  <h3>🎵 Audio Timing</h3>
  <p class="help-text">Upload narração para sincronizar automaticamente</p>

  <div class="audio-controls">
    <input
      type="file"
      id="audioInput"
      accept="audio/*"
      style="display: none;"
    />
    <button class="btn btn-outline btn-sm" id="uploadAudioBtn">
      <i class="fas fa-microphone"></i> Upload Audio
    </button>
    <button
      class="btn btn-outline btn-sm"
      id="clearAudioBtn"
      style="display: none;"
    >
      <i class="fas fa-trash"></i> Clear
    </button>
  </div>

  <div class="audio-preview" id="audioPreview" style="display: none;">
    <audio controls id="audioPlayer" style="width: 100%;">
      Your browser does not support the audio element.
    </audio>
    <div class="audio-info">
      <span id="audioDuration">--:--</span> |
      <span id="audioLanguage">--</span>
    </div>
  </div>

  <div class="audio-settings">
    <label>
      Language:
      <select id="audioLanguage">
        <option value="pt-BR" selected>Português (BR)</option>
        <option value="en-US">English (US)</option>
      </select>
    </label>

    <label>
      Granularity:
      <select id="audioGranularity">
        <option value="word" selected>Word-level</option>
        <option value="phoneme">Phoneme-level</option>
      </select>
    </label>
  </div>

  <button
    class="btn btn-primary btn-sm"
    id="alignAudioBtn"
    style="display: none;"
  >
    <i class="fas fa-sync"></i> Align with Text
  </button>
</div>

<!-- Timing Mode Toggle -->
<div class="section">
  <h3>⏱️ Timing Mode</h3>
  <div class="timing-mode-toggle">
    <label class="toggle-option">
      <input type="radio" name="timingMode" value="manual" checked />
      <span>Manual Timing</span>
    </label>
    <label class="toggle-option">
      <input type="radio" name="timingMode" value="audio_driven" />
      <span>Audio-Driven</span>
    </label>
  </div>
</div>
```

### 2.2 Timeline Enhancement (CSS)

```css
/* Audio timeline styles */
.timeline-audio-track {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.audio-waveform {
  height: 60px;
  background: linear-gradient(
    90deg,
    var(--primary-color-alpha) 0%,
    var(--primary-color) 50%,
    var(--primary-color-alpha) 100%
  );
  border-radius: var(--radius-xs);
  position: relative;
}

.timeline-frame.audio-synced {
  border-left: 3px solid var(--success-color);
  box-shadow: 0 0 0 1px var(--success-color-alpha);
}

.timeline-frame.low-confidence {
  border-left: 3px solid var(--warning-color);
  opacity: 0.8;
}

.audio-controls {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.timing-mode-toggle {
  display: flex;
  gap: var(--spacing-md);
  background: var(--bg-tertiary);
  padding: var(--spacing-xs);
  border-radius: var(--radius-md);
}

.toggle-option {
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s ease;
}

.toggle-option:has(input[type="radio"]:checked) {
  background: var(--primary-color);
  color: var(--text-inverse);
}

.toggle-option input[type="radio"] {
  display: none;
}
```

### 2.3 JavaScript Audio Integration (app.js)

```javascript
// Add to FaceSequencerApp class

initializeAudioComponents() {
  this.audioInput = document.getElementById('audioInput');
  this.uploadAudioBtn = document.getElementById('uploadAudioBtn');
  this.clearAudioBtn = document.getElementById('clearAudioBtn');
  this.audioPreview = document.getElementById('audioPreview');
  this.audioPlayer = document.getElementById('audioPlayer');
  this.alignAudioBtn = document.getElementById('alignAudioBtn');
  this.timingModeRadios = document.querySelectorAll('input[name="timingMode"]');

  // Event listeners
  this.uploadAudioBtn.addEventListener('click', () => {
    this.audioInput.click();
  });

  this.audioInput.addEventListener('change', (e) => {
    this.handleAudioUpload(e.target.files[0]);
  });

  this.alignAudioBtn.addEventListener('click', () => {
    this.alignAudioWithText();
  });

  this.timingModeRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      this.handleTimingModeChange(radio.value);
    });
  });
}

async handleAudioUpload(file) {
  if (!file) return;

  try {
    // Upload audio file
    const formData = new FormData();
    formData.append('audio', file);
    formData.append('language', this.getSelectedLanguage());

    const response = await this.apiCall('audio/upload', 'POST', formData);

    if (response.success) {
      this.state.project.audio_file = response.audio_path;
      this.showAudioPreview(file);
      this.alignAudioBtn.style.display = 'block';
      this.showSuccess('Áudio carregado! Clique "Align with Text" para sincronizar.');
    }
  } catch (error) {
    this.showError('Erro ao carregar áudio: ' + error.message);
  }
}

async alignAudioWithText() {
  if (!this.state.project.text) {
    this.showError('Digite o texto antes de alinhar com o áudio');
    return;
  }

  try {
    this.showStatus('Alinhando áudio com texto... (pode levar alguns minutos)');

    const alignmentData = {
      audio_file: this.state.project.audio_file,
      text: this.state.project.text,
      language: this.getSelectedLanguage(),
      granularity: this.getSelectedGranularity()
    };

    const response = await this.apiCall('audio/align', 'POST', alignmentData);

    if (response.success) {
      this.state.project.audio_alignment = response.alignment;
      this.state.project.timing_mode = 'audio_driven';

      // Switch to audio-driven mode
      document.querySelector('input[name="timingMode"][value="audio_driven"]').checked = true;
      this.handleTimingModeChange('audio_driven');

      this.showSuccess(`Alinhamento concluído! ${response.alignment.stats.avg_confidence * 100:.1f}% confiança média`);
      this.updateTimelineWithAudio();
    }
  } catch (error) {
    this.showError('Erro no alinhamento: ' + error.message);
  }
}

handleTimingModeChange(mode) {
  const audioSection = document.getElementById('audioSection');
  const manualSettings = document.querySelector('.animation-settings');

  if (mode === 'audio_driven') {
    audioSection.style.display = 'block';
    manualSettings.style.opacity = '0.5';
    manualSettings.style.pointerEvents = 'none';

    // Use audio timing if available
    if (this.state.project.audio_alignment) {
      this.buildSequenceFromAudio();
    }
  } else {
    audioSection.style.display = 'none';
    manualSettings.style.opacity = '1';
    manualSettings.style.pointerEvents = 'auto';
  }

  this.state.project.timing_mode = mode;
}

async buildSequenceFromAudio() {
  if (!this.state.project.audio_alignment) {
    this.showError('Nenhum alinhamento de áudio disponível');
    return;
  }

  try {
    const response = await this.apiCall('sequence/build-from-audio', 'POST', {
      alignment: this.state.project.audio_alignment,
      letter_map: this.state.project.letter_map,
      fallback_image: this.state.project.fallback_image
    });

    if (response.success) {
      this.state.sequence = response.sequence;
      this.updateTimeline();
      this.showSuccess(`Sequência gerada com timing de áudio: ${response.sequence.length} frames`);
    }
  } catch (error) {
    this.showError('Erro ao gerar sequência: ' + error.message);
  }
}

updateTimelineWithAudio() {
  // Enhance timeline to show audio sync indicators
  this.state.sequence.forEach((frame, index) => {
    const frameElement = document.querySelector(`[data-frame-index="${index}"]`);
    if (frameElement) {
      if (frame.audio_sync) {
        frameElement.classList.add('audio-synced');

        if (frame.confidence < 0.7) {
          frameElement.classList.add('low-confidence');
        }
      }
    }
  });
}
```

## Phase 3: Testing & Validation (1 day)

### 3.1 Test Cases

```python
# test_audio_alignment.py

def test_portuguese_sample():
    """Test with Portuguese audio and text"""
    aligner = AudioAligner(language="pt-BR")

    text = "Olá, como você está hoje? Este é um teste de alinhamento."
    # result = aligner.align_audio_to_text("samples/portuguese.wav", text)

    # Validate results
    # assert result.stats.avg_confidence > 0.8
    # assert result.stats.drift_ms < 50
    # assert len(result.tokens) > 0

def test_english_sample():
    """Test with English audio and text"""
    aligner = AudioAligner(language="en-US")

    text = "Hello, how are you today? This is an alignment test."
    # result = aligner.align_audio_to_text("samples/english.wav", text)

def test_mixed_content():
    """Test with Portuguese text containing English words"""
    text = "Vamos fazer o download do software agora."
    # Should handle code-switching gracefully
```

### 3.2 Integration Tests

- Upload audio through web interface
- Verify alignment quality indicators
- Test timeline synchronization
- Validate export functionality

## Phase 4: Documentation & Polish (1 day)

### 4.1 User Guide Updates

- Add audio upload instructions
- Explain timing modes
- Troubleshooting guide for alignment issues

### 4.2 Performance Optimization

- Cache alignment models
- Implement background processing for long audio
- Add progress indicators

## Installation Requirements

```bash
# Core audio processing
pip install whisperx>=3.1.0
pip install webrtcvad>=2.0.10
pip install librosa>=0.10.0

# PyTorch (CPU or GPU)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# Optional: GPU acceleration
# pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## Expected Benefits

1. **Precision**: Sub-second timing accuracy vs manual approximation
2. **Efficiency**: Automated timing vs manual frame-by-frame adjustment
3. **Quality**: Professional lip-sync vs basic approximation
4. **Language Support**: Native Portuguese handling with English fallback
5. **Scalability**: Batch processing capability for multiple projects

## Risk Mitigation

1. **Alignment Failures**: Fallback to energy-based segmentation
2. **Poor Audio Quality**: Preprocessing with denoising and normalization
3. **Language Detection**: Explicit language parameter with validation
4. **Performance**: Chunked processing for long audio files
5. **Compatibility**: Maintain existing manual timing as default mode

This integration plan maintains backward compatibility while adding sophisticated audio-driven capabilities specifically optimized for Portuguese content.
