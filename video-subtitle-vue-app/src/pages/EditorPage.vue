<template>
  <DefaultLayout>
    <div class="editor-page">
      <header class="page-header">
        <div>
          <h1>CapCut-Style Subtitle Studio</h1>
          <p>
            Create animated captions with precise karaoke sync and export-ready
            styling.
          </p>
        </div>
        <div class="status-pills">
          <span v-if="workflow.uploading" class="pill">Uploading...</span>
          <span v-if="workflow.aligning" class="pill">Aligning...</span>
          <span v-if="workflow.generating" class="pill">Generating...</span>
          <span v-if="workflow.exporting" class="pill">Exporting...</span>
          <span v-if="workflow.error" class="pill error">{{
            workflow.error
          }}</span>
        </div>
      </header>

      <section class="ingest-card">
        <div class="file-column">
          <label class="heading">Media</label>
          <div class="file-picker">
            <button type="button" class="primary" @click="openFilePicker">
              Select Media
            </button>
            <input
              ref="fileInputRef"
              class="hidden"
              type="file"
              accept="audio/*,video/*"
              @change="onFileChange"
            />
            <span v-if="pendingFile" class="file-meta"
              >{{ pendingFile.name }} (local)</span
            >
            <span v-else-if="workflow.lastUploadFilename" class="file-meta"
              >Server: {{ workflow.lastUploadFilename }}</span
            >
          </div>
          <div class="toggles">
            <label
              ><input type="checkbox" v-model="autoUpload" /> Auto-upload on
              select</label
            >
            <label
              ><input type="checkbox" v-model="snapping" /> Timeline
              snapping</label
            >
          </div>
          <div class="actions">
            <button
              type="button"
              class="ghost"
              :disabled="!pendingFile || workflow.uploading"
              @click="uploadPending"
            >
              Upload Media
            </button>
            <button
              type="button"
              class="ghost"
              :disabled="!workflow.lastUploadFilename"
              @click="workflow.refreshLatestFile"
            >
              Refresh Latest
            </button>
          </div>
        </div>
        <div class="transcript-column">
          <label class="heading">Transcript</label>
          <textarea
            v-model="workflow.rawText"
            rows="5"
            placeholder="Paste transcript for alignment and caption generation"
          ></textarea>
          <div class="transcript-actions">
            <select v-model="workflow.language">
              <option value="pt-BR">Portugu�s</option>
              <option value="en">English</option>
            </select>
            <button
              type="button"
              class="ghost"
              :disabled="!workflow.lastUploadFilename || !workflow.rawText"
              @click="alignAudio"
            >
              Align Audio
            </button>
            <button
              type="button"
              class="primary"
              :disabled="!workflow.lastUploadFilename || !workflow.rawText"
              @click="generateSubtitles"
            >
              Generate Captions
            </button>
            <button
              type="button"
              class="ghost"
              :disabled="!alignmentTokens.length"
              @click="smartSplit"
            >
              Smart Split
            </button>
          </div>
        </div>
      </section>

      <section class="workspace" v-if="hasLayers">
        <div class="preview-column">
          <VideoPlayer
            :video-src="videoSource"
            :filename="workflow.lastUploadFilename || ''"
            :current-time="playback.currentTime"
            :layers="activeLayers"
            :aspect-ratio="editorStore.aspectRatio"
            :active-layer-ids="editorStore.selection.order"
            :safe-zone-enabled="editorStore.safeZoneEnabled"
            :grid-visible="editorStore.gridVisible"
            @update:currentTime="editorStore.setPlaybackTime"
            @update:duration="editorStore.setPlaybackDuration"
            @update:playing="editorStore.setPlaybackState"
            @select-layer="selectLayer"
            @hover-layer="setHoverLayer"
            @double-click-layer="openRenameLayer"
            @update-layer-position="updateLayerPosition"
          />
          <div class="preview-controls">
            <RatioSafeZones
              :presets="aspectPresets"
              :active-preset-id="editorStore.aspectRatio.id"
              :safe-zone-enabled="editorStore.safeZoneEnabled"
              @select="editorStore.setAspectRatio"
              @toggle-safe-zone="editorStore.toggleSafeZone"
            />
          </div>
        </div>
        <StylePanel
          :layer="selectedLayer"
          :templates="editorStore.templates"
          @apply-template="applyTemplate"
          @update-style="updateLayerStyle"
          @update-animation="updateLayerAnimation"
          @toggle-karaoke="toggleKaraoke"
          @update-karaoke="updateKaraoke"
          @rename-layer="openRenameLayer"
        />
      </section>

      <section class="timeline-section" v-if="hasLayers">
        <TimelineEditor
          :tracks="editorStore.orderedTracks"
          :layers="editorStore.layers"
          :current-time="playback.currentTime"
          :duration="playback.duration"
          :active-layer-ids="editorStore.selection.order"
          :snapping="snapping"
          :snap-interval="snapInterval"
          @update:time="editorStore.setPlaybackTime"
          @update-layer="updateLayerTiming"
          @select-layer="selectLayer"
          @toggle-snapping="value => (snapping = value)"
          @create-track="createTrack"
          @duplicate-selection="duplicateSelection"
          @reorder-layer="onReorderLayer"
          @reorder-track="onReorderTrack"
          @update-snap-interval="value => (snapInterval = value)"
        />
      </section>

      <section class="export-bar" v-if="hasLayers">
        <button type="button" class="ghost" @click="exportCaptions('srt')">
          Export SRT
        </button>
        <button type="button" class="ghost" @click="exportCaptions('vtt')">
          Export VTT
        </button>
        <button
          type="button"
          class="primary"
          :disabled="!canExportVideo"
          @click="exportVideoWithCaptions"
        >
          Export Video with Captions
        </button>
      </section>
    </div>
  </DefaultLayout>
