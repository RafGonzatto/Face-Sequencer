// src/modules/video/videoTypes.ts

export interface Video {
  id: string;
  title: string;
  description: string;
  url: string;
  duration: number; // in seconds
  thumbnail: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface VideoState {
  currentVideo: Video | null;
  isPlaying: boolean;
  volume: number; // range from 0 to 1
  playbackRate: number; // e.g., 1 for normal speed
  currentTime: number; // in seconds
}