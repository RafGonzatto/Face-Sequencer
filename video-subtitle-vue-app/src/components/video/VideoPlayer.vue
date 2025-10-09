<template>
  <div class="video-player">
    <div class="video-frame" :style="frameStyle">
      <template
        v-if="showBackendPreview && backendPreviewUrl && backendImageOk"
      >
        <img
          class="backend-frame"
          :src="backendPreviewUrl"
          alt="Backend preview frame"
          draggable="false"
          @error="onBackendImgError"
        />
      </template>
      <template v-else>
        <video
          ref="videoElement"
          playsinline
          :controls="false"
          @loadedmetadata="onLoadedMetadata"
          @timeupdate="onTimeUpdate"
          @play="onPlay"
          @pause="onPause"
        >
          <source
            v-if="videoSrc"
            :src="videoSrc"
            :type="videoMime || undefined"
          />
        </video>
        <OverlayCanvas
          ref="overlayRef"
          :layers="layers"
          :current-time="currentTime"
          :aspect-ratio="aspectRatio"
          :active-layer-ids="activeLayerIds"
          :safe-zone-enabled="safeZoneEnabled"
          :grid-visible="gridVisible"
          :playing="isPlaying"
          @update:layer-position="
            layer => $emit('update-layer-position', layer)
          "
          @select-layer="onSelectLayer"
          @hover-layer="$emit('hover-layer', $event)"
          @double-click-layer="$emit('double-click-layer', $event)"
        />
      </template>
    </div>
    <VideoControls
      :isPlaying="isPlaying"
      :currentTime="currentTime"
      :duration="duration"
      :volume="volume"
      @playPause="togglePlay"
      @seek="onSeek"
      @setVolume="setVolume"
    />
  </div>
</template>

<script lang="ts">
// @ts-nocheck
import { defineComponent, PropType, ref, watch, computed } from 'vue';
import VideoControls from './VideoControls.vue';
import OverlayCanvas from './OverlayCanvas.vue';
import { useVideoPlayer } from '@/composables/useVideoPlayer';
import type { TextLayer } from '@/modules/editor/editor-types';

interface AspectRatioSize {
  width: number;
  height: number;
  safeZonePadding?: number;
}

