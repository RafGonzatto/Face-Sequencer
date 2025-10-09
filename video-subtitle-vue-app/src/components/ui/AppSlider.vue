<template>
  <div class="app-slider">
    <input
      type="range"
      :min="min"
      :max="max"
      :value="modelValue"
      @input="updateValue"
      class="slider"
    />
    <span class="slider-value">{{ modelValue }}</span>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from 'vue';

export default defineComponent({
  name: 'AppSlider',
  props: {
    modelValue: {
      type: Number,
      required: true,
    },
    min: {
      type: Number,
      default: 0,
    },
    max: {
      type: Number,
      default: 100,
    },
  },
  emits: ['update:modelValue'],
  methods: {
    updateValue(event: Event) {
      const target = event.target as HTMLInputElement;
      const value = Number(target.value);
      this.$emit('update:modelValue', value);
    },
  },
});
</script>

<style scoped>
.app-slider {
  display: flex;
  align-items: center;
}

.slider {
  flex: 1;
  margin-right: 10px;
}

.slider-value {
  font-weight: bold;
}
</style>