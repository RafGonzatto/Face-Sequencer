<template>
  <div class="timeline-editor">
    <header class="timeline-toolbar">
      <div class="left">
        <button type="button" class="btn" @click="$emit('create-track')">
          Add Text Track
        </button>
        <button
          type="button"
          class="btn"
          @click="$emit('duplicate-selection')"
          :disabled="!activeLayerIds.length"
        >
          Duplicate Layer
        </button>
      </div>
      <div class="center">
        <label class="zoom">
          <span>Zoom</span>
          <input
            type="range"
            min="40"
            max="240"
            step="10"
            v-model.number="pixelsPerSecond"
          />
        </label>
        <label class="toggle">
          <input
            type="checkbox"
            :checked="snapping"
            @change="$emit('toggle-snapping', $event.target?.checked)"
          />
          <span>Snapping</span>
        </label>
        <label class="zoom" title="Snap interval in seconds">
          <span>Grid</span>
          <input
            type="number"
            min="0.01"
            step="0.01"
            :value="snapInterval"
            @change="
              $emit(
                'update-snap-interval',
                Number(($event.target as HTMLInputElement).value) || 0.05
              )
            "
            style="width: 64px"
          />
        </label>
      </div>
      <div class="right">
        <span class="time"
          >{{ formattedCurrentTime }} / {{ formattedDuration }}</span
        >
      </div>
    </header>
    <div class="timeline-body">
      <div ref="rulerRef" class="time-ruler" @pointerdown="onRulerPointerDown">
        <div class="ticks" :style="{ width: rulerWidth + 'px' }">
          <div
            v-for="tick in ticks"
            :key="tick.time"
            class="tick"
            :class="{ major: tick.major }"
            :style="{ left: tick.position + 'px' }"
          >
            <span v-if="tick.major">{{ tick.label }}</span>
          </div>
        </div>
        <div class="playhead" :style="{ left: playheadPosition + 'px' }"></div>
      </div>
      <div ref="tracksContainerRef" class="tracks" @scroll="onScroll">
        <div class="tracks-inner" :style="{ width: rulerWidth + 'px' }">
          <SubtitleTrack
            v-for="track in tracks"
            :key="track.id"
            :track="track"
            :duration="duration"
            :layers="layers"
            :pixels-per-second="pixelsPerSecond"
            :active-layer-ids="activeLayerIds"
            :scroll-left="scrollLeft"
            :snapping="snapping"
            :snap-interval="snapInterval"
            @select-layer="$emit('select-layer', $event)"
            @update-layer="onUpdateLayer"
            @reorder-layer="$emit('reorder-layer', $event)"
            @reorder-track="$emit('reorder-track', $event)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
// @ts-nocheck
import {
  computed,
  defineComponent,
  onBeforeUnmount,
  onMounted,
  PropType,
  ref,
  watch,
} from 'vue';
import SubtitleTrack from './SubtitleTrack.vue';
import type { TextLayer, TextTrack } from '@/modules/editor/editor-types';
import { formatTime } from '@/utils/time';

interface TickMark {
  time: number;
  label: string;
  position: number;
  major: boolean;
}

