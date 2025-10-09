import { AspectRatioPreset, EditorTemplate, KaraokeState, LayerAnimation, LayerStyle } from './editor-types';

export const ASPECT_RATIO_PRESETS: AspectRatioPreset[] = [
  { id: '9:16', label: '9:16 Vertical', width: 1080, height: 1920, safeZonePadding: 0.08 },
  { id: '1:1', label: '1:1 Square', width: 1080, height: 1080, safeZonePadding: 0.06 },
  { id: '16:9', label: '16:9 Landscape', width: 1920, height: 1080, safeZonePadding: 0.05 },
];

export const DEFAULT_LAYER_STYLE: LayerStyle = {
  fontFamily: 'Inter, Arial, sans-serif',
  fontSize: 48,
  fontWeight: '700',
  lineHeight: 1.1,
  letterSpacing: 0,
  fill: '#FFFFFF',
  strokeColor: '#000000',
  strokeWidth: 2,
  shadowColor: 'rgba(0,0,0,0.8)',
  shadowBlur: 12,
  shadowOffsetX: 0,
  shadowOffsetY: 4,
  backgroundColor: 'rgba(0,0,0,0.35)',
  backgroundOpacity: 0.75,
  backgroundPadding: 16,
  backgroundRadius: 12,
  textAlign: 'center',
  uppercase: false,
  italic: false,
  gradientAngle: 90,
};

export const DEFAULT_KARAOKE_STATE: KaraokeState = {
  enabled: true,
  highlightColor: '#FFD166',
  restColor: '#FFFFFF',
  outlineColor: 'rgba(0,0,0,0.85)',
  words: [],
  cursorTime: 0,
};

export const DEFAULT_LAYER_ANIMATION: LayerAnimation = {
  id: 'animation-none',
  kind: 'none',
  in: [],
  out: [],
  loop: [],
};

export const BUILT_IN_TEMPLATES: EditorTemplate[] = [
  {
    id: 'capcut-classic',
    name: 'CapCut Classic',
    description: 'Bold white text with dark shadow and pop entrance.',
    style: {
      fontFamily: 'Poppins, Arial, sans-serif',
      fontSize: 52,
      fontWeight: '800',
      strokeWidth: 4,
      shadowBlur: 18,
      shadowOffsetY: 6,
      backgroundOpacity: 0.2,
    },
    animation: {
      id: 'anim-pop',
      kind: 'pop',
    },
  },
  {
    id: 'sunset-gradient',
    name: 'Sunset Gradient',
    description: 'Warm gradient fill with subtle bounce animation.',
    style: {
      fill: [
        { offset: 0, color: '#FF9A9E' },
        { offset: 0.5, color: '#FAD0C4' },
        { offset: 1, color: '#FBC2EB' },
      ],
      strokeColor: 'rgba(0,0,0,0.4)',
      strokeWidth: 1,
      backgroundOpacity: 0,
    },
    animation: {
      id: 'anim-bounce',
      kind: 'bounce',
    },
  },
  {
    id: 'karaoke-neon',
    name: 'Karaoke Neon',
    description: 'Neon outline with karaoke highlight focus.',
    style: {
      fontFamily: 'Montserrat, Arial, sans-serif',
      fontSize: 58,
      strokeColor: '#00F5D4',
      strokeWidth: 6,
      shadowColor: 'rgba(0, 245, 212, 0.4)',
      shadowBlur: 22,
      backgroundOpacity: 0,
    },
    karaoke: {
      highlightColor: '#00F5D4',
      restColor: '#FFFFFF',
    },
    animation: {
      id: 'anim-typewriter',
      kind: 'typewriter',
    },
  },
];

export const DEFAULT_TRACK_COLORS = ['#FF6F61', '#6B5B95', '#88B04B', '#F7CAC9', '#92A8D1'];

export function nextTrackColor(index: number): string {
  return DEFAULT_TRACK_COLORS[index % DEFAULT_TRACK_COLORS.length];
}

export const DEFAULT_EDITOR_DURATION = 120; // seconds fallback

