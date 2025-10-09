<template>
  <div class="ratio-safe-zones">
    <header>
      <span class="title">Aspect Ratio</span>
      <label class="toggle">
        <input type="checkbox" :checked="safeZoneEnabled" @change="$emit('toggle-safe-zone', $event.target?.checked)" />
        <span>Safe Zones</span>
      </label>
    </header>
    <div class="preset-grid">
      <button
        v-for="preset in presets"
        :key="preset.id"
        :class="['preset-btn', { active: preset.id === activePresetId }]"
        type="button"
        @click="$emit('select', preset.id)"
      >
        <span class="ratio-label">{{ preset.label }}</span>
        <small>{{ preset.width }} × {{ preset.height }}</small>
      </button>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from 'vue';
import type { AspectRatioPreset } from '@/modules/editor/editor-types';

export default defineComponent({
  name: 'RatioSafeZones',
  props: {
    presets: {
      type: Array as PropType<AspectRatioPreset[]>,
      required: true,
    },
    activePresetId: {
      type: String,
      required: true,
    },
    safeZoneEnabled: {
      type: Boolean,
      default: true,
    },
  },
  emits: ['select', 'toggle-safe-zone'],
});
</script>

<style scoped>
.ratio-safe-zones {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  color: #cdd2dd;
}

.title {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
}

.toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  opacity: 0.85;
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(96px, 1fr));
  gap: 8px;
}

.preset-btn {
  background: #1f232b;
  border: 1px solid transparent;
  color: #f0f4ff;
  border-radius: 8px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.preset-btn:hover {
  background: #242a35;
  border-color: rgba(255, 255, 255, 0.12);
}

.preset-btn.active {
  border-color: #00adff;
  background: rgba(0, 173, 255, 0.12);
}

.ratio-label {
  font-weight: 600;
  font-size: 0.9rem;
}

small {
  font-size: 0.7rem;
  opacity: 0.75;
}
</style>
