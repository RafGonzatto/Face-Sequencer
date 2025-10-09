<template>
  <aside class="style-panel" v-if="layer">
    <header class="panel-header">
      <div>
        <h3>{{ layer.name }}</h3>
        <p>{{ formatRange(layer.start) }} – {{ formatRange(layer.end) }}</p>
      </div>
      <button type="button" class="btn" @click="$emit('rename-layer')">Rename</button>
    </header>

    <section class="section">
      <h4>Templates</h4>
      <div class="template-grid">
        <button
          v-for="template in templates"
          :key="template.id"
          type="button"
          :class="['template-card', { active: layer.templateId === template.id }]"
          @click="$emit('apply-template', template.id)"
        >
          <span class="template-name">{{ template.name }}</span>
          <small>{{ template.description }}</small>
        </button>
      </div>
    </section>

    <section class="section">
      <h4>Typography</h4>
      <div class="control">
        <label>Font Family</label>
        <select :value="layer.style.fontFamily" @change="updateStyle({ fontFamily: ($event.target as HTMLSelectElement).value })">
          <option v-for="option in fontOptions" :key="option" :value="option">{{ option }}</option>
        </select>
      </div>
      <div class="control-row">
        <label>Size</label>
        <input type="range" min="24" max="96" :value="layer.style.fontSize" @input="updateStyle({ fontSize: Number(($event.target as HTMLInputElement).value) })" />
        <span>{{ layer.style.fontSize }} px</span>
      </div>
      <div class="control-row">
        <label>Weight</label>
        <input type="range" min="100" max="900" step="100" :value="Number(layer.style.fontWeight)" @input="updateStyle({ fontWeight: String(($event.target as HTMLInputElement).value) })" />
        <span>{{ layer.style.fontWeight }}</span>
      </div>
      <div class="control-checks">
        <label><input type="checkbox" :checked="layer.style.uppercase" @change="updateStyle({ uppercase: ($event.target as HTMLInputElement).checked })" /> Uppercase</label>
        <label><input type="checkbox" :checked="layer.style.italic" @change="updateStyle({ italic: ($event.target as HTMLInputElement).checked })" /> Italic</label>
      </div>
    </section>

    <section class="section">
      <h4>Colors</h4>
      <div class="control">
        <label>Fill</label>
        <input type="color" :value="resolveColor(layer.style.fill)" @input="updateStyle({ fill: ($event.target as HTMLInputElement).value })" />
      </div>
      <div class="control">
        <label>Stroke</label>
        <div class="row">
          <input type="color" :value="layer.style.strokeColor" @input="updateStyle({ strokeColor: ($event.target as HTMLInputElement).value })" />
          <input type="range" min="0" max="12" :value="layer.style.strokeWidth" @input="updateStyle({ strokeWidth: Number(($event.target as HTMLInputElement).value) })" />
          <span>{{ layer.style.strokeWidth }} px</span>
        </div>
      </div>
      <div class="control">
        <label>Background</label>
        <div class="row">
          <input type="color" :value="layer.style.backgroundColor" @input="updateStyle({ backgroundColor: ($event.target as HTMLInputElement).value })" />
          <input type="range" min="0" max="1" step="0.05" :value="layer.style.backgroundOpacity" @input="updateStyle({ backgroundOpacity: Number(($event.target as HTMLInputElement).value) })" />
          <span>{{ Math.round(layer.style.backgroundOpacity * 100) }}%</span>
        </div>
      </div>
    </section>

    <section class="section">
      <h4>Shadow</h4>
      <div class="control-row">
        <label>Blur</label>
        <input type="range" min="0" max="48" :value="layer.style.shadowBlur" @input="updateStyle({ shadowBlur: Number(($event.target as HTMLInputElement).value) })" />
        <span>{{ layer.style.shadowBlur }} px</span>
      </div>
      <div class="control-row">
        <label>Offset X</label>
        <input type="range" min="-32" max="32" :value="layer.style.shadowOffsetX" @input="updateStyle({ shadowOffsetX: Number(($event.target as HTMLInputElement).value) })" />
        <span>{{ layer.style.shadowOffsetX }} px</span>
      </div>
      <div class="control-row">
        <label>Offset Y</label>
        <input type="range" min="-32" max="32" :value="layer.style.shadowOffsetY" @input="updateStyle({ shadowOffsetY: Number(($event.target as HTMLInputElement).value) })" />
        <span>{{ layer.style.shadowOffsetY }} px</span>
      </div>
      <div class="control">
        <label>Shadow Color</label>
        <input type="color" :value="layer.style.shadowColor" @input="updateStyle({ shadowColor: ($event.target as HTMLInputElement).value })" />
      </div>
    </section>

    <section class="section">
      <h4>Animation</h4>
      <select :value="layer.animation.kind" @change="$emit('update-animation', ($event.target as HTMLSelectElement).value)">
        <option value="none">None</option>
        <option value="pop">Pop In</option>
        <option value="bounce">Bounce</option>
        <option value="scale">Scale</option>
        <option value="fade">Fade</option>
        <option value="typewriter">Typewriter</option>
      </select>
    </section>

    <section class="section">
      <h4>Karaoke</h4>
      <label class="toggle">
        <input type="checkbox" :checked="layer.karaoke.enabled" @change="$emit('toggle-karaoke', ($event.target as HTMLInputElement).checked)" />
        <span>Enable word highlight</span>
      </label>
      <div class="control" v-if="layer.karaoke.enabled">
        <label>Highlight</label>
        <input type="color" :value="layer.karaoke.highlightColor" @input="$emit('update-karaoke', { highlightColor: ($event.target as HTMLInputElement).value })" />
      </div>
      <div class="control" v-if="layer.karaoke.enabled">
        <label>Rest</label>
        <input type="color" :value="layer.karaoke.restColor" @input="$emit('update-karaoke', { restColor: ($event.target as HTMLInputElement).value })" />
      </div>
    </section>
  </aside>
  <aside v-else class="style-panel empty">
    <h3>Select a layer to customize</h3>
    <p>Choose a caption in the preview or timeline to edit its style, animation, and karaoke options.</p>
  </aside>
