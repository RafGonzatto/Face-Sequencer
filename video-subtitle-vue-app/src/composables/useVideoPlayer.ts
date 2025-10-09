import { ref, computed } from 'vue';

export function useVideoPlayer(videoRef) {
  const isPlaying = ref(false);
  const currentTime = ref(0);
  const duration = ref(0);
  const volume = ref(1);
  const isMuted = ref(false);

  const togglePlay = () => {
    if (isPlaying.value) {
      pause();
    } else {
      play();
    }
  };

  const play = () => {
    if (videoRef.value) {
      videoRef.value.play();
      isPlaying.value = true;
    }
  };

  const pause = () => {
    if (videoRef.value) {
      videoRef.value.pause();
      isPlaying.value = false;
    }
  };

  const seekTo = (time) => {
    if (videoRef.value) {
      videoRef.value.currentTime = time;
      currentTime.value = time;
    }
  };

  const setVolume = (value) => {
    if (videoRef.value) {
      videoRef.value.volume = value;
      volume.value = value;
      isMuted.value = value === 0;
    }
  };

  const toggleMute = () => {
    if (videoRef.value) {
      isMuted.value = !isMuted.value;
      setVolume(isMuted.value ? 0 : volume.value);
    }
  };

  const updateCurrentTime = () => {
    if (videoRef.value) {
      currentTime.value = videoRef.value.currentTime;
    }
  };

  const updateDuration = () => {
    if (videoRef.value) {
      duration.value = videoRef.value.duration;
    }
  };

  return {
    isPlaying: computed(() => isPlaying.value),
    currentTime: computed(() => currentTime.value),
    duration: computed(() => duration.value),
    volume: computed(() => volume.value),
    isMuted: computed(() => isMuted.value),
    togglePlay,
    play,
    pause,
    seekTo,
    setVolume,
    toggleMute,
    updateCurrentTime,
    updateDuration,
  };
}