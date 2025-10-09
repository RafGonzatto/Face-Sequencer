import { ref } from 'vue';
import { VideoType } from './videoTypes';

const videoData = ref<VideoType | null>(null);

export const useVideoService = () => {
  const fetchVideoData = async (videoId: string): Promise<void> => {
    try {
      const response = await fetch(`/api/videos/${videoId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch video data');
      }
      videoData.value = await response.json();
    } catch (error) {
      console.error(error);
    }
  };

  const getVideoData = () => {
    return videoData.value;
  };

  return {
    fetchVideoData,
    getVideoData,
  };
};