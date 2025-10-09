import {
  DEFAULT_EDITOR_DURATION,
  DEFAULT_KARAOKE_STATE,
  DEFAULT_LAYER_ANIMATION,
  DEFAULT_LAYER_STYLE,
  nextTrackColor,
} from './editor-constants';
import {
  EditorState,
  HydrateOptions,
  KaraokeState,
  LayerTransformPayload,
  LayerStyle,
  TextLayer,
  TextTrack,
} from './editor-types';

export function createId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

export function cloneStyle(style: LayerStyle): LayerStyle {
  return JSON.parse(JSON.stringify(style));
}

export function cloneKaraoke(karaoke: KaraokeState): KaraokeState {
  return JSON.parse(JSON.stringify(karaoke));
}

export function createTrack(name: string, order: number): TextTrack {
  return {
    id: createId('track'),
    name,
    order,
    layerIds: [],
    collapsed: false,
    color: nextTrackColor(order),
  };
}

export function createLayerFromCue(
  cue: HydrateOptions['cues'][number],
  trackId: string,
  templateStyle?: Partial<LayerStyle>,
  karaokeOverrides?: Partial<KaraokeState>
): TextLayer {
  const start = Math.max(0, cue.start);
  const end = Math.max(start + 0.01, cue.end);
  const style = {
    ...cloneStyle(DEFAULT_LAYER_STYLE),
    ...(templateStyle || {}),
  };

  const karaoke = {
    ...cloneKaraoke(DEFAULT_KARAOKE_STATE),
    ...(karaokeOverrides || {}),
    words: cue.words ? cue.words.map(word => ({ ...word })) : [],
  };

  return {
    id: createId('layer'),
    trackId,
    cueId: cue.id,
    name: cue.text.slice(0, 32) || 'Layer',
    text: cue.text,
    start,
    end,
    rotation: 0,
    scale: 1,
    opacity: 1,
    position: {
      x: 0.5,
      y: 0.72,
      anchorX: 0,
      anchorY: 0,
    },
    style,
    animation: { ...DEFAULT_LAYER_ANIMATION },
    karaoke,
    locked: false,
    visible: true,
    createdAt: Date.now(),
    updatedAt: Date.now(),
  };
}

export function createBaseEditorState(): EditorState {
  return {
    aspectRatio: {
      id: '9:16',
      label: '9:16 Vertical',
      width: 1080,
      height: 1920,
      safeZonePadding: 0.08,
    },
    tracks: {},
    layers: {},
    activeLayerIds: [],
    hoverLayerId: null,
    playback: {
      duration: DEFAULT_EDITOR_DURATION,
      currentTime: 0,
      isPlaying: false,
      playbackRate: 1,
    },
    snapping: true,
    gridVisible: true,
    safeZoneEnabled: true,
    templates: [],
    lastAppliedTemplateId: null,
  };
}

export function applyLayerTransform(
  layer: TextLayer,
  payload: LayerTransformPayload
): TextLayer {
  const updated: TextLayer = {
    ...layer,
    start: payload.start ?? layer.start,
    end: payload.end ?? layer.end,
    scale: payload.scale ?? layer.scale,
    opacity: payload.opacity ?? layer.opacity,
    rotation: payload.rotation ?? layer.rotation,
    text: payload.text ?? layer.text,
    name: payload.name ?? layer.name,
    visible: payload.visible ?? layer.visible,
    updatedAt: Date.now(),
  };

  if (payload.position) {
    updated.position = {
      ...layer.position,
      ...payload.position,
    };
  }

  if (payload.style) {
    updated.style = {
      ...layer.style,
      ...payload.style,
    };
  }

  if (payload.karaoke) {
    updated.karaoke = {
      ...layer.karaoke,
      ...payload.karaoke,
      words: payload.karaoke.words ?? layer.karaoke.words,
    };
  }

  if (payload.animation) {
    updated.animation = {
      ...layer.animation,
      ...payload.animation,
    };
  }

  if (payload.trackId && payload.trackId !== layer.trackId) {
    updated.trackId = payload.trackId;
  }

  return updated;
}