export default defineComponent({
  name: 'VideoPlayer',
  components: { VideoControls, OverlayCanvas },
  props: {
    videoSrc: { type: String as PropType<string>, default: '' },
    filename: { type: String as PropType<string>, default: '' },
    currentTime: { type: Number, required: true },
    layers: { type: Array as PropType<TextLayer[]>, default: () => [] },
    aspectRatio: { type: Object as PropType<AspectRatioSize>, required: true },
    activeLayerIds: { type: Array as PropType<string[]>, default: () => [] },
    safeZoneEnabled: { type: Boolean, default: true },
    gridVisible: { type: Boolean, default: true },
    backendPreviewUrl: { type: String as PropType<string>, default: '' },
    showBackendPreview: { type: Boolean, default: false },
  },
  emits: [
    'update:currentTime',
    'update:duration',
    'update:playing',
    'select-layer',
    'hover-layer',
    'double-click-layer',
    'update-layer-position',
  ],
  setup(
    props,
    /** @type {{ emit: any; expose: (exposed: any) => void }} */ {
      emit,
      expose,
    }
  ) {
    const backendImageOk = ref(true);
    const videoElement = ref<HTMLVideoElement | null>(null);
    const overlayRef = ref<any | null>(null);
    const videoMime = ref<string | null>(null);
    const {
      isPlaying,
      currentTime,
      duration,
      volume,
      togglePlay,
      seekTo,
      setVolume,
      updateCurrentTime,
      updateDuration,
    } = useVideoPlayer(videoElement);
    function onSeek(time: number) {
      // Atualiza o tempo no elemento de vídeo e notifica o pai imediatamente
      seekTo(time);
      emit('update:currentTime', time);
    }

    function onLoadedMetadata() {
      if (!videoElement.value) return;
      console.log('VIDEO PLAYER - (2/2) metadata carregada', {
        duration: videoElement.value.duration,
        videoWidth: videoElement.value.videoWidth,
        videoHeight: videoElement.value.videoHeight,
        readyState: videoElement.value.readyState,
        currentSrc: videoElement.value.currentSrc,
      });
      // Atualiza estado interno via composable e também notifica o pai
      updateDuration();
      emit('update:duration', videoElement.value.duration || 0);
    }

    function onTimeUpdate() {
      if (!videoElement.value) return;
      const time = videoElement.value.currentTime;
      // Atualiza estado interno via composable e também notifica o pai
      updateCurrentTime();
      emit('update:currentTime', time);
    }

    function onPlay() {
      emit('update:playing', true);
    }

    function onPause() {
      emit('update:playing', false);
    }

    function onBackendImgError() {
      backendImageOk.value = false;
    }

    function guessMime(src: string, name?: unknown): string | null {
      const target = String(name || src)
        .split('?')[0]
        .toLowerCase();
      const ext = target.substring(target.lastIndexOf('.') + 1);
      switch (ext) {
        case 'mp4':
          return 'video/mp4';
        case 'mov':
          return 'video/quicktime';
        case 'webm':
          return 'video/webm';
        case 'mkv':
          return 'video/x-matroska';
        case 'ogg':
        case 'ogv':
          return 'video/ogg';
        default:
          return null;
      }
    }

    watch(
      () => [props.videoSrc, props.filename],
      ([src, name]: [string, unknown]) => {
        if (src && videoElement.value) {
          console.log('VIDEO PLAYER - (1/2) aplicando source', {
            src,
            filename: name,
            mimeDetectado: guessMime(src, name),
            timestamp: new Date().toISOString(),
          });
          videoMime.value = guessMime(src, name);
          videoElement.value.src = src;
          videoElement.value.load();
        }
      },
      { immediate: true }
    );

    // Reset image-ok flag when a new backend image URL arrives
    watch(
      () => props.backendPreviewUrl,
      () => {
        backendImageOk.value = true;
      }
    );

    watch(
      () => props.currentTime,
      (time: number) => {
        if (!videoElement.value) return;
        const diff = Math.abs(videoElement.value.currentTime - time);
        if (diff > 0.02) {
          videoElement.value.currentTime = time;
        }
      }
    );

    const frameStyle = computed(() => {
      const ratio = props.aspectRatio.height / props.aspectRatio.width;
      return {
        paddingBottom: `${ratio * 100}%`,
      };
    });

    function onSelectLayer(layerId: string) {
      emit('select-layer', layerId);
    }

    // Expose elements for parent quick-export
    expose({
      getVideoEl: () => videoElement.value,
      getOverlayCanvas: () => overlayRef.value?.getCanvas?.() || null,
      getRenderSize: () => overlayRef.value?.getRenderSize?.() || null,
    });

    return {
      videoElement,
      overlayRef,
      videoMime,
      isPlaying,
      currentTime,
      duration,
      volume,
      togglePlay,
      seekTo,
      onSeek,
      setVolume,
      onLoadedMetadata,
      onTimeUpdate,
      onPlay,
      onPause,
      frameStyle,
      onSelectLayer,
      backendImageOk,
      onBackendImgError,
    };
  },
});
</script>

<style scoped>
.video-player {
  display: flex;
  flex-direction: column;
  gap: 12px;
  /* Evita que o player force scroll vertical excessivo; espaço reservado para controles abaixo */
  max-height: 100%;
}

.video-frame {
  position: relative;
  width: 100%;
  background: #000;
  border-radius: 12px;
  overflow: hidden;
  /* Permitir que o container encolha proporcionalmente sem quebrar layout */
  max-width: 100%;
}

.video-frame video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
  z-index: 1;
}

.video-frame .backend-frame {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
  z-index: 1;
  user-select: none;
}

/* Caso o container pai limite a altura, manter aspecto e caber sem ultrapassar viewport */
@media (max-height: 900px) {
  .video-player {
    max-height: calc(100vh - 200px); /* header + margens aproximadas */
  }
  .video-frame {
    /* permite que encolha; a proporção é preservada pelo padding trick */
    max-height: 100%;
  }
}

@media (max-width: 820px) {
  .video-player {
    max-height: none;
  }
}

.video-frame :deep(canvas) {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 2;
}
</style>
