import { defineStore } from 'pinia';
import { computed } from 'vue';
import {
  ASPECT_RATIO_PRESETS,
  BUILT_IN_TEMPLATES,
  DEFAULT_EDITOR_DURATION,
  DEFAULT_KARAOKE_STATE,
  DEFAULT_LAYER_ANIMATION,
  DEFAULT_LAYER_STYLE,
} from '@/modules/editor/editor-constants';
import {
  EditorState,
  HydrateOptions,
  LayerTransformPayload,
  LayerAnimation,
  LayerStyle,
  TextLayer,
  TextTrack,
} from '@/modules/editor/editor-types';
import {
  applyLayerTransform,
  createBaseEditorState,
  createId,
  createLayerFromCue,
  createTrack,
} from '@/modules/editor/editor-helpers';
import type { SubtitleCue } from '@/modules/subtitles/subtitleTypes';

function findAspectRatio(id: EditorState['aspectRatio']['id']) {
  return ASPECT_RATIO_PRESETS.find(preset => preset.id === id) || ASPECT_RATIO_PRESETS[0];
}

function normalizeTime(value: number) {
  if (Number.isNaN(value)) return 0;
  return Math.max(0, value);
}

export const useEditorStore = defineStore('capcut-editor', {
  state: (): EditorState & {
    selection: {
      primary: string | null;
      order: string[];
    };
    trackOrder: string[];
  } => {
    const base = createBaseEditorState();
    return {
      ...base,
      templates: [...BUILT_IN_TEMPLATES],
      selection: {
        primary: null,
        order: [],
      },
      trackOrder: [],
    };
  },
  getters: {
    orderedTracks(state): TextTrack[] {
      return state.trackOrder
        .map((id: string) => state.tracks[id])
        .filter((t: TextTrack | undefined): t is TextTrack => Boolean(t));
    },
    orderedLayers(state): TextLayer[] {
      const layers = Object.values(state.layers) as TextLayer[];
      return layers.sort((a: TextLayer, b: TextLayer) => a.start - b.start);
    },
    activeLayers(state): TextLayer[] {
      return state.selection.order
        .map((id: string) => state.layers[id])
        .filter((layer): layer is TextLayer => Boolean(layer));
    },
    primaryLayer(): TextLayer | null {
      const primaryId = this.selection.primary;
      return primaryId ? this.layers[primaryId] || null : null;
    },
    aspectRatioSize(state) {
      return {
        width: state.aspectRatio.width,
        height: state.aspectRatio.height,
      };
    },
  },
  actions: {
    setAspectRatio(id: EditorState['aspectRatio']['id']) {
      this.aspectRatio = findAspectRatio(id);
    },
    toggleSafeZone(value?: boolean) {
      this.safeZoneEnabled = value ?? !this.safeZoneEnabled;
    },
    toggleGrid(value?: boolean) {
      this.gridVisible = value ?? !this.gridVisible;
    },
    setSnapping(value: boolean) {
      this.snapping = value;
    },
    ensureTrack(name = 'Text Track 1'): TextTrack {
      if (this.trackOrder.length) {
        const track = this.tracks[this.trackOrder[0]];
        if (track) return track;
      }
      const track = createTrack(name, 0);
      this.tracks[track.id] = track;
      this.trackOrder = [track.id];
      return track;
    },
    addTrack(name?: string) {
      const order = this.trackOrder.length;
      const track = createTrack(name || `Track ${order + 1}`, order);
      this.tracks[track.id] = track;
      this.trackOrder.push(track.id);
      return track.id;
    },
    removeTrack(id: string) {
      const track = this.tracks[id];
      if (!track) return;
      track.layerIds.forEach((layerId: string) => {
        delete this.layers[layerId];
        this.selection.order = this.selection.order.filter((current: string) => current !== layerId);
        if (this.selection.primary === layerId) {
          this.selection.primary = null;
        }
      });
      delete this.tracks[id];
      this.trackOrder = this.trackOrder.filter((trackId: string) => trackId !== id);
    },
    hydrateFromCues(options: HydrateOptions) {
      const baseTrack = this.ensureTrack(options.trackName || 'Text Track 1');
      const template = options.templateId
  ? this.templates.find((item: any) => item.id === options.templateId)
        : null;

      const createdLayers: string[] = [];
      options.cues.forEach((cue, index) => {
        const layer = createLayerFromCue(cue, baseTrack.id, {
          ...DEFAULT_LAYER_STYLE,
          ...(options.baseStyle || {}),
          ...(template?.style || {}),
        }, template?.karaoke);
        if (!layer.name || layer.name.trim().length === 0) {
          layer.name = `Layer ${index + 1}`;
        }
        layer.animation = template?.animation
          ? ({ ...DEFAULT_LAYER_ANIMATION, ...template.animation } as LayerAnimation)
          : { ...DEFAULT_LAYER_ANIMATION };
        layer.karaoke.enabled = layer.karaoke.words.length > 0
          ? layer.karaoke.enabled
          : DEFAULT_KARAOKE_STATE.enabled;
        this.layers[layer.id] = layer;
        baseTrack.layerIds.push(layer.id);
        createdLayers.push(layer.id);
      });
      this.selection.order = createdLayers;
      this.selection.primary = createdLayers[0] || null;
      this.updatePlaybackDurationFromLayers();
    },
    syncLayersFromCues(cues: SubtitleCue[]) {
      const track = this.ensureTrack();
      const existingLayers = track.layerIds.map((id: string) => this.layers[id]).filter(Boolean) as TextLayer[];
      const byCueText = new Map(existingLayers.map((layer: TextLayer) => [layer.text, layer]));
      const created: string[] = [];
      cues.forEach((cue, index) => {
        const match = byCueText.get(cue.text);
        if (match) {
          this.layers[match.id] = {
            ...match,
            start: cue.start,
            end: cue.end,
            updatedAt: Date.now(),
          };
          created.push(match.id);
        } else {
          const layer = createLayerFromCue(
            { ...cue, id: cue.text.slice(0, 32) || undefined },
            track.id
          );
          this.layers[layer.id] = layer;
          track.layerIds.splice(index, 0, layer.id);
          created.push(layer.id);
        }
      });
      // Remove layers that no longer have cues
      const toRemove = track.layerIds.filter((id: string) => !created.includes(id));
      toRemove.forEach((id: string) => {
        delete this.layers[id];
      });
      track.layerIds = track.layerIds.filter((id: string) => created.includes(id));
      this.selection.order = created;
      this.selection.primary = created[0] || null;
      this.updatePlaybackDurationFromLayers();
    },
    updateLayer(payload: LayerTransformPayload) {
      const layer = this.layers[payload.layerId];
      if (!layer) return;
      const updated = applyLayerTransform(layer, payload);
      this.layers[layer.id] = updated;
      if (payload.trackId && payload.trackId !== layer.trackId) {
        const previousTrack = this.tracks[layer.trackId];
        const nextTrack = this.tracks[payload.trackId];
        if (previousTrack) {
          previousTrack.layerIds = previousTrack.layerIds.filter((id: string) => id !== layer.id);
        }
        if (nextTrack) {
          nextTrack.layerIds.push(layer.id);
        }
      }
      this.updatePlaybackDurationFromLayers();
    },
    reorderLayer(layerId: string, targetIndex: number, trackId?: string) {
      const currentLayer = this.layers[layerId];
      if (!currentLayer) return;
      const sourceTrack = this.tracks[currentLayer.trackId];
      if (!sourceTrack) return;
      sourceTrack.layerIds = sourceTrack.layerIds.filter((id: string) => id !== layerId);
      const destinationTrackId = trackId || currentLayer.trackId;
      const destinationTrack = this.tracks[destinationTrackId];
      if (!destinationTrack) return;
      destinationTrack.layerIds.splice(Math.max(0, targetIndex), 0, layerId);
      this.layers[layerId].trackId = destinationTrack.id;
    },
    reorderTrack(trackId: string, targetIndex: number) {
      const currentIndex = this.trackOrder.indexOf(trackId);
      if (currentIndex === -1) return;
      const clampedIndex = Math.max(0, Math.min(targetIndex, this.trackOrder.length - 1));
      if (currentIndex === clampedIndex) return;
      this.trackOrder = this.trackOrder.filter(id => id !== trackId);
      this.trackOrder.splice(clampedIndex, 0, trackId);
      // update track.order metadata
      this.trackOrder.forEach((id, idx) => {
        const track = this.tracks[id];
        if (track) track.order = idx;
      });
    },
    deleteLayer(layerId: string) {
      const layer = this.layers[layerId];
      if (!layer) return;
      const track = this.tracks[layer.trackId];
      if (track) {
        track.layerIds = track.layerIds.filter(id => id !== layerId);
      }
      delete this.layers[layerId];
      this.selection.order = this.selection.order.filter(id => id !== layerId);
      if (this.selection.primary === layerId) {
        this.selection.primary = this.selection.order[0] || null;
      }
      this.updatePlaybackDurationFromLayers();
    },
    duplicateLayer(layerId: string) {
      const base = this.layers[layerId];
      if (!base) return;
      const cloneId = createId('layer');
      const cloned: TextLayer = {
        ...JSON.parse(JSON.stringify(base)),
        id: cloneId,
        name: `${base.name} Copy`,
        start: base.start + 0.25,
        end: base.end + 0.25,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      this.layers[cloneId] = cloned;
      const track = this.tracks[base.trackId];
      if (track) {
        const index = track.layerIds.indexOf(layerId);
        track.layerIds.splice(index + 1, 0, cloneId);
      }
      this.selection.order = [cloneId];
      this.selection.primary = cloneId;
      this.updatePlaybackDurationFromLayers();
    },
    selectLayers(layerIds: string[], primaryId?: string) {
      this.selection.order = layerIds;
      this.selection.primary = primaryId ?? layerIds[0] ?? null;
    },
    clearSelection() {
      this.selection.primary = null;
      this.selection.order = [];
    },
    setPlaybackTime(time: number) {
      this.playback.currentTime = Math.min(
        Math.max(0, time),
        this.playback.duration
      );
      if (this.playback.currentTime !== time) {
        this.playback.currentTime = normalizeTime(time);
      }
    },
    setPlaybackDuration(duration: number) {
      this.playback.duration = Math.max(duration, 0);
    },
    updatePlaybackDurationFromLayers() {
      const maxEnd = Math.max(
        ...Object.values(this.layers).map(layer => layer.end),
        DEFAULT_EDITOR_DURATION
      );
      this.playback.duration = Math.max(maxEnd, this.playback.duration);
    },
    setPlaybackState(isPlaying: boolean) {
      this.playback.isPlaying = isPlaying;
    },
    updatePlaybackRate(value: number) {
      this.playback.playbackRate = Math.max(0.25, Math.min(3, value));
    },
    updateTemplates(templates: typeof BUILT_IN_TEMPLATES) {
      this.templates = templates;
    },
    applyTemplateToLayer(layerId: string, templateId: string) {
      const layer = this.layers[layerId];
      if (!layer) return;
      const template = this.templates.find(item => item.id === templateId);
      if (!template) return;
      const nextStyle: LayerStyle = {
        ...layer.style,
        ...(template.style || {}),
      };
      const nextAnimation: LayerAnimation = {
        ...layer.animation,
        ...(template.animation || {}),
      };
      const karaoke = template.karaoke
        ? {
            ...layer.karaoke,
            ...template.karaoke,
          }
        : layer.karaoke;
      this.layers[layerId] = {
        ...layer,
        style: nextStyle,
        animation: nextAnimation,
        karaoke,
        templateId,
        updatedAt: Date.now(),
      };
      this.lastAppliedTemplateId = templateId;
    },
    updateLayerWords(layerId: string, words: TextLayer['karaoke']['words']) {
      const layer = this.layers[layerId];
      if (!layer) return;
      this.layers[layerId] = {
        ...layer,
        karaoke: {
          ...layer.karaoke,
          words: words.map(word => ({ ...word })),
        },
        updatedAt: Date.now(),
      };
    },
    setHoverLayer(layerId: string | null) {
      this.hoverLayerId = layerId;
    },
    reset() {
      const base = createBaseEditorState();
      this.aspectRatio = base.aspectRatio;
      this.tracks = {};
      this.layers = {};
      this.selection = { primary: null, order: [] };
      this.playback = base.playback;
      this.trackOrder = [];
    },
  },
});