export default defineComponent({
  name: 'TimelineEditor',
  components: { SubtitleTrack },
  props: {
    tracks: {
      type: Array as PropType<TextTrack[]>,
      required: true,
    },
    layers: {
      type: Object as PropType<Record<string, TextLayer>>,
      required: true,
    },
    currentTime: {
      type: Number,
      required: true,
    },
    duration: {
      type: Number,
      required: true,
    },
    activeLayerIds: {
      type: Array as PropType<string[]>,
      default: () => [],
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
  emits: [
    'update:time',
    'update-layer',
    'select-layer',
    'toggle-snapping',
    'create-track',
    'duplicate-selection',
    'reorder-layer',
    'reorder-track',
    'update-snap-interval',
  ],
  setup(props, { emit }) {
    const pixelsPerSecond = ref(120);
    const rulerRef = ref<HTMLDivElement | null>(null);
    const tracksContainerRef = ref<HTMLDivElement | null>(null);
    const scrollLeft = ref(0);
    const scrubbing = ref(false);

    const formattedCurrentTime = computed(() => formatTime(props.currentTime));
    const formattedDuration = computed(() => formatTime(props.duration));

    const rulerWidth = computed(() =>
      Math.max(props.duration * pixelsPerSecond.value, 600)
    );

    const playheadPosition = computed(
      () => props.currentTime * pixelsPerSecond.value
    );

    const ticks = computed(() => {
      const spacing = determineTickSpacing(pixelsPerSecond.value);
      const tickMarks: TickMark[] = [];
      for (let time = 0; time <= props.duration; time += spacing.minor) {
        const major = time % spacing.major === 0;
        tickMarks.push({
          time,
          label: major ? formatTime(time) : '',
          position: time * pixelsPerSecond.value,
          major,
        });
      }
      return tickMarks;
    });

    function determineTickSpacing(pps: number) {
      if (pps > 200) {
        return { major: 2, minor: 0.5 };
      }
      if (pps > 120) {
        return { major: 5, minor: 1 };
      }
      if (pps > 80) {
        return { major: 10, minor: 2 };
      }
      return { major: 15, minor: 5 };
    }

    function updatePlayheadFromPointer(event: PointerEvent) {
      if (!rulerRef.value) return;
      const rect = rulerRef.value.getBoundingClientRect();
      const x = event.clientX - rect.left + scrollLeft.value;
      const seconds = x / pixelsPerSecond.value;
      emit('update:time', Math.max(0, Math.min(props.duration, seconds)));
    }

    function onPointerMove(event: PointerEvent) {
      if (!scrubbing.value) return;
      updatePlayheadFromPointer(event);
    }

    function onPointerUp(event: PointerEvent) {
      if (!scrubbing.value) return;
      scrubbing.value = false;
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
      updatePlayheadFromPointer(event);
    }

    function onRulerPointerDown(event: PointerEvent) {
      scrubbing.value = true;
      updatePlayheadFromPointer(event);
      window.addEventListener('pointermove', onPointerMove);
      window.addEventListener('pointerup', onPointerUp);
    }

    function onScroll() {
      if (!tracksContainerRef.value) return;
      scrollLeft.value = tracksContainerRef.value.scrollLeft;
    }

    function onUpdateLayer(payload: {
      layerId: string;
      start: number;
      end: number;
    }) {
      emit('update-layer', payload);
    }

    onMounted(() => {
      if (tracksContainerRef.value) {
        scrollLeft.value = tracksContainerRef.value.scrollLeft;
      }
    });

    onBeforeUnmount(() => {
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
    });

    watch(
      () => props.duration,
      () => {
        if (props.duration * pixelsPerSecond.value < 600) {
          pixelsPerSecond.value = Math.max(
            40,
            600 / Math.max(props.duration, 1)
          );
        }
      },
      { immediate: true }
    );

    return {
      pixelsPerSecond,
      rulerRef,
      tracksContainerRef,
      scrollLeft,
      ticks,
      rulerWidth,
      playheadPosition,
      formattedCurrentTime,
      formattedDuration,
      onRulerPointerDown,
      onScroll,
      onUpdateLayer,
    };
  },
});
</script>

<style scoped>
.timeline-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #141821;
  border: 1px solid #1e2431;
  border-radius: 12px;
  padding: 12px;
}

.timeline-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.timeline-toolbar .btn {
  background: #1f2736;
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #f3f7ff;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.timeline-toolbar .btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.left,
.center,
.right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.zoom {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.zoom input[type='range'] {
  accent-color: #00adff;
}

.toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.7rem;
  opacity: 0.8;
}

.time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  color: #cdd2dd;
}

.timeline-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.time-ruler {
  position: relative;
  height: 40px;
  background: #1a1f2b;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}

.ticks {
  position: relative;
  height: 100%;
}

.tick {
  position: absolute;
  top: 0;
  width: 1px;
  height: 40px;
  background: rgba(255, 255, 255, 0.12);
}

.tick.major {
  background: rgba(255, 255, 255, 0.25);
}

.tick span {
  position: absolute;
  top: 16px;
  left: 8px;
  font-size: 0.65rem;
  color: rgba(255, 255, 255, 0.6);
}

.playhead {
  position: absolute;
  top: 0;
  width: 2px;
  height: 100%;
  background: #00adff;
  pointer-events: none;
}

.tracks {
  max-height: 260px;
  overflow-x: auto;
  overflow-y: auto;
  background: #10131c;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.tracks-inner {
  position: relative;
}
</style>
