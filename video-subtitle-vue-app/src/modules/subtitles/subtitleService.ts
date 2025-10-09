import { ref } from 'vue';
import { Subtitle } from './subtitleTypes';

export class SubtitleService {
  private subtitles: Subtitle[] = ref([]);

  constructor() {
    this.subtitles = [];
  }

  // Fetch subtitles from a given URL
  async fetchSubtitles(url: string): Promise<void> {
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Failed to fetch subtitles');
      }
      const data = await response.json();
      this.subtitles = this.parseSubtitles(data);
    } catch (error) {
      console.error('Error fetching subtitles:', error);
    }
  }

  // Parse the fetched subtitle data
  private parseSubtitles(data: any): Subtitle[] {
    // Implement parsing logic based on the subtitle format
    return data.map((item: any) => ({
      start: item.start,
      end: item.end,
      text: item.text,
    }));
  }

  // Get all subtitles
  getSubtitles(): Subtitle[] {
    return this.subtitles;
  }

  // Clear all subtitles
  clearSubtitles(): void {
    this.subtitles = [];
  }
}