</template>

<script lang="ts">
// @ts-nocheck
import {
  computed,
  defineComponent,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from 'vue';
import DefaultLayout from '@/layouts/DefaultLayout.vue';
import VideoPlayer from '@/components/video/VideoPlayer.vue';
import StylePanel from '@/components/subtitles/StylePanel.vue';
import TimelineEditor from '@/components/subtitles/TimelineEditor.vue';
import RatioSafeZones from '@/components/video/RatioSafeZones.vue';
import { useSubtitleWorkflow } from '@/composables/useSubtitleWorkflow';
import { useEditorStore } from '@/store/editor-store';
import { useSubtitleStore } from '@/store/subtitleStore';
import { ASPECT_RATIO_PRESETS } from '@/modules/editor/editor-constants';
import type {
  EditorTemplate,
  KaraokeWord,
  TextLayer,
} from '@/modules/editor/editor-types';
import { exportSubtitles, downloadBlob } from '@/api/subtitleExportService';
import { exportVideoWithSubtitles } from '@/api/videoExportService';

interface AlignmentToken {
  text: string;
  start_ms: number;
  end_ms: number;
  type?: string;
}

export default defineComponent({
  name: 'EditorPage',
  components: {
    DefaultLayout,
    VideoPlayer,
    StylePanel,
    TimelineEditor,
    RatioSafeZones,
  },
  setup() {
    const workflow = useSubtitleWorkflow();
    const editorStore = useEditorStore();
    const subtitleStore = useSubtitleStore();

    const fileInputRef = ref<HTMLInputElement | null>(null);
    const pendingFile = ref<File | null>(null);
    const videoSource = ref<string>('');
    const autoUpload = ref(true);
    const snapping = ref(true);
  const snapInterval = ref(0.05);
    const exportingVideo = ref(false);
    const exportMessage = ref('');

    const aspectPresets = ASPECT_RATIO_PRESETS;

    const playback = computed(() => editorStore.playback);
    const selectedLayer = computed(() => editorStore.primaryLayer);
    const activeLayers = computed(() => editorStore.orderedLayers);
    const hasLayers = computed(() => activeLayers.value.length > 0);

    const alignmentTokens = computed<AlignmentToken[]>(() => {
      const tokens = workflow.alignment.value?.alignment?.tokens ?? [];
      return tokens
        .filter((token: any) => token)
        .map((token: any) => ({
          text: token.text || token.word || '',
          start_ms: token.start_ms ?? token.start_time ?? 0,
          end_ms: token.end_ms ?? token.end_time ?? 0,
          type: token.type as string | undefined,
        }))
        .filter(
          (token: AlignmentToken) => token.text && token.end_ms > token.start_ms
        );
    });

    function openFilePicker() {
      fileInputRef.value?.click();
    }

    function revokeVideoSource() {
      if (videoSource.value.startsWith('blob:')) {
        URL.revokeObjectURL(videoSource.value);
      }
    }

    function isVideoFile(file: File) {
      return file.type.startsWith('video');
    }

    function onFileChange(event: Event) {
      const files = (event.target as HTMLInputElement).files;
      if (!files?.length) return;
      const file = files[0];
      pendingFile.value = file;
      if (isVideoFile(file)) {
        revokeVideoSource();
        videoSource.value = URL.createObjectURL(file);
      }
      if (autoUpload.value) {
        uploadPending();
      }
    }

    async function uploadPending() {
      if (!pendingFile.value) return;
      try {
        await workflow.doUpload(pendingFile.value);
      } catch (error) {
        console.error('Upload failed', error);
      }
    }

    async function alignAudio() {
      try {
        await workflow.doAlign();
      } catch (error) {
        console.error('Alignment failed', error);
      }
    }

    function mapTokensToWords(start: number, end: number): KaraokeWord[] {
      const startMs = start * 1000;
      const endMs = end * 1000;
      return alignmentTokens.value
        .filter(
          (token: AlignmentToken) =>
            token.start_ms >= startMs - 80 && token.end_ms <= endMs + 80
        )
        .map((token: AlignmentToken, index: number) => ({
          id: `word-${token.start_ms}-${index}`,
          text: token.text.trim(),
          start: token.start_ms / 1000,
          end: token.end_ms / 1000,
        }))
        .filter(
          (word: KaraokeWord) => word.text.length > 0 && word.end > word.start
        );
    }

    async function generateSubtitles() {
      try {
        await workflow.doGenerate();
        hydrateEditorFromSubtitleStore();
      } catch (error) {
        console.error('Generation failed', error);
      }
    }

    function hydrateEditorFromSubtitleStore() {
      const cues = subtitleStore.cues.value;
      if (!cues.length) return;
      editorStore.reset();
      const hydratedCues = cues.map((cue: any, index: number) => ({
        id: cue.id ?? `cue-${index}`,
        text: cue.text,
        start: cue.start,
        end: cue.end,
        words: mapTokensToWords(cue.start, cue.end),
      }));
      editorStore.hydrateFromCues({ cues: hydratedCues });
      editorStore.setPlaybackDuration(
        Math.max(
          playback.value.duration,
          hydratedCues.at(-1)?.end ?? playback.value.duration
        )
      );
    }

    function applyTemplate(templateId: string) {
      if (!selectedLayer.value) return;
      editorStore.applyTemplateToLayer(selectedLayer.value.id, templateId);
    }

    function updateLayerStyle(style: Partial<TextLayer['style']>) {
      if (!selectedLayer.value) return;
      editorStore.updateLayer({ layerId: selectedLayer.value.id, style });
    }

    function updateLayerAnimation(kind: string) {
      if (!selectedLayer.value) return;
      editorStore.updateLayer({
        layerId: selectedLayer.value.id,
        animation: { kind },
      });
    }

    function toggleKaraoke(enabled: boolean) {
      if (!selectedLayer.value) return;
      const words =
        enabled && !selectedLayer.value.karaoke.words.length
          ? mapTokensToWords(selectedLayer.value.start, selectedLayer.value.end)
          : selectedLayer.value.karaoke.words;
      editorStore.updateLayer({
        layerId: selectedLayer.value.id,
        karaoke: { enabled, words },
      });
    }

    function updateKaraoke(patch: Partial<TextLayer['karaoke']>) {
      if (!selectedLayer.value) return;
      editorStore.updateLayer({
        layerId: selectedLayer.value.id,
        karaoke: patch,
      });
    }

    function selectLayer(layerId: string) {
      if (!layerId) {
        editorStore.clearSelection();
        return;
      }
      editorStore.selectLayers([layerId]);
    }

    function setHoverLayer(layerId: string | null) {
      editorStore.setHoverLayer(layerId);
    }

    function updateLayerPosition(payload: {
      layerId: string;
      position: { x: number; y: number };
    }) {
      editorStore.updateLayer({
        layerId: payload.layerId,
        position: payload.position,
      });
    }

    function updateLayerTiming(payload: {
      layerId: string;
      start: number;
      end: number;
    }) {
      editorStore.updateLayer({
        layerId: payload.layerId,
        start: payload.start,
        end: payload.end,
      });
    }

    function createTrack() {
      editorStore.addTrack();
    }

    function duplicateSelection() {
      const firstSelected = editorStore.selection.order[0];
      if (firstSelected) {
        editorStore.duplicateLayer(firstSelected);
      }
    }

    function onReorderLayer(payload: { layerId: string; targetTrackId: string; targetIndex: number }) {
      const targetTrack = editorStore.tracks[payload.targetTrackId];
      if (!targetTrack) return;
      const index = payload.targetIndex === -1 ? targetTrack.layerIds.length : payload.targetIndex;
      editorStore.reorderLayer(payload.layerId, index, payload.targetTrackId);
    }

    function onReorderTrack(payload: { trackId: string; targetIndex: number }) {
      editorStore.reorderTrack(payload.trackId, payload.targetIndex);
    }

    function smartSplit() {
      const tokens = alignmentTokens.value;
      if (!tokens.length) return;
      const groups: AlignmentToken[][] = [];
      let currentGroup: AlignmentToken[] = [];
      tokens.forEach((token: AlignmentToken, index: number) => {
        if (!currentGroup.length) {
          currentGroup.push(token);
          return;
        }
        const previous = currentGroup[currentGroup.length - 1];
        const gap = token.start_ms - previous.end_ms;
        const currentText = currentGroup.map(t => t.text).join(' ');
        if (gap > 600 || currentText.length > 64) {
          groups.push(currentGroup);
          currentGroup = [token];
        } else {
          currentGroup.push(token);
        }
        if (index === tokens.length - 1) {
          groups.push(currentGroup);
        }
      });
      if (!groups.length) return;
      editorStore.reset();
      subtitleStore.setSubtitles(
        groups.map((group, index) => ({
          id: `smart-${index}`,
          text: group.map(t => t.text).join(' '),
          start: Math.max(group[0].start_ms / 1000, 0),
          end:
            Math.max(
              group.at(-1)?.end_ms ?? group[0].end_ms,
              group[0].start_ms
            ) / 1000,
          confidence: 1,
        }))
      );
      const mapped = groups.map((group, index) => ({
        id: `smart-${index}`,
        text: group.map(t => t.text).join(' '),
        start: group[0].start_ms / 1000,
        end: (group.at(-1)?.end_ms ?? group[0].end_ms) / 1000,
        words: group.map((token, wordIndex) => ({
          id: `smart-${index}-${wordIndex}`,
          text: token.text,
          start: token.start_ms / 1000,
          end: token.end_ms / 1000,
        })),
      }));
      editorStore.hydrateFromCues({ cues: mapped });
    }

    async function exportCaptions(format: 'srt' | 'vtt') {
      try {
        const blob = await exportSubtitles(format, subtitleStore.cues.value);
        downloadBlob(blob, `captions.${format}`);
      } catch (error) {
        console.error('Export failed', error);
      }
    }

    const canExportVideo = computed(() =>
      Boolean(workflow.lastUploadFilename && hasLayers.value)
    );

    const presetMap: Record<string, string> = {
      '9:16': 'instagram_reel',
      '1:1': 'instagram_story',
      '16:9': 'youtube_horizontal',
    };

    function resolveVideoPath(filename: string) {
      return `uploads/audio/${filename}`;
    }

    async function exportVideoWithCaptions() {
      if (!workflow.lastUploadFilename || !editorStore.orderedLayers.length)
        return;
      exportingVideo.value = true;
      exportMessage.value = 'Exporting...';
      try {
        const segments = editorStore.orderedLayers.map((layer: any) => ({
          id: layer.id,
          text: layer.text,
          start_time: layer.start,
          end_time: layer.end,
          confidence: 1,
          style_overrides: layer.style,
          karaoke: layer.karaoke,
        }));
        const response = await exportVideoWithSubtitles({
          inputVideoPath: resolveVideoPath(workflow.lastUploadFilename),
          outputFilename: `${workflow.lastUploadFilename.replace(/\.[^.]+$/, '')}-styled.mp4`,
          presetName: presetMap[editorStore.aspectRatio.id] || 'instagram_reel',
          subtitleSegments: segments,
          customSettings: {
            animations: editorStore.orderedLayers.map((layer: any) => ({
              id: layer.id,
              animation: layer.animation,
            })),
            aspectRatio: editorStore.aspectRatio,
            safeZone: editorStore.safeZoneEnabled,
          },
        });
        if (response.success) {
          exportMessage.value = 'Export ready';
          if (response.download_url) {
            window.open(response.download_url, '_blank');
          }
        } else {
          exportMessage.value = response.error || 'Export failed';
        }
      } catch (error) {
        console.error('Video export failed', error);
        exportMessage.value = 'Export failed';
      } finally {
        setTimeout(() => {
          exportingVideo.value = false;
          exportMessage.value = '';
        }, 4000);
      }
    }

    function openRenameLayer() {
      if (!selectedLayer.value) return;
      const nextName = window.prompt('Rename layer', selectedLayer.value.name);
      if (nextName && nextName.trim().length) {
        editorStore.updateLayer({
          layerId: selectedLayer.value.id,
          name: nextName.trim(),
        });
      }
    }

    function mapPresetsToTemplates(
      presets: Record<string, any>
    ): EditorTemplate[] {
      return Object.entries(presets).map(([id, preset]) => ({
        id: `preset-${id}`,
        name: preset.name || id,
        description:
          `${preset.aspect_ratio ?? ''} ${preset.resolution ?? ''}`.trim(),
        style: preset.style || {},
      }));
    }

    watch(
      () => workflow.presets.value,
      (presets: unknown) => {
        if (!presets) return;
        const templates = mapPresetsToTemplates(presets as Record<string, any>);
        const base = editorStore.templates.filter(
          (template: any) => !template.id.startsWith('preset-')
        );
        editorStore.updateTemplates([...base, ...templates]);
      }
    );

    onMounted(() => {
      workflow.fetchPresets();
    });

    onBeforeUnmount(() => {
      revokeVideoSource();
    });

    return {
      workflow,
      editorStore,
      playback,
      selectedLayer,
      activeLayers,
      hasLayers,
      fileInputRef,
      pendingFile,
      videoSource,
      autoUpload,
      snapping,
      aspectPresets,
      alignmentTokens,
      openFilePicker,
      onFileChange,
      uploadPending,
      alignAudio,
      generateSubtitles,
      applyTemplate,
      updateLayerStyle,
      updateLayerAnimation,
      toggleKaraoke,
      updateKaraoke,
      selectLayer,
      setHoverLayer,
      updateLayerPosition,
      updateLayerTiming,
      createTrack,
      duplicateSelection,
      smartSplit,
      exportCaptions,
      exportVideoWithCaptions,
      canExportVideo,
      exportingVideo,
      exportMessage,
    };
  },
});
</script>

<style scoped>
.editor-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  color: #f3f7ff;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.page-header h1 {
  margin: 0;
  font-size: 1.8rem;
}

