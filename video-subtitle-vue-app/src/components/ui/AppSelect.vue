<template>
  <div class="app-select">
    <label v-if="label" :for="selectId" class="app-select__label">{{ label }}</label>
    <select
      :id="selectId"
      v-model="selectedValue"
      @change="handleChange"
      class="app-select__input"
    >
      <option v-for="option in options" :key="option.value" :value="option.value">
        {{ option.text }}
      </option>
    </select>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from 'vue';

interface Option {
  value: string | number;
  text: string;
}

export default defineComponent({
  name: 'AppSelect',
  props: {
    options: {
      type: Array as PropType<Option[]>,
      required: true,
    },
    modelValue: {
      type: [String, Number] as PropType<string | number>,
      required: true,
    },
    label: {
      type: String,
      default: '',
    },
    selectId: {
      type: String,
      default: () => `app-select-${Math.random().toString(36).substr(2, 9)}`,
    },
  },
  emits: ['update:modelValue'],
  computed: {
    selectedValue: {
      get() {
        return this.modelValue;
      },
      set(value) {
        this.$emit('update:modelValue', value);
      },
    },
  },
  methods: {
    handleChange() {
      this.$emit('change', this.selectedValue);
    },
  },
});
</script>

<style scoped>
.app-select {
  display: flex;
  flex-direction: column;
}

.app-select__label {
  margin-bottom: 0.5rem;
  font-weight: bold;
}

.app-select__input {
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 1rem;
}
</style>