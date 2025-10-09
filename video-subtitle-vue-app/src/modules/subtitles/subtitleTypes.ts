// src/modules/subtitles/subtitleTypes.ts

export interface SubtitleCue {
  start: number; // Start time in seconds
  end: number;   // End time in seconds
  text: string;  // Subtitle text
}

export interface SubtitleTrack {
  language: string; // Language of the subtitles
  cues: SubtitleCue[]; // Array of subtitle cues
}

export type SubtitleFormat = 'srt' | 'vtt' | 'ass'; // Supported subtitle formats

export interface SubtitleOptions {
  format: SubtitleFormat; // Format of the subtitle file
  defaultLanguage?: string; // Default language for subtitles
}