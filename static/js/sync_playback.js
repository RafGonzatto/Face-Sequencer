// Synchronized audio and animation playback for Face Sequencer Pro
// This extension adds synced playback functionality to the main app

// We extend the FaceSequencerApp prototype with the sync playback methods
// These methods will be available to the main application after it loads

FaceSequencerApp.prototype.initSyncPlayback = function() {
  // Initialize sync playback UI elements
  this.syncPlaybackBtn = document.getElementById("syncPlaybackBtn");
  
  // Bind event listeners
  if (this.syncPlaybackBtn) {
    this.syncPlaybackBtn.addEventListener("click", () => {
      this.toggleSyncPlayback();
    });
  }
  
  // Initialize sync state
  this.state.syncPlaybackActive = false;
  this.state.currentAudioTime = 0;
  this.state.syncAnimationFrameTimer = null;
};

FaceSequencerApp.prototype.toggleSyncPlayback = function() {
  if (this.state.syncPlaybackActive) {
    this.stopSyncPlayback();
  } else {
    this.startSyncPlayback();
  }
};

FaceSequencerApp.prototype.startSyncPlayback = function() {
  // Check if audio and sequence are available
  if (!this.audioManager || !this.audioManager.wavesurfer || !this.state.sequence || this.state.sequence.length === 0) {
    this.showError("No audio or sequence available for synchronized playback");
    return;
  }
  
  // Stop any existing playback
  this.stopSequence();
  
  // Set the state
  this.state.syncPlaybackActive = true;
  
  // Update UI
  this.syncPlaybackBtn.classList.add("sync-active");
  this.syncPlaybackBtn.innerHTML = '<i class="fas fa-pause"></i> Stop Sync Playback';
  
  // Start audio playback
  this.audioManager.wavesurfer.play();
  
  // Set up a handler for audio timeupdate to sync with animation frames
  this.audioManager.wavesurfer.on('audioprocess', (currentTime) => {
    this.updateAnimationForAudioTime(currentTime * 1000); // Convert to ms
  });
  
  // Handle audio playback end
  this.audioManager.wavesurfer.on('finish', () => {
    this.stopSyncPlayback();
  });
};

FaceSequencerApp.prototype.stopSyncPlayback = function() {
  if (!this.state.syncPlaybackActive) return;
  
  // Update state
  this.state.syncPlaybackActive = false;
  
  // Stop audio
  if (this.audioManager && this.audioManager.wavesurfer) {
    this.audioManager.wavesurfer.pause();
    // Remove the event listeners
    this.audioManager.wavesurfer.un('audioprocess');
    this.audioManager.wavesurfer.un('finish');
  }
  
  // Reset UI
  this.syncPlaybackBtn.classList.remove("sync-active");
  this.syncPlaybackBtn.innerHTML = '<i class="fas fa-film"></i> <i class="fas fa-music"></i> Play Audio + Animation';
  
  // Clear any active frame timer
  if (this.state.syncAnimationFrameTimer) {
    clearTimeout(this.state.syncAnimationFrameTimer);
    this.state.syncAnimationFrameTimer = null;
  }
};

FaceSequencerApp.prototype.updateAnimationForAudioTime = function(timeMs) {
  // Find the frame that corresponds to the current audio time
  let cumulativeTime = 0;
  let targetFrameIndex = -1;
  
  // Iterate through frames to find the one that corresponds to the current audio time
  for (let i = 0; i < this.state.sequence.length; i++) {
    const frame = this.state.sequence[i];
    const frameDuration = frame.ms || frame.duration;
    
    // If we have audio_start and audio_end, use those for precise timing
    if (frame.audio_start !== undefined && frame.audio_end !== undefined) {
      if (timeMs >= frame.audio_start && timeMs < frame.audio_end) {
        targetFrameIndex = i;
        break;
      }
    } else {
      // Otherwise use the cumulative frame durations
      cumulativeTime += frameDuration;
      if (cumulativeTime > timeMs) {
        targetFrameIndex = i;
        break;
      }
    }
  }
  
  // If we found a valid frame, show it
  if (targetFrameIndex >= 0 && targetFrameIndex < this.state.sequence.length) {
    // Only update the frame if it's different from the current one
    if (targetFrameIndex !== this.state.currentFrame) {
      this.selectFrame(targetFrameIndex);
      this.loadFramePreview(targetFrameIndex);
    }
  }
};