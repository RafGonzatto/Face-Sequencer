import { ref, onMounted, onBeforeUnmount } from 'vue';

export function useKeyboardShortcuts(videoPlayer) {
  const isPlaying = ref(false);

  const handleKeydown = (event) => {
    switch (event.key) {
      case ' ':
      case 'Spacebar':
        event.preventDefault();
        togglePlay();
        break;
      case 'ArrowRight':
        event.preventDefault();
        seekRelative(5); // Seek forward 5 seconds
        break;
      case 'ArrowLeft':
        event.preventDefault();
        seekRelative(-5); // Seek backward 5 seconds
        break;
      case 'ArrowUp':
        event.preventDefault();
        adjustVolume(0.1); // Increase volume
        break;
      case 'ArrowDown':
        event.preventDefault();
        adjustVolume(-0.1); // Decrease volume
        break;
      case 'f':
      case 'F':
        event.preventDefault();
        toggleFullscreen();
        break;
      case 'm':
      case 'M':
        event.preventDefault();
        toggleMute();
        break;
      default:
        break;
    }
  };

  const togglePlay = () => {
    if (videoPlayer.value) {
      if (isPlaying.value) {
        videoPlayer.value.pause();
      } else {
        videoPlayer.value.play();
      }
      isPlaying.value = !isPlaying.value;
    }
  };

  const seekRelative = (delta) => {
    if (videoPlayer.value) {
      videoPlayer.value.currentTime = Math.max(0, videoPlayer.value.currentTime + delta);
    }
  };

  const adjustVolume = (delta) => {
    if (videoPlayer.value) {
      videoPlayer.value.volume = Math.min(1, Math.max(0, videoPlayer.value.volume + delta));
    }
  };

  const toggleFullscreen = () => {
    if (videoPlayer.value) {
      if (!document.fullscreenElement) {
        videoPlayer.value.requestFullscreen();
      } else {
        document.exitFullscreen();
      }
    }
  };

  const toggleMute = () => {
    if (videoPlayer.value) {
      videoPlayer.value.muted = !videoPlayer.value.muted;
    }
  };

  onMounted(() => {
    document.addEventListener('keydown', handleKeydown);
  });

  onBeforeUnmount(() => {
    document.removeEventListener('keydown', handleKeydown);
  });

  return {
    isPlaying,
  };
}