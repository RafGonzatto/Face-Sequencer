import { defineStore } from 'pinia';
import { ref } from 'vue';
import { SubtitleCue } from '../modules/subtitles/subtitleTypes';

export const useSubtitleStore = defineStore('subtitle', () => {
  const cues = ref<SubtitleCue[]>([]);
  const activeCueIndex = ref<number | null>(null);

  function setSubtitles(newCues: SubtitleCue[]) {
    cues.value = newCues;
    activeCueIndex.value = null;
  }

  function updateActiveCue(currentTime: number) {
    const index = cues.value.findIndex(cue => currentTime >= cue.start && currentTime <= cue.end);
    activeCueIndex.value = index !== -1 ? index : null;
  }

  function getActiveCue() {
    return activeCueIndex.value !== null ? cues.value[activeCueIndex.value] : null;
  }

  return {
    cues,
    activeCueIndex,
    setSubtitles,
    updateActiveCue,
    getActiveCue,
  };
});