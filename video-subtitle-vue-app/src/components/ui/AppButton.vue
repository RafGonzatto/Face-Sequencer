<template>
  <button
    :class="buttonClass"
    :style="buttonStyle"
    @click="handleClick"
    :disabled="isDisabled"
  >
    <slot></slot>
  </button>
</template>

<script lang="ts">
import { defineComponent, PropType } from 'vue';

export default defineComponent({
  name: 'AppButton',
  props: {
    type: {
      type: String as PropType<'button' | 'submit' | 'reset'>,
      default: 'button',
    },
    variant: {
      type: String,
      default: 'primary',
    },
    size: {
      type: String,
      default: 'medium',
    },
    isDisabled: {
      type: Boolean,
      default: false,
    },
    customStyle: {
      type: Object as PropType<CSSStyleDeclaration>,
      default: () => ({}),
    },
  },
  computed: {
    buttonClass() {
      return [
        'app-button',
        `app-button--${this.variant}`,
        `app-button--${this.size}`,
        { 'app-button--disabled': this.isDisabled },
      ];
    },
    buttonStyle() {
      return this.customStyle;
    },
  },
  methods: {
    handleClick(event: MouseEvent) {
      if (this.isDisabled) {
        event.preventDefault();
        return;
      }
      this.$emit('click', event);
    },
  },
});
</script>

<style scoped>
.app-button {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.app-button--primary {
  background-color: #007bff;
  color: white;
}

.app-button--secondary {
  background-color: #6c757d;
  color: white;
}

.app-button--medium {
  font-size: 16px;
}

.app-button--disabled {
  background-color: #d6d6d6;
  cursor: not-allowed;
}
</style>