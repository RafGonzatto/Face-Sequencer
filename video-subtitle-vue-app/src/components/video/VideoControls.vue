<template>
  <div class="video-controls">
    <button type="button" class="btn" @click="$emit('playPause')">
      <span v-if="isPlaying">?</span>
      <span v-else>?</span>
    </button>
    <input
      class="seek"
      type="range"
      :value="currentTime"
      min="0"
      :max="duration"
      step="0.01"
      @input="$emit('seek', Number(($event.target as HTMLInputElement).value))"
    />
    <span class="time">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
    <input
      class="volume"
      type="range"
      :value="volume"
      min="0"
      max="1"
      step="0.05"
      @input="$emit('setVolume', Number(($event.target as HTMLInputElement).value))"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { formatTime } from '@/utils/time';

export default defineComponent({
  name: 'VideoControls',
  props: {
    isPlaying: { type: Boolean, default: false },
    currentTime: { type: Number, default: 0 },
    duration: { type: Number, default: 0 },
    volume: { type: Number, default: 1 },
  },
  emits: ['playPause', 'seek', 'setVolume'],
  setup() {
    return { formatTime };
  },
});
</script>

<style scoped>
.video-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(0, 0, 0, 0.25);
  padding: 8px 12px;
  border-radius: 8px;
}

.btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: #ffffff;
  color: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
}

.seek {
  flex: 1;
}

.time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  opacity: 0.8;
}

.volume {
  width: 120px;
}
</style>