</template>

<script lang="ts">
import { defineComponent, PropType } from 'vue';
import type { EditorTemplate, LayerStyle, TextLayer } from '@/modules/editor/editor-types';
import { formatTime } from '@/utils/time';

export default defineComponent({
  name: 'StylePanel',
  props: {
    layer: {
      type: Object as PropType<TextLayer | null>,
      default: null,
    },
    templates: {
      type: Array as PropType<EditorTemplate[]>,
      default: () => [],
    },
  },
  emits: ['update-style', 'apply-template', 'update-animation', 'toggle-karaoke', 'update-karaoke', 'rename-layer'],
  setup(props, { emit }) {
    const fontOptions = [
      'Inter, Arial, sans-serif',
      'Poppins, Arial, sans-serif',
      'Montserrat, Arial, sans-serif',
      'Roboto, Arial, sans-serif',
      'Oswald, Arial, sans-serif',
      'Playfair Display, serif',
    ];

    function updateStyle(stylePatch: Partial<LayerStyle>) {
      emit('update-style', stylePatch);
    }

    function resolveColor(fill: LayerStyle['fill']) {
      return Array.isArray(fill) ? fill[0]?.color ?? '#ffffff' : fill;
    }

    function formatRange(seconds: number) {
      return formatTime(seconds);
    }

    return {
      fontOptions,
      updateStyle,
      resolveColor,
      formatRange,
    };
  },
});
</script>

<style scoped>
.style-panel {
  background: #10141d;
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 320px;
  max-width: 360px;
}

.style-panel.empty {
  align-items: center;
  text-align: center;
  opacity: 0.8;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.panel-header p {
  margin: 0;
  font-size: 0.75rem;
  opacity: 0.6;
}

.btn {
  background: #1f2736;
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #f3f7ff;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 0.7rem;
  text-transform: uppercase;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section h4 {
  margin: 0;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  opacity: 0.8;
}

.control,
.control-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
}

.control {
  justify-content: space-between;
}

.control label,
.control-row label {
  flex: 1;
  opacity: 0.7;
}

.control select,
.control input[type='color'],
.control-row input[type='range'],
.control input[type='range'] {
  flex: 1;
}

.control-row span,
.control span {
  min-width: 48px;
  text-align: right;
  font-size: 0.75rem;
  opacity: 0.7;
}

.control-checks {
  display: flex;
  gap: 12px;
  font-size: 0.75rem;
  opacity: 0.8;
}

.control-checks label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
}

.template-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 10px;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #e8ecf9;
}

.template-card.active {
  border-color: #00adff;
  background: rgba(0, 173, 255, 0.16);
}

.template-name {
  font-weight: 600;
  font-size: 0.85rem;
}

.template-card small {
  font-size: 0.7rem;
  opacity: 0.7;
}

.row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.75rem;
}
</style>
