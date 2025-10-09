<template>
  <div class="subtitle-overlay" v-if="activeCue">
    <div class="subtitle-text" :style="computedStyle">
      {{ activeCue.text }}
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, computed, ref, watch } from 'vue';
import { SubtitleCue } from '@/modules/subtitles/subtitleTypes';

export default defineComponent({
  name: 'SubtitleOverlay',
  props: {
    cues: { type: Array as () => SubtitleCue[], required: true },
    currentTime: {
      type: Number,
      required: true,
    },
    style: { type: Object, required: false, default: () => ({}) },
  },
  setup(props) {
    const activeCue = ref<SubtitleCue | null>(null);

    const updateActiveCue = () => {
      const cue = props.cues.find(
        cue => props.currentTime >= cue.start && props.currentTime <= cue.end
      );
      activeCue.value = cue || null;
    };

    const computedStyle = computed(() => {
      const s: any = props.style || {};
      return {
        fontFamily: s.fontFamily || 'Arial, sans-serif',
        fontSize: s.fontSize ? `${s.fontSize}px` : '24px',
        color: s.color || '#fff',
        backgroundColor: s.bgColor || 'rgba(0,0,0,0.6)',
        opacity: s.bgOpacity ?? 1,
        padding: s.padding ? `${s.padding}px` : '4px 8px',
        borderRadius: s.borderRadius ? `${s.borderRadius}px` : '4px',
        textAlign: s.textAlign || 'center',
        position: 'absolute',
        bottom: s.marginY ? `${s.marginY}px` : '5%',
        left: '50%',
        transform: 'translateX(-50%)',
        maxWidth: s.maxWidth ? `${s.maxWidth}%` : '80%',
      };
    });

    // Watch for changes in currentTime to update the active cue
    watch(() => props.currentTime, updateActiveCue);

    return {
      activeCue,
      computedStyle,
    };
  },
});
</script>

<style scoped>
.subtitle-overlay {
  position: relative;
  pointer-events: none;
}

.subtitle-text {
  display: flex;
  justify-content: center;
  align-items: center;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
}
</style>
