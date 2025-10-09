<template>
  <div
    ref="containerRef"
    class="overlay-canvas"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointerleave="onPointerUp"
    @dblclick="onDoubleClick"
  >
    <canvas ref="canvasRef"></canvas>
    <div v-if="safeZoneEnabled" class="safe-zone" :style="safeZoneStyle"></div>
  </div>
</template>

<script lang="ts">
// @ts-nocheck
import {
  defineComponent,
  onBeforeUnmount,
  onMounted,
  PropType,
  reactive,
  ref,
  watch,
  computed,
} from 'vue';
import { useResizeObserver } from '@/composables/useResizeObserver';
import type { TextLayer } from '@/modules/editor/editor-types';

interface LayerRect {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function easeOutBack(t: number) {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
}

function degToRad(value: number) {
  return (value * Math.PI) / 180;
}

export default defineComponent({
  name: 'OverlayCanvas',
  props: {
    layers: {
      type: Array as PropType<TextLayer[]>,
      required: true,
    },
    currentTime: {
      type: Number,
      required: true,
    },
    aspectRatio: {
      type: Object as PropType<{
        width: number;
        height: number;
        safeZonePadding?: number;
      }>,
      required: true,
    },
    activeLayerIds: {
      type: Array as PropType<string[]>,
      default: () => [],
    },
    safeZoneEnabled: {
      type: Boolean,
      default: true,
    },
    gridVisible: {
      type: Boolean,
      default: true,
    },
    playing: {
      type: Boolean,
      default: false,
    },
  },
  emits: [
    'update:layer-position',
    'select-layer',
    'hover-layer',
    'double-click-layer',
  ],
  setup(
    props,
    /** @type {{ emit: any; expose: (exposed: any) => void }} */ {
      emit,
      expose,
    }
  ) {
    const containerRef = ref<HTMLDivElement | null>(null);
    const canvasRef = ref<HTMLCanvasElement | null>(null);
    const ctxRef = ref<CanvasRenderingContext2D | null>(null);
    const size = reactive({ width: 320, height: 568 });
    const layerRects = reactive<Map<string, LayerRect>>(new Map());
    const frameHandle = ref<number | null>(null);
    const dragState = reactive({
      active: false,
      layerId: '' as string | null,
      offsetX: 0,
      offsetY: 0,
    });

    const visibleLayers = computed(() => {
      return props.layers
        .filter(
          (layer: TextLayer) =>
            props.currentTime >= layer.start &&
            props.currentTime <= layer.end &&
            layer.visible
        )
        .sort((a: TextLayer, b: TextLayer) => a.start - b.start);
    });
    const safeZoneEnabledRef = computed(() => props.safeZoneEnabled);

    const safeZoneStyle = computed(() => {
      const padding = props.safeZoneEnabled
        ? (props.aspectRatio.safeZonePadding ?? 0.08)
        : 0;
      const pct = padding * 100;
      return {
        top: `${pct}%`,
        bottom: `${pct}%`,
        left: `${pct}%`,
        right: `${pct}%`,
      };
    });

    function updateCanvasSize(rect?: DOMRectReadOnly) {
      if (!canvasRef.value || !containerRef.value) return;
      const bounds = rect || containerRef.value.getBoundingClientRect();
      if (!bounds.width) return;
      const ratio = props.aspectRatio.height / props.aspectRatio.width;
      const width = bounds.width;
      const height = width * ratio;
      size.width = width;
      size.height = height;
      const canvas = canvasRef.value;
      const dpr = Math.max(1, window.devicePixelRatio || 1);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      const ctx = ctxRef.value;
      if (ctx) {
        // Reset any existing transform and apply DPR scaling to keep crisp rendering
        if ((ctx as any).resetTransform) {
          (ctx as any).resetTransform();
        }
        if ((ctx as any).setTransform) {
          (ctx as any).setTransform(dpr, 0, 0, dpr, 0, 0);
        } else {
          ctx.scale(dpr, dpr);
        }
      }
      scheduleDraw();
    }

    function scheduleDraw() {
      if (frameHandle.value !== null) return;
      frameHandle.value = requestAnimationFrame(() => {
        frameHandle.value = null;
        drawFrame();
      });
    }

    function resetLayerRects() {
      layerRects.clear();
    }

    function buildFillStyle(
      ctx: CanvasRenderingContext2D,
      width: number,
      height: number,
      fill: TextLayer['style']['fill'],
      angleDeg: number
    ) {
      if (Array.isArray(fill)) {
        const angle = degToRad(angleDeg);
        const x = Math.cos(angle) * width;
        const y = Math.sin(angle) * height;
        const gradient = ctx.createLinearGradient(0, 0, x, y);
        fill.forEach(stop => gradient.addColorStop(stop.offset, stop.color));
        return gradient;
      }
      return fill;
    }

    function drawRoundedRect(
      ctx: CanvasRenderingContext2D,
      x: number,
      y: number,
      width: number,
      height: number,
      radius: number
    ) {
      const r = Math.min(radius, width / 2, height / 2);
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + width - r, y);
      ctx.quadraticCurveTo(x + width, y, x + width, y + r);
      ctx.lineTo(x + width, y + height - r);
      ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
      ctx.lineTo(x + r, y + height);
      ctx.quadraticCurveTo(x, y + height, x, y + height - r);
      ctx.lineTo(x, y + r);
      ctx.quadraticCurveTo(x, y, x + r, y);
      ctx.closePath();
    }

    function applyAnimation(layer: TextLayer, time: number) {
      const local = clamp(time - layer.start, 0, layer.end - layer.start);
      const duration = Math.max(layer.end - layer.start, 0.001);
      const progress = clamp(local / duration, 0, 1);
      let scale = layer.scale;
      let opacity = layer.opacity;
      let typedText = layer.text;

      switch (layer.animation.kind) {
        case 'pop': {
          if (progress < 0.4) {
            const eased = easeOutBack(progress / 0.4);
            scale = layer.scale * clamp(eased, 0, 1.1);
          }
          break;
        }
        case 'bounce': {
          const t = Math.min(progress / 0.3, 1);
          const bounce = Math.sin(t * Math.PI * 1.5) * 0.08;
          scale = layer.scale * (1 + bounce);
          break;
        }
        case 'scale': {
          const t = clamp(progress / 0.5, 0, 1);
          scale = layer.scale * (0.7 + t * 0.3);
          break;
        }
        case 'fade': {
          if (progress < 0.2) {
            opacity = layer.opacity * clamp(progress / 0.2, 0, 1);
          } else if (progress > 0.8) {
            opacity = layer.opacity * clamp((1 - progress) / 0.2, 0, 1);
          }
          break;
        }
        case 'typewriter': {
          const totalChars = Math.max(layer.text.length, 1);
          const charCount = Math.floor(totalChars * progress);
          typedText = layer.text.slice(0, Math.max(1, charCount));
          break;
        }
        default:
          break;
      }

      return { scale, opacity, typedText };
    }

    function drawGrid(ctx: CanvasRenderingContext2D) {
      const spacing = size.height / 12;
      ctx.save();
      ctx.strokeStyle = 'rgba(255,255,255,0.08)';
      ctx.lineWidth = 1;
      for (let y = spacing; y < size.height; y += spacing) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(size.width, y);
        ctx.stroke();
      }
      const verticalSpacing = size.width / 6;
      for (let x = verticalSpacing; x < size.width; x += verticalSpacing) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, size.height);
        ctx.stroke();
      }
      ctx.restore();
    }

    function drawFrame() {
      const ctx = ctxRef.value;
      const canvas = canvasRef.value;
      if (!ctx || !canvas) return;
      // Debug: summarize render state
      console.log('OVERLAY DEBUG - drawFrame', {
        layersProp: props.layers.length,
        visible: visibleLayers.value.length,
        time: props.currentTime,
      });
      // Clear with identity transform to account for DPR scaling
      ctx.save();
      if ((ctx as any).setTransform) {
        (ctx as any).setTransform(1, 0, 0, 1, 0, 0);
      } else if ((ctx as any).resetTransform) {
        (ctx as any).resetTransform();
      }
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.restore();

      ctx.save();
      if (props.gridVisible) {
        drawGrid(ctx);
      }
      resetLayerRects();
      const scaleFactor = size.width / props.aspectRatio.width;
      visibleLayers.value.forEach((layer: TextLayer) => {
        drawLayer(ctx, layer, scaleFactor);
      });
      ctx.restore();
    }

    function drawLayer(
      ctx: CanvasRenderingContext2D,
      layer: TextLayer,
      scaleFactor: number
    ) {
      const { scale, opacity, typedText } = applyAnimation(
        layer,
        props.currentTime
      );
      if (opacity <= 0) return;

      const text = layer.style.uppercase ? typedText.toUpperCase() : typedText;
      const fontSize = layer.style.fontSize * scaleFactor * scale;
      const lineHeightPx = fontSize * layer.style.lineHeight;
      ctx.save();
      ctx.font = `${layer.style.italic ? 'italic ' : ''}${layer.style.fontWeight} ${fontSize}px ${layer.style.fontFamily}`;
      ctx.textBaseline = 'middle';
      ctx.textAlign = layer.style.textAlign;
      const lines = text.split(/\r?\n/);
      const lineWidths = lines.map(line => ctx.measureText(line).width);
      const textWidth = Math.max(...lineWidths, 1);
      const contentWidth = textWidth;
      const contentHeight = lineHeightPx * lines.length;
      const padding = layer.style.backgroundPadding * scaleFactor;
      const boxWidth = contentWidth + padding * 2;
      const boxHeight = contentHeight + padding * 2;
      const posX = layer.position.x * size.width;
      const posY = layer.position.y * size.height;

      const anchorX =
        layer.position.anchorX === -1
          ? 0
          : layer.position.anchorX === 1
            ? 1
            : 0.5;
      const anchorY =
        layer.position.anchorY === -1
          ? 0
          : layer.position.anchorY === 1
            ? 1
            : 0.5;
      const offsetX = boxWidth * anchorX;
      const offsetY = boxHeight * anchorY;

      ctx.translate(posX, posY);
      ctx.rotate(degToRad(layer.rotation));
      ctx.globalAlpha = opacity;
      ctx.translate(-offsetX, -offsetY);

      const boxX = 0;
      const boxY = 0;
      // Background
      if (layer.style.backgroundOpacity > 0) {
        ctx.save();
        ctx.globalAlpha = layer.style.backgroundOpacity;
        ctx.fillStyle = layer.style.backgroundColor;
        drawRoundedRect(
          ctx,
          boxX,
          boxY,
          boxWidth,
          boxHeight,
          layer.style.backgroundRadius * scaleFactor
        );
        ctx.fill();
        ctx.restore();
      }

      // Selection outline
      if (props.activeLayerIds.includes(layer.id)) {
        ctx.save();
        ctx.strokeStyle = 'rgba(0, 173, 255, 0.9)';
        ctx.lineWidth = 2;
        drawRoundedRect(
          ctx,
          boxX - 4,
          boxY - 4,
          boxWidth + 8,
          boxHeight + 8,
          layer.style.backgroundRadius * scaleFactor
        );
        ctx.stroke();
        ctx.restore();
      }

      // Shadow
      ctx.shadowColor = layer.style.shadowColor;
      ctx.shadowBlur = layer.style.shadowBlur * scaleFactor;
      ctx.shadowOffsetX = layer.style.shadowOffsetX * scaleFactor;
      ctx.shadowOffsetY = layer.style.shadowOffsetY * scaleFactor;

      const fillStyle = layer.karaoke.enabled
        ? layer.karaoke.restColor
        : buildFillStyle(
            ctx,
            contentWidth,
            contentHeight,
            layer.style.fill,
            layer.style.gradientAngle
          );

      const startX = padding;
      let currentY = padding + lineHeightPx / 2;

      ctx.fillStyle = fillStyle as CanvasGradient | string;
      if (layer.style.strokeWidth > 0) {
        ctx.lineWidth = layer.style.strokeWidth * scaleFactor;
        ctx.strokeStyle = layer.style.strokeColor;
      }

      lines.forEach((line, index) => {
        const lineWidth = Math.max(lineWidths[index], 1);
        let lineX = startX;
        if (layer.style.textAlign === 'center') {
          lineX = padding + contentWidth / 2;
        } else if (layer.style.textAlign === 'right') {
          lineX = padding + contentWidth;
        }
        if (layer.style.strokeWidth > 0) {
          ctx.strokeText(line, lineX, currentY);
        }
        ctx.fillText(line, lineX, currentY);
        currentY += lineHeightPx;
      });

      if (layer.karaoke.enabled) {
        ctx.save();
        ctx.shadowColor = 'transparent';
        const words = [...layer.karaoke.words].sort(
          (a, b) => a.start - b.start
        );
        const boxLeft = boxX + padding;
        let highlightWidth = 0;
        let highlightCap = 0;
        const spaceWidth = ctx.measureText(' ').width;
        words.forEach((word, index) => {
          const width =
            ctx.measureText(word.text).width +
            (index < words.length - 1 ? spaceWidth : 0);
          if (props.currentTime >= word.end) {
            highlightWidth += width;
            highlightCap = highlightWidth;
          } else if (props.currentTime >= word.start) {
            const span = word.end - word.start || 0.0001;
            const ratio = clamp((props.currentTime - word.start) / span, 0, 1);
            highlightWidth += width * ratio;
            highlightCap = highlightWidth;
          }
        });
        if (highlightCap > 0) {
          ctx.beginPath();
          ctx.rect(boxLeft, boxY + padding, highlightCap, contentHeight);
          ctx.clip();
          ctx.fillStyle = layer.karaoke.highlightColor;
          currentY = padding + lineHeightPx / 2;
          lines.forEach((line, index) => {
            const lineWidth = Math.max(lineWidths[index], 1);
            let lineX = startX;
            if (layer.style.textAlign === 'center') {
              lineX = padding + contentWidth / 2;
            } else if (layer.style.textAlign === 'right') {
              lineX = padding + contentWidth;
            }
            ctx.fillText(line, lineX, currentY);
            currentY += lineHeightPx;
          });
        }
        ctx.restore();
      }

      const rect: LayerRect = {
        id: layer.id,
        x: (posX - offsetX) / size.width,
        y: (posY - offsetY) / size.height,
        width: boxWidth / size.width,
        height: boxHeight / size.height,
      };
      layerRects.set(layer.id, rect);
      ctx.restore();
    }

    function hitTestLayer(normalizedX: number, normalizedY: number) {
      const entries = Array.from(layerRects.values()) as LayerRect[];
      for (let i = entries.length - 1; i >= 0; i -= 1) {
        const rect = entries[i];
        if (
          normalizedX >= rect.x &&
          normalizedX <= rect.x + rect.width &&
          normalizedY >= rect.y &&
          normalizedY <= rect.y + rect.height
        ) {
          return rect.id;
        }
      }
      return null;
    }

    function getPointerPosition(event: PointerEvent) {
      const canvas = canvasRef.value;
      if (!canvas) {
        return { x: 0, y: 0, nx: 0, ny: 0 };
      }
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      return {
        x,
        y,
        nx: clamp(x / rect.width, 0, 1),
        ny: clamp(y / rect.height, 0, 1),
      };
    }

    function onPointerDown(event: PointerEvent) {
      event.preventDefault();
      const pos = getPointerPosition(event);
      const layerId = hitTestLayer(pos.nx, pos.ny);
      if (layerId) {
        dragState.active = true;
        dragState.layerId = layerId;
        dragState.offsetX = pos.nx;
        dragState.offsetY = pos.ny;
        const layer = props.layers.find(
          (item: TextLayer) => item.id === layerId
        );
        if (layer) {
          dragState.offsetX -= layer.position.x;
          dragState.offsetY -= layer.position.y;
        }
        emit('select-layer', layerId);
      } else {
        emit('select-layer', '');
      }
    }

    function onPointerMove(event: PointerEvent) {
      const pos = getPointerPosition(event);
      if (dragState.active && dragState.layerId) {
        const layer = props.layers.find(
          (item: TextLayer) => item.id === dragState.layerId
        );
        if (layer) {
          const nextX = clamp(pos.nx - dragState.offsetX, 0, 1);
          const nextY = clamp(pos.ny - dragState.offsetY, 0, 1);
          emit('update:layer-position', {
            layerId: dragState.layerId,
            position: { x: nextX, y: nextY },
          });
        }
      } else {
        const layerId = hitTestLayer(pos.nx, pos.ny);
        emit('hover-layer', layerId || null);
      }
    }

    function onPointerUp() {
      dragState.active = false;
      dragState.layerId = null;
    }

    function onDoubleClick(event: MouseEvent) {
      const pos = getPointerPosition(event as unknown as PointerEvent);
      const layerId = hitTestLayer(pos.nx, pos.ny);
      if (layerId) {
        emit('double-click-layer', layerId);
      }
    }

    function handleWindowResize() {
      // Recalculate sizes on window resize/zoom (affects devicePixelRatio)
      updateCanvasSize();
    }

    onMounted(() => {
      if (!canvasRef.value) return;
      ctxRef.value = canvasRef.value.getContext('2d');
      updateCanvasSize();
      scheduleDraw();
      // Iniciar observer de resize do container
      if (containerRef.value) {
        observe(containerRef.value);
      }
      // Listen to window resize/zoom to update DPR and sizes
      window.addEventListener('resize', handleWindowResize);
    });

    onBeforeUnmount(() => {
      if (frameHandle.value !== null) {
        cancelAnimationFrame(frameHandle.value);
      }
      if (containerRef.value) {
        unobserve(containerRef.value);
      }
      window.removeEventListener('resize', handleWindowResize);
    });

    const { observe, unobserve } = useResizeObserver(entries => {
      if (!entries.length) return;
      updateCanvasSize(entries[0].contentRect);
    });

    watch(
      () => [
        props.layers,
        props.currentTime,
        props.safeZoneEnabled,
        props.gridVisible,
        props.activeLayerIds,
      ],
      scheduleDraw,
      { deep: true }
    );

    // Log when incoming layers change
    watch(
      () => props.layers,
      (layers: TextLayer[]) => {
        console.log('OVERLAY DEBUG - props.layers changed', {
          count: Array.isArray(layers) ? layers.length : 0,
          first:
            Array.isArray(layers) && layers[0]
              ? {
                  id: layers[0].id,
                  text: layers[0].text,
                  start: layers[0].start,
                  end: layers[0].end,
                }
              : null,
        });
      },
      { immediate: true, deep: true }
    );

    watch(
      () => props.playing,
      (value: boolean) => {
        if (value) {
          scheduleDraw();
        }
      }
    );

    // Expose internal elements for parent compositing/recording
    expose({
      getCanvas: () => canvasRef.value,
      getContainer: () => containerRef.value,
      getRenderSize: () => ({ width: size.width, height: size.height }),
    });

    return {
      containerRef,
      canvasRef,
      safeZoneStyle,
      safeZoneEnabled: safeZoneEnabledRef,
      onPointerDown,
      onPointerMove,
      onPointerUp,
      onDoubleClick,
    };
  },
});
</script>

<style scoped>
.overlay-canvas {
  position: relative;
  width: 100%;
  height: auto;
  touch-action: none;
  cursor: grab;
}

.overlay-canvas:active {
  cursor: grabbing;
}

canvas {
  display: block;
  width: 100%;
  height: auto;
  background: transparent;
  user-select: none;
}

.safe-zone {
  position: absolute;
  border: 2px dashed rgba(255, 255, 255, 0.25);
  border-radius: 8px;
  pointer-events: none;
}
</style>
