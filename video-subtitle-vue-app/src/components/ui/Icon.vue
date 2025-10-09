<template>
  <span :class="iconClass" aria-hidden="true">
    <slot></slot>
  </span>
</template>

<script lang="ts">
import { defineComponent, PropType } from 'vue';

export default defineComponent({
  name: 'Icon',
  props: {
    name: {
      type: String as PropType<string>,
      required: true,
    },
    size: {
      type: String as PropType<string>,
      default: '1em',
    },
    color: {
      type: String as PropType<string>,
      default: 'currentColor',
    },
  },
  computed: {
    iconClass(): string {
      return `icon-${this.name}`;
    },
  },
});
</script>

<style scoped>
.icon {
  display: inline-block;
  width: var(--icon-size, 1em);
  height: var(--icon-size, 1em);
  fill: var(--icon-color, currentColor);
}
</style>