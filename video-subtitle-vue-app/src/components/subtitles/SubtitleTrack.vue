<template>
  <div class="subtitle-track" :data-track-id="track.id" :data-track-order="track.order">
    <div class="track-header" :style="{ borderColor: track.color }" @pointerdown="onTrackHeaderPointerDown">
      <span class="name">{{ track.name }}</span>
      <span class="meta">{{ track.layerIds.length }} layers</span>
    </div>
    <div ref="laneRef" class="track-lane">
      <div
        v-for="layerId in track.layerIds"
        :key="layerId"
        v-if="layers[layerId]"
        class="clip"
        :class="{ active: activeLayerIds.includes(layerId) }"
        :style="getClipStyle(layers[layerId])"
        @pointerdown="onClipPointerDown($event, layers[layerId])"
      >
        <div class="handle start" @pointerdown.stop="onHandlePointerDown($event, layers[layerId], 'trim-start')"></div>
        <span class="clip-name">{{ layers[layerId].name }}</span>
        <div class="handle end" @pointerdown.stop="onHandlePointerDown($event, layers[layerId], 'trim-end')"></div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
// @ts-nocheck
import { defineComponent, onBeforeUnmount, PropType, ref } from 'vue';
import type { TextLayer, TextTrack } from '@/modules/editor/editor-types';

