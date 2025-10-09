export type LayerAnimationKind =
  | 'none'
  | 'pop'
  | 'bounce'
  | 'scale'
  | 'fade'
  | 'typewriter';

export interface AnimationKeyframe {
  time: number; // seconds from layer start
  properties: Partial<{
    opacity: number;
    scale: number;
    translateX: number;
    translateY: number;
    rotate: number;
    skewX: number;
    skewY: number;
  }>;
  easing?: string;
}

export interface LayerAnimation {
  id: string;
  kind: LayerAnimationKind;
  in?: AnimationKeyframe[];
  out?: AnimationKeyframe[];
  loop?: AnimationKeyframe[];
  duration?: number; // optional explicit duration override
}

export interface LayerGradientStop {
  offset: number; // 0..1
  color: string;
}

export interface LayerStyle {
  fontFamily: string;
  fontSize: number;
  fontWeight: string;
  lineHeight: number;
  letterSpacing: number;
  fill: string | LayerGradientStop[];
  strokeColor: string;
  strokeWidth: number;
  shadowColor: string;
  shadowBlur: number;
  shadowOffsetX: number;
  shadowOffsetY: number;
  backgroundColor: string;
  backgroundOpacity: number;
  backgroundPadding: number;
  backgroundRadius: number;
  textAlign: 'left' | 'center' | 'right';
  uppercase: boolean;
  italic: boolean;
  gradientAngle: number;
}

export interface KaraokeWord {
  id: string;
  text: string;
  start: number; // seconds relative to timeline
  end: number; // seconds relative to timeline
}

export interface KaraokeState {
  enabled: boolean;
  highlightColor: string;
  restColor: string;
  outlineColor: string;
  words: KaraokeWord[];
  cursorTime: number; // absolute timeline seconds
}

export interface LayerPosition {
  x: number; // normalized 0..1 relative to canvas width
  y: number; // normalized 0..1 relative to canvas height
  anchorX: number; // -1 left, 0 center, 1 right
  anchorY: number; // -1 top, 0 middle, 1 bottom
}

export interface TextLayer {
  id: string;
  trackId: string;
  cueId?: string;
  name: string;
  text: string;
  start: number;
  end: number;
  rotation: number;
  scale: number;
  opacity: number;
  position: LayerPosition;
  style: LayerStyle;
  animation: LayerAnimation;
  karaoke: KaraokeState;
  locked: boolean;
  visible: boolean;
  templateId?: string;
  createdAt: number;
  updatedAt: number;
}

export interface TextTrack {
  id: string;
  name: string;
  order: number;
  layerIds: string[];
  collapsed: boolean;
  color: string;
}

export interface AspectRatioPreset {
  id: '9:16' | '1:1' | '16:9';
  label: string;
  width: number;
  height: number;
  safeZonePadding: number; // percentage padding from edges
}

export interface EditorTemplate {
  id: string;
  name: string;
  description: string;
  style: Partial<LayerStyle>;
  animation?: Partial<LayerAnimation>;
  karaoke?: Partial<KaraokeState>;
}

export interface LayerTransformPayload {
  layerId: string;
  start?: number;
  end?: number;
  position?: Partial<LayerPosition>;
  opacity?: number;
  scale?: number;
  rotation?: number;
  style?: Partial<LayerStyle>;
  karaoke?: Partial<KaraokeState>;
  animation?: Partial<LayerAnimation>;
  text?: string;
  name?: string;
  trackId?: string;
  visible?: boolean;
}

export interface EditorPlaybackState {
  duration: number;
  currentTime: number;
  isPlaying: boolean;
  playbackRate: number;
}

export interface EditorState {
  aspectRatio: AspectRatioPreset;
  tracks: Record<string, TextTrack>;
  layers: Record<string, TextLayer>;
  activeLayerIds: string[];
  hoverLayerId: string | null;
  playback: EditorPlaybackState;
  snapping: boolean;
  gridVisible: boolean;
  safeZoneEnabled: boolean;
  templates: EditorTemplate[];
  lastAppliedTemplateId: string | null;
}

export type LayerMap = EditorState['layers'];
export type TrackMap = EditorState['tracks'];

export interface HydrateOptions {
  cues: Array<{
    id?: string;
    text: string;
    start: number;
    end: number;
    words?: KaraokeWord[];
  }>;
  templateId?: string;
  trackName?: string;
  baseStyle?: Partial<LayerStyle>;
}

export interface LayerSelectionState {
  primary: string | null;
  order: string[];
}