.page-header p {
  margin: 4px 0 0;
  opacity: 0.7;
}

.status-pills {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pill {
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(0, 173, 255, 0.15);
  border: 1px solid rgba(0, 173, 255, 0.4);
  font-size: 0.7rem;
}

.pill.error {
  background: rgba(255, 82, 82, 0.2);
  border-color: rgba(255, 82, 82, 0.6);
}

.ingest-card {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;
  padding: 20px;
  border-radius: 16px;
  background: #10141d;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.file-column,
.transcript-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.heading {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  opacity: 0.75;
}

.file-picker {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hidden {
  display: none;
}

.primary {
  background: linear-gradient(135deg, #00adff, #34ffd9);
  border: none;
  color: #000;
  padding: 10px 16px;
  border-radius: 8px;
  font-weight: 600;
}

.ghost {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #f3f7ff;
  padding: 8px 14px;
  border-radius: 8px;
}

.file-meta {
  font-size: 0.75rem;
  opacity: 0.65;
}

.toggles {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.75rem;
}

.actions {
  display: flex;
  gap: 10px;
}

.transcript-column textarea {
  width: 100%;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 12px;
  color: inherit;
}

.transcript-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.workspace {
  display: flex;
  gap: 24px;
}

.preview-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.preview-controls {
  padding: 12px;
  border-radius: 12px;
  background: #10141d;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.timeline-section {
  border-radius: 16px;
  background: #0d1118;
  border: 1px solid rgba(255, 255, 255, 0.04);
  padding: 16px;
}

.export-bar {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
</style>
