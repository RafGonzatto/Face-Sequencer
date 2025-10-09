// This file contains global TypeScript declarations for the video subtitle application. 
// You can define types, interfaces, and other global declarations here.

declare global {
  interface Window {
    initVideoUI: () => void;
    setSubtitles: (cues: Array<{ start: number; end: number; text: string }>) => void;
    setStyle: (styleJson: Record<string, any>) => void;
    getStyle: () => Record<string, any>;
    resizeOverlay: () => void;
  }

  type SubtitleCue = {
    start: number;
    end: number;
    text: string;
  };

  type VideoPlaybackState = {
    paused: boolean;
    ended: boolean;
    currentTime: number;
    duration: number;
    volume: number;
    muted: boolean;
    playbackRate: number;
    isFullscreen: boolean;
  };
}

export {};