interface DragState {
  active: boolean;
  mode: 'move' | 'trim-start' | 'trim-end';
  layerId: string;
  startTime: number;
  endTime: number;
  pointerStartX: number;
  originalStart: number;
  originalEnd: number;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

export default defineComponent({
  name: 'SubtitleTrack',
  props: {
    track: {
      type: Object as PropType<TextTrack>,
      required: true,
    },
    layers: {
      type: Object as PropType<Record<string, TextLayer>>,
      required: true,
    },
    duration: {
      type: Number,
      required: true,
    },
    pixelsPerSecond: {
      type: Number,
      required: true,
    },
    activeLayerIds: {
      type: Array as PropType<string[]>,
      default: () => [],
    },
    scrollLeft: {
      type: Number,
      default: 0,
    },
    snapping: {
      type: Boolean,
      default: true,
    },
    snapInterval: {
      type: Number,
      default: 0.05,
    },
  },
  emits: ['select-layer', 'update-layer', 'reorder-layer', 'reorder-track'],
  setup(props, { emit }) {
    const laneRef = ref<HTMLDivElement | null>(null);
    const dragState = ref<DragState>({
      active: false,
      mode: 'move',
      layerId: '',
      startTime: 0,
      endTime: 0,
      pointerStartX: 0,
      originalStart: 0,
      originalEnd: 0,
    });
    const trackDrag = ref<{ active: boolean; trackId: string; startY: number }>({
      active: false,
      trackId: '',
      startY: 0,
    });

    function toPixels(seconds: number) {
      return seconds * props.pixelsPerSecond;
    }

    function roundToGrid(seconds: number) {
      if (!props.snapping) return seconds;
      const grid = props.snapInterval || 0.05;
      return Math.round(seconds / grid) * grid;
    }

    function getClipStyle(layer: TextLayer) {
      const left = toPixels(layer.start);
      const width = Math.max(toPixels(layer.end - layer.start), 32);
      return {
        left: `${left}px`,
        width: `${width}px`,
        borderColor: layer.templateId ? 'rgba(0, 173, 255, 0.6)' : 'rgba(255,255,255,0.15)',
      };
    }

    function captureDragState(event: PointerEvent, layer: TextLayer, mode: DragState['mode']) {
      dragState.value = {
        active: true,
        mode,
        layerId: layer.id,
        startTime: layer.start,
        endTime: layer.end,
        pointerStartX: event.clientX,
        originalStart: layer.start,
        originalEnd: layer.end,
      };
      window.addEventListener('pointermove', onPointerMove);
      window.addEventListener('pointerup', onPointerUp, { once: true });
    }

    function onClipPointerDown(event: PointerEvent, layer: TextLayer) {
      event.preventDefault();
      emit('select-layer', layer.id);
      captureDragState(event, layer, 'move');
    }

    function onHandlePointerDown(event: PointerEvent, layer: TextLayer, mode: DragState['mode']) {
      event.preventDefault();
      emit('select-layer', layer.id);
      captureDragState(event, layer, mode);
    }

    function computePointerDelta(event: PointerEvent) {
      const lane = laneRef.value;
      if (!lane) return 0;
      const rect = lane.getBoundingClientRect();
      const x = event.clientX - rect.left + props.scrollLeft;
      const dx = x - (dragState.value.pointerStartX - rect.left + props.scrollLeft);
      return dx / props.pixelsPerSecond;
    }

    function onPointerMove(event: PointerEvent) {
      if (!dragState.value.active) return;
      const delta = computePointerDelta(event);
      const minDuration = 0.15;
      let newStart = dragState.value.originalStart;
      let newEnd = dragState.value.originalEnd;

      if (dragState.value.mode === 'move') {
        newStart = roundToGrid(clamp(dragState.value.originalStart + delta, 0, props.duration - minDuration));
        const layerDuration = dragState.value.originalEnd - dragState.value.originalStart;
        newEnd = clamp(newStart + layerDuration, newStart + minDuration, props.duration);
      } else if (dragState.value.mode === 'trim-start') {
        newStart = roundToGrid(clamp(dragState.value.originalStart + delta, 0, dragState.value.originalEnd - minDuration));
      } else if (dragState.value.mode === 'trim-end') {
        newEnd = roundToGrid(clamp(dragState.value.originalEnd + delta, dragState.value.originalStart + minDuration, props.duration));
      }

      dragState.value.startTime = newStart;
      dragState.value.endTime = newEnd;
      emit('update-layer', {
        layerId: dragState.value.layerId,
        start: newStart,
        end: newEnd,
      });
    }

    function onPointerUp(event?: PointerEvent) {
      dragState.value.active = false;
      window.removeEventListener('pointermove', onPointerMove);
      // Determine vertical reorder target if moving
      if (event && dragState.value.layerId && dragState.value.mode === 'move') {
        const layer = props.layers[dragState.value.layerId];
        if (layer) {
          const trackElements = Array.from(document.querySelectorAll('.subtitle-track')) as HTMLElement[];
          const target = trackElements.find(el => {
            const rect = el.getBoundingClientRect();
            return event.clientY >= rect.top && event.clientY <= rect.bottom;
          });
            const targetTrackId = target?.dataset.trackId;
          if (targetTrackId && targetTrackId !== layer.trackId) {
            emit('reorder-layer', {
              layerId: layer.id,
              targetTrackId,
              targetIndex: -1, // append
            });
          }
        }
      }
      if (event && trackDrag.value.active) {
        const trackElements = Array.from(document.querySelectorAll('.subtitle-track')) as HTMLElement[];
        const target = trackElements.find(el => {
          const rect = el.getBoundingClientRect();
          return event.clientY >= rect.top && event.clientY <= rect.bottom;
        });
        const targetTrackId = target?.dataset.trackId;
        if (targetTrackId && targetTrackId !== trackDrag.value.trackId) {
          const targetIndex = trackElements.findIndex(el => el.dataset.trackId === targetTrackId);
          emit('reorder-track', { trackId: trackDrag.value.trackId, targetIndex });
        }
      }
      trackDrag.value.active = false;
    }

    function onTrackHeaderPointerDown(event: PointerEvent) {
      // Start track drag only if clicking header area (left column) without a layer clip
      const target = event.target as HTMLElement;
      if (target.closest('.track-header')) {
        trackDrag.value = { active: true, trackId: props.track.id, startY: event.clientY };
        window.addEventListener('pointerup', onPointerUp, { once: true });
      }
    }

    onBeforeUnmount(() => {
      window.removeEventListener('pointermove', onPointerMove);
    });

    return {
      laneRef,
      getClipStyle,
      onClipPointerDown,
      onHandlePointerDown,
      onTrackHeaderPointerDown,
    };
  },
});
</script>

<style scoped>
.subtitle-track {
  display: grid;
  grid-template-columns: 160px 1fr;
  align-items: stretch;
  min-height: 64px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.subtitle-track:last-child {
  border-bottom: none;
}

.track-header {
  padding: 12px;
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  border-left: 4px solid transparent;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: rgba(255, 255, 255, 0.02);
}

.name {
  font-weight: 600;
  color: #f5f7ff;
  font-size: 0.85rem;
}

.meta {
  font-size: 0.7rem;
  opacity: 0.6;
}

.track-lane {
  position: relative;
  background: rgba(255, 255, 255, 0.015);
  overflow: hidden;
}

.clip {
  position: absolute;
  top: 14px;
  height: 36px;
  background: linear-gradient(135deg, rgba(0, 173, 255, 0.35), rgba(0, 173, 255, 0.15));
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  cursor: grab;
  color: #e9f6ff;
  font-size: 0.8rem;
}

.clip.active {
  background: linear-gradient(135deg, rgba(0, 173, 255, 0.6), rgba(0, 173, 255, 0.35));
  border-color: rgba(0, 173, 255, 0.8);
}

.clip:active {
  cursor: grabbing;
}

.handle {
  width: 10px;
  height: 100%;
  position: absolute;
  top: 0;
  cursor: ew-resize;
  display: flex;
  align-items: center;
  justify-content: center;
}

.handle.start {
  left: -2px;
}

.handle.end {
  right: -2px;
}

.handle::before {
  content: '';
  width: 3px;
  height: 18px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 2px;
}

.clip-name {
  pointer-events: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>


