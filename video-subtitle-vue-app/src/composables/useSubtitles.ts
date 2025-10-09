import { computed } from 'vue';
import { useSubtitleStore } from '@/store/subtitleStore';
import type { SubtitleCue as Subtitle } from '@/modules/subtitles/subtitleTypes';

export function useSubtitles() {
  const subtitleStore = useSubtitleStore();
  const subtitles = computed(() => subtitleStore.cues);
  const activeSubtitle = computed(() => subtitleStore.getActiveCue());

  const setSubtitles = (newSubtitles: Subtitle[]) => {
    subtitleStore.setSubtitles(newSubtitles);
  };

  const updateActiveCue = (currentTime: number) => {
    subtitleStore.updateActiveCue(currentTime);
  };

  return {
    subtitles,
    activeSubtitle,
    setSubtitles,
    updateActiveCue,
  };
}
