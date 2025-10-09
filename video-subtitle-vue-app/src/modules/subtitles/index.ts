import { ref } from 'vue';
import { SubtitleCue } from './subtitleTypes';
import { fetchSubtitles } from './subtitleService';

export function useSubtitles() {
  const cues = ref<SubtitleCue[]>([]);
  const activeCueIndex = ref<number | null>(null);

  const loadSubtitles = async (url: string) => {
    const fetchedCues = await fetchSubtitles(url);
    cues.value = fetchedCues;
    activeCueIndex.value = null;
  };

  const updateActiveCue = (currentTime: number) => {
    const index = cues.value.findIndex(cue => 
      currentTime >= cue.start && currentTime <= cue.end
    );
    activeCueIndex.value = index !== -1 ? index : null;
  };

  const getActiveCue = () => {
    return activeCueIndex.value !== null ? cues.value[activeCueIndex.value] : null;
  };

  return {
    cues,
    loadSubtitles,
    updateActiveCue,
    getActiveCue,
  };
}