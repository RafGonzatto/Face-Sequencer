import { ref } from 'vue';
import { VideoType } from './videoTypes';
import { fetchVideoData } from './videoService';

export const useVideo = () => {
  const video = ref<VideoType | null>(null);
  const loading = ref<boolean>(false);
  const error = ref<string | null>(null);

  const loadVideo = async (videoId: string) => {
    loading.value = true;
    error.value = null;

    try {
      video.value = await fetchVideoData(videoId);
    } catch (err) {
      error.value = 'Failed to load video';
    } finally {
      loading.value = false;
    }
  };

  return {
    video,
    loading,
    error,
    loadVideo,
  };
};