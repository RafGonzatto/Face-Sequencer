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
          <span v-if="uploading" class="pill">Uploading...</span>
          <span v-if="aligning" class="pill">Aligning...</span>
          <span v-if="generating" class="pill">Generating...</span>
          <span v-if="exportingVideo" class="pill">Exporting...</span>
          <span v-if="error" class="pill error">{{ error }}</span>
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
            <span v-else-if="lastUploadFilename" class="file-meta"
              >Server: {{ lastUploadFilename }}</span
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
              :disabled="!pendingFile || uploading"
              @click="uploadPending"
            >
              Upload Media
            </button>
            <button
              type="button"
              class="ghost"
              :disabled="!lastUploadFilename"
              @click="workflow.refreshLatestFile"
            >
              Refresh Latest
            </button>
          </div>
        </div>
        <div class="transcript-column">
          <label class="heading">Transcript</label>
          <textarea
            v-model="localTranscript"
            rows="5"
            placeholder="Paste transcript for alignment and caption generation"
            @input="
              () =>
                console.log('TEXTAREA2 INPUT:', localTranscript.length, 'chars')
            "
          ></textarea>
          <div class="transcript-actions">
            <select v-model="language">
              <option value="pt-BR">Português</option>
              <option value="en">English</option>
            </select>
            <button type="button" class="ghost" @click="alignAudio">
              Align Audio
            </button>
            <button type="button" class="primary" @click="generateSubtitles">
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
            <label class="inline-control">
              <input type="checkbox" v-model="charLevel" />
              Separação por caracteres (karaokê)
            </label>
            <label class="inline-control">
              <input type="checkbox" v-model="forceUppercase" />
              Converter para MAIÚSCULAS
            </label>
            <label class="inline-control">
              <input type="checkbox" v-model="wrapLinesOnExport" />
              Quebrar linhas no SRT (20–26 colunas)
            </label>
            <div
              v-if="wrapLinesOnExport"
              class="inline-control"
              style="gap: 8px; align-items: center"
            >
              <small>mín:</small>
              <input
                type="number"
                v-model.number="wrapMin"
                min="10"
                max="80"
                style="width: 64px"
              />
              <small>máx:</small>
              <input
                type="number"
                v-model.number="wrapMax"
                min="10"
                max="80"
                style="width: 64px"
              />
            </div>
            <!-- Debug panel to visualize state after generation -->
            <div style="margin-left: auto; font-size: 12px; opacity: 0.8">
              <span>hasLayers: {{ hasLayers ? 'yes' : 'no' }}</span>
              <span style="margin-left: 8px"
                >layers: {{ activeLayers.length }}</span
              >
              <span style="margin-left: 8px"
                >cues:
                {{
                  Array.isArray(subtitleStore.cues)
                    ? subtitleStore.cues.length
                    : subtitleStore.cues?.value?.length || 0
                }}</span
              >
              <button
                class="ghost"
                type="button"
                style="margin-left: 8px"
                @click="hydrateEditorFromSubtitleStore()"
              >
                Hydrate now
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- Alterado: antes só mostrava workspace se já existissem layers.
           Agora mostramos assim que há um vídeo selecionado/upload (videoSource ou lastUploadFilename) -->
      <section class="workspace" v-if="videoSource || lastUploadFilename">
        <div class="preview-column">
          <VideoPlayer
            ref="playerRef"
            :video-src="videoSrcEffective"
            :filename="lastUploadFilename || ''"
            :current-time="playback.currentTime"
            :layers="activeLayers"
            :aspect-ratio="editorStore.aspectRatio"
            :active-layer-ids="editorStore.selection.order"
            :safe-zone-enabled="editorStore.safeZoneEnabled"
            :grid-visible="editorStore.gridVisible"
            :backend-preview-url="backendPreviewUrl"
            :show-backend-preview="backendPreviewEnabled && !playback.isPlaying"
            @update:currentTime="editorStore.setPlaybackTime"
            @update:duration="editorStore.setPlaybackDuration"
            @update:playing="editorStore.setPlaybackState"
            @select-layer="selectLayer"
            @hover-layer="setHoverLayer"
            @double-click-layer="openRenameLayer"
            @update-layer-position="updateLayerPosition"
          />
          <div v-if="!hasLayers" class="no-layers-hint">
            <p>
              <strong>Pré-visualização carregada.</strong> Ainda não há layers
              de texto porque você não gerou legendas.
            </p>
            <ol>
              <li>Insira / cole um transcript no campo Transcript.</li>
              <li>
                Clique em "Align Audio" (opcional) e depois "Generate Captions".
              </li>
              <li>As legendas aparecerão aqui e você poderá editar.</li>
            </ol>
          </div>
          <div class="preview-controls">
            <RatioSafeZones
              :presets="aspectPresets"
              :active-preset-id="editorStore.aspectRatio.id"
              :safe-zone-enabled="editorStore.safeZoneEnabled"
              @select="editorStore.setAspectRatio"
              @toggle-safe-zone="editorStore.toggleSafeZone"
            />
            <div class="backend-toggle">
              <label>
                <input type="checkbox" v-model="backendPreviewEnabled" />
                Backend‑aligned preview (pixel‑perfect)
              </label>
              <small
                v-if="backendPreviewEnabled"
                style="opacity: 0.75; display: block; margin-top: 4px"
              >
                Pausa o vídeo para ver o frame gerado pelo backend.
              </small>
            </div>
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
          Exportar SRT
        </button>
        <button type="button" class="ghost" @click="exportCaptions('vtt')">
          Exportar VTT
        </button>
        <button
          type="button"
          class="ghost"
          :disabled="!canExportVideo"
          @click="quickExportWebM"
          title="Experimental: grava a visualização (WebM) no navegador"
        >
          Quick export (browser • WebM)
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
  nextTick,
} from 'vue';
import DefaultLayout from '@/layouts/DefaultLayout.vue';
import VideoPlayer from '@/components/video/VideoPlayer.vue';
import StylePanel from '@/components/subtitles/StylePanel.vue';
import TimelineEditor from '@/components/subtitles/TimelineEditor.vue';
import RatioSafeZones from '@/components/video/RatioSafeZones.vue';
import { useSubtitleWorkflow } from '@/composables/useSubtitleWorkflow';
import { useEditorStore } from '@/store/editor-store';
import { storeToRefs } from 'pinia';
import { useSubtitleStore } from '@/store/subtitleStore';
import { ASPECT_RATIO_PRESETS } from '@/modules/editor/editor-constants';
import type {
  EditorTemplate,
  KaraokeWord,
  TextLayer,
} from '@/modules/editor/editor-types';
import { exportSubtitles, downloadBlob } from '@/api/subtitleExportService';
import { exportVideoWithSubtitles } from '@/api/videoExportService';
import { getPreviewFrameUrl } from '@/api/previewService';

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
    // Pinia getters/refs reativos
    const { orderedLayers, selection } = storeToRefs(editorStore as any);
    const subtitleStore = useSubtitleStore();

    const fileInputRef = ref<HTMLInputElement | null>(null);
    const pendingFile = ref<File | null>(null);
    const videoSource = ref<string>('');
    const autoUpload = ref(true);
    const snapping = ref(true);
    const snapInterval = ref(0.05);
    const charLevel = ref(false);
    const forceUppercase = ref(false);
    const wrapLinesOnExport = ref(false);
    const wrapMin = ref(20);
    const wrapMax = ref(26);
    const exportingVideo = ref(false);
    const exportMessage = ref('');
    const backendPreviewEnabled = ref(false);
    const backendPreviewUrl = ref<string>('');
    const playerRef = ref<any | null>(null);
    let lastBackendObjectUrl: string | null = null;
    // Sequencing to avoid races where an older response revokes the newest blob URL
    let previewRequestSeq = 0;
    let lastAppliedSeq = 0;

    // Ref local para o transcript com sincronização bidirecional
    const localTranscript = ref('');

    // Sincronizar local -> workflow
    watch(localTranscript, newVal => {
      workflow.rawText.value = newVal;
      console.log('LOCAL TRANSCRIPT -> WORKFLOW:', {
        length: newVal?.length || 0,
        preview: newVal?.substring(0, 50) || '(vazio)',
      });
    });

    // Sincronizar workflow -> local (caso workflow mude por outro motivo)
    watch(
      () => workflow.rawText.value,
      newVal => {
        if (newVal !== localTranscript.value) {
          localTranscript.value = newVal;
          console.log('WORKFLOW -> LOCAL TRANSCRIPT:', {
            length: newVal?.length || 0,
          });
        }
      },
      { immediate: true }
    );

    const aspectPresets = ASPECT_RATIO_PRESETS;

    // Expose top-level refs for template reactivity (avoid nested ref unwrapping pitfalls)
    const uploading = workflow.uploading;
    const aligning = workflow.aligning;
    const generating = workflow.generating;
    const error = workflow.error;
    const lastUploadFilename = workflow.lastUploadFilename;
    const language = workflow.language;

    const playback = computed(() => editorStore.playback);
    const selectedLayer = computed(() => editorStore.primaryLayer);
    // orderedLayers via storeToRefs garante reatividade na template
    const activeLayers = orderedLayers;
    const hasLayers = computed(() => (activeLayers.value?.length || 0) > 0);

    // Debug: observe when layers change and when hasLayers flips
    watch(
      () => Object.keys(editorStore.layers).length,
      len => {
        console.log('EDITOR DEBUG - layers count changed', { count: len });
      },
      { immediate: true }
    );
    watch(
      () => activeLayers.value,
      layers => {
        console.log('EDITOR DEBUG - orderedLayers update', {
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
      () => hasLayers.value,
      value => {
        console.log('EDITOR DEBUG - hasLayers changed', { hasLayers: value });
      },
      { immediate: true }
    );

    // Auto-hydrate editor layers when new cues land in subtitleStore
    let autoHydratedOnce = false;
    watch(
      () => subtitleStore.cues,
      (cues: any) => {
        const arr = Array.isArray(cues) ? cues : cues?.value;
        const count = Array.isArray(arr) ? arr.length : 0;
        if (count > 0 && !hasLayers.value && !autoHydratedOnce) {
          hydrateEditorFromSubtitleStore();
          autoHydratedOnce = true;
        }
      },
      { immediate: true, deep: true }
    );

    const alignmentTokens = computed<AlignmentToken[]>(() => {
      const tokens = workflow.alignment.value?.tokens ?? [];
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

    // Computeds to avoid nested ref pitfall in templates
    const canAlign = computed(() =>
      Boolean(
        workflow.lastUploadFilename.value && workflow.rawText.value?.trim()
      )
    );
    const canGenerate = computed(() =>
      Boolean(
        workflow.lastUploadFilename.value && workflow.rawText.value?.trim()
      )
    );

    function openFilePicker() {
      console.log('FILE PICKER - (1/1) abrir seletor: clique no botão');
      fileInputRef.value?.click();
    }

    function revokeVideoSource() {
      if (videoSource.value.startsWith('blob:')) {
        URL.revokeObjectURL(videoSource.value);
      }
    }

    function revokeBackendPreviewUrl() {
      if (lastBackendObjectUrl) {
        URL.revokeObjectURL(lastBackendObjectUrl);
        lastBackendObjectUrl = null;
      }
      backendPreviewUrl.value = '';
    }

    function isVideoFile(file: File) {
      return file.type.startsWith('video');
    }

    function onFileChange(event: Event) {
      const files = (event.target as HTMLInputElement).files;
      if (!files?.length) return;
      const file = files[0];
      pendingFile.value = file;
      console.log(
        'UPLOAD VIDEO - Seleção de arquivo (A) arquivo selecionado no input',
        {
          name: file.name,
          size_bytes: file.size,
          size_mb: (file.size / (1024 * 1024)).toFixed(2),
          type: file.type,
          lastUploadFilenameAtual: workflow.lastUploadFilename.value,
          isVideo: isVideoFile(file),
          timestamp: new Date().toISOString(),
        }
      );
      if (isVideoFile(file)) {
        revokeVideoSource();
        console.log(
          'UPLOAD VIDEO - Pré-visualização (B) gerando ObjectURL anteriorRevogado',
          {
            tinhaBlobAnterior: videoSource.value.startsWith('blob:'),
          }
        );
        videoSource.value = URL.createObjectURL(file);
        console.log('UPLOAD VIDEO - Pré-visualização (C) object URL criado', {
          objectUrl: videoSource.value,
          dica: 'Será usado como src do <video> antes do upload finalizar',
        });
      }
      if (autoUpload.value) {
        console.log(
          'UPLOAD VIDEO - Disparo automático (D) chamando uploadPending()',
          {
            autoUpload: autoUpload.value,
          }
        );
        uploadPending();
      }
      if (!isVideoFile(file)) {
        console.log(
          'UPLOAD VIDEO - Aviso: arquivo não é video/* portanto preview visual pode não aparecer até pós-processamento',
          { type: file.type }
        );
      }
    }

    async function uploadPending() {
      if (!pendingFile.value) return;
      try {
        console.log('UPLOAD UI - (1/2) iniciar upload pendente', {
          filename: pendingFile.value.name,
          size_mb: (pendingFile.value.size / (1024 * 1024)).toFixed(2),
          isVideo: isVideoFile(pendingFile.value),
        });
        console.log(
          'UPLOAD VIDEO - Ponte para workflow (pré 1/4) Chamando workflow.doUpload',
          {
            filename: pendingFile.value.name,
          }
        );
        await workflow.doUpload(pendingFile.value);
        console.log('UPLOAD UI - (2/2) upload concluído', {
          serverFilename: lastUploadFilename.value,
          videoSrcEffective: videoSrcEffective,
        });
      } catch (error) {
        console.error('Upload failed', error);
      }
    }

    async function alignAudio() {
      try {
        console.log('ALIGN UI - (1/2) iniciar alinhamento', {
          hasFilename: !!lastUploadFilename.value,
          text_len: workflow.rawText.value?.trim()?.length || 0,
          language: language.value,
        });
        await workflow.doAlign();
        const tok = alignmentTokens.value.length;
        console.log('ALIGN UI - (2/2) concluído com sucesso', {
          tokens: tok,
          sample: alignmentTokens.value.slice(0, 3),
        });
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
        // GARANTIR que localTranscript foi sincronizado com workflow.rawText
        console.log('GEN UI - (0/4) PRÉ-SYNC', {
          localTranscript_length: localTranscript.value?.length || 0,
          workflow_rawText_length: workflow.rawText.value?.length || 0,
        });

        // Forçar sincronização explícita (caso watcher não tenha executado ainda)
        if (
          localTranscript.value &&
          localTranscript.value !== workflow.rawText.value
        ) {
          console.warn('GEN UI - SYNC MANUAL NECESSÁRIO');
          workflow.rawText.value = localTranscript.value;
        }

        console.log('GEN UI - (1/4) iniciar geração a partir da UI', {
          rawText_length: workflow.rawText.value?.length || 0,
          rawText_preview:
            workflow.rawText.value?.substring(0, 50) || '(vazio)',
          rawText_full: workflow.rawText.value,
          lastUploadFilename: workflow.lastUploadFilename.value,
        });
        await workflow.doGenerate({
          character_level: charLevel.value,
          uppercase: forceUppercase.value,
        });
        console.log('GEN UI - (2/4) retorno do workflow');
        const raw =
          (Array.isArray(subtitleStore.cues)
            ? (subtitleStore.cues as any)
            : (subtitleStore.cues?.value as any)) ?? [];
        if (!Array.isArray(raw)) {
          console.warn(
            'GEN UI - (3/4) abortado: subtitleStore.cues não é array',
            {
              type: typeof raw,
              value: raw,
            }
          );
          return;
        }
        if (!raw.length) {
          console.log(
            'GEN UI - (3/4) sem legendas retornadas; nada para hidratar'
          );
          return;
        }
        hydrateEditorFromSubtitleStore();
        console.log('GEN UI - (4/4) hidratação concluída');
      } catch (error) {
        console.error('Generation failed', error);
      }
    }

    async function hydrateEditorFromSubtitleStore() {
      console.log('HYDRATE EDITOR - (1/4) verificar cues no store');
      const raw =
        (Array.isArray(subtitleStore.cues)
          ? (subtitleStore.cues as any)
          : (subtitleStore.cues?.value as any)) ?? [];
      if (!Array.isArray(raw)) {
        console.warn(
          'HYDRATE EDITOR - (X) abortado: subtitleStore.cues não é array',
          {
            type: typeof raw,
            value: raw,
          }
        );
        return;
      }
      if (!raw.length) {
        console.log('HYDRATE EDITOR - (X) sem cues para hidratar');
        return;
      }
      const cues = raw;
      console.log('HYDRATE EDITOR - (2/4) cues recebidas', {
        count: cues.length,
      });
      editorStore.reset();
      const hydratedCues = cues.map((cue: any, index: number) => ({
        id: cue.id ?? `cue-${index}`,
        text: cue.text,
        start: cue.start,
        end: cue.end,
        words: mapTokensToWords(cue.start, cue.end),
      }));
      console.log('HYDRATE EDITOR - (3/4) mapeadas para layers', {
        layers: hydratedCues.length,
        sample: hydratedCues.slice(0, 2),
      });
      editorStore.hydrateFromCues({ cues: hydratedCues });
      editorStore.setPlaybackDuration(
        Math.max(
          playback.value.duration,
          hydratedCues.at(-1)?.end ?? playback.value.duration
        )
      );
      console.log('HYDRATE EDITOR - (4/4) concluído', {
        layers: hydratedCues.length,
      });
      // Checagens pós-hidratação para confirmar reatividade
      console.log('POST-HYDRATE CHECK - imediato', {
        orderedLayers_len: editorStore.orderedLayers.length,
        layersKeys: Object.keys(editorStore.layers).length,
        selectionCount: editorStore.selection.order.length,
      });
      await nextTick();
      console.log('POST-HYDRATE CHECK - nextTick', {
        orderedLayers_len: editorStore.orderedLayers.length,
        layersKeys: Object.keys(editorStore.layers).length,
        selectionCount: editorStore.selection.order.length,
      });
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

    function onReorderLayer(payload: {
      layerId: string;
      targetTrackId: string;
      targetIndex: number;
    }) {
      const targetTrack = editorStore.tracks[payload.targetTrackId];
      if (!targetTrack) return;
      const index =
        payload.targetIndex === -1
          ? targetTrack.layerIds.length
          : payload.targetIndex;
      editorStore.reorderLayer(payload.layerId, index, payload.targetTrackId);
    }

    function onReorderTrack(payload: { trackId: string; targetIndex: number }) {
      editorStore.reorderTrack(payload.trackId, payload.targetIndex);
    }

    function smartSplit() {
      const tokens = alignmentTokens.value;
      if (!tokens.length) return;
      console.log('SMART SPLIT - (1/3) iniciar', { tokens: tokens.length });
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
      console.log('SMART SPLIT - (2/3) grupos formados', {
        groups: groups.length,
      });
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
      console.log('SMART SPLIT - (3/3) concluído', {
        groups: groups.length,
        layers: mapped.length,
      });
    }

    async function exportCaptions(format: 'srt' | 'vtt') {
      try {
        console.log('EXPORT CAPTIONS - (1/2) iniciar', { format });
        const cuesArr = Array.isArray(subtitleStore.cues)
          ? (subtitleStore.cues as any)
          : (subtitleStore.cues?.value as any);
        const blob = await exportSubtitles(
          format,
          cuesArr || [],
          wrapLinesOnExport.value
            ? { wrap: true, wrapMin: wrapMin.value, wrapMax: wrapMax.value }
            : undefined
        );
        // Prefer using the uploaded filename as base for the subtitle file
        const base = (lastUploadFilename.value || 'captions').replace(
          /\.[^.]+$/,
          ''
        );
        downloadBlob(blob, `${base}.${format}`);
        console.log('EXPORT CAPTIONS - (2/2) concluído', {
          format,
          cueCount: Array.isArray(cuesArr) ? cuesArr.length : 0,
          blobType: blob.type,
        });
      } catch (error) {
        console.error('Export failed', error);
      }
    }

    const canExportVideo = computed(() =>
      Boolean(workflow.lastUploadFilename.value && hasLayers.value)
    );

    // Map UI aspect ratios to valid backend presets (names must exist in backend)
    const presetMap: Record<string, string> = {
      '9:16': 'instagram_reel',
      '1:1': 'custom_square',
      '16:9': 'facebook_video',
    };

    // URL para o browser usar como src do <video>
    function resolveVideoUrl(filename: string) {
      return `/uploads/audio/${filename}`;
    }
    // Caminho esperado pelo backend (filesystem relativo), SEM barra inicial
    function resolveVideoFsPath(filename: string) {
      return `uploads/audio/${filename}`;
    }

    const videoSrcEffective = computed(() => {
      if (videoSource.value) return videoSource.value;
      if (lastUploadFilename.value)
        return resolveVideoUrl(lastUploadFilename.value);
      return '';
    });

    watch(
      () => videoSrcEffective.value,
      (val: string) => {
        console.log('WORKSPACE - (1/1) vídeo disponível', {
          src: val || '(vazio)',
          hasBlob: !!val && val.startsWith('blob:'),
          isServerFile: !!val && val.includes('/uploads/'),
        });
        // invalidate backend preview when source changes
        revokeBackendPreviewUrl();
      },
      { immediate: true }
    );

    // Debounce helper for lightweight UI
    function debounce<T extends (...args: any[]) => void>(fn: T, wait = 150) {
      let t: number | undefined;
      return (...args: Parameters<T>) => {
        if (t) window.clearTimeout(t);
        t = window.setTimeout(() => fn(...args), wait);
      };
    }

    const requestBackendPreview = debounce(async () => {
      try {
        if (!backendPreviewEnabled.value) return;
        if (!workflow.lastUploadFilename.value) return;
        const mySeq = ++previewRequestSeq;
        // Build segments from editor state
        const segments = editorStore.orderedLayers.map((layer: any) => ({
          id: layer.id,
          text: layer.text,
          start_time: layer.start,
          end_time: layer.end,
          confidence: 1,
          style_overrides: { ...layer.style, position: layer.position },
          karaoke: layer.karaoke,
        }));
        const arId = editorStore.aspectRatio.id;
        const presetName =
          (arId === '9:16' && 'instagram_reel') ||
          (arId === '1:1' && 'custom_square') ||
          (arId === '16:9' && 'facebook_video') ||
          'instagram_reel';
        const url = await getPreviewFrameUrl({
          inputVideoPath: `uploads/audio/${workflow.lastUploadFilename.value}`,
          time: playback.value.currentTime,
          presetName,
          subtitleSegments: segments,
          customSettings: {
            aspectRatio: editorStore.aspectRatio,
            safeZone: editorStore.safeZoneEnabled,
          },
        });
        // If another request started after this one, discard this result
        if (mySeq < previewRequestSeq) {
          URL.revokeObjectURL(url);
          return;
        }
        // Apply new URL, then revoke the previously applied one
        const prev = lastBackendObjectUrl;
        backendPreviewUrl.value = url;
        lastBackendObjectUrl = url;
        lastAppliedSeq = mySeq;
        if (prev && prev !== url) {
          URL.revokeObjectURL(prev);
        }
      } catch (e) {
        console.warn('Backend preview request failed', e);
      }
    }, 150);

    // Update backend preview when paused/time/aspect changes
    watch(
      () => [
        backendPreviewEnabled.value,
        playback.value.isPlaying,
        playback.value.currentTime,
        editorStore.aspectRatio.id,
      ],
      () => {
        if (backendPreviewEnabled.value && !playback.value.isPlaying) {
          requestBackendPreview();
        }
      }
    );

    // Update backend preview when layers change (positions/styles/timing)
    watch(
      () => editorStore.orderedLayers,
      () => {
        if (backendPreviewEnabled.value && !playback.value.isPlaying) {
          requestBackendPreview();
        }
      },
      { deep: true }
    );

    async function exportVideoWithCaptions() {
      if (!lastUploadFilename.value || !editorStore.orderedLayers.length)
        return;
      exportingVideo.value = true;
      exportMessage.value = 'Exporting...';
      try {
        console.log('VIDEO EXPORT - (1/4) início preparação', {
          filename: lastUploadFilename.value,
          layerCount: editorStore.orderedLayers.length,
          aspect: editorStore.aspectRatio.id,
        });
        const segments = editorStore.orderedLayers.map((layer: any) => ({
          id: layer.id,
          text: layer.text,
          start_time: layer.start,
          end_time: layer.end,
          confidence: 1,
          style_overrides: {
            ...layer.style,
            position: layer.position,
          },
          karaoke: layer.karaoke,
        }));
        console.log(
          'VIDEO EXPORT - (2/4) chamando serviço exportVideoWithSubtitles',
          {
            segmentCount: segments.length,
          }
        );
        const response = await exportVideoWithSubtitles({
          inputVideoPath: resolveVideoFsPath(lastUploadFilename.value),
          outputFilename: `${String(lastUploadFilename.value).replace(/\.[^.]+$/, '')}-styled.mp4`,
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
        console.log('VIDEO EXPORT - (3/4) resposta serviço', {
          success: response.success,
          job_id: response.job_id,
          output: response.output_path,
        });
        if (response.success) {
          exportMessage.value = 'Export ready';
          // Start download immediately (prefer provided URL; fallback to job-based route)
          const dlUrl =
            response.download_url ||
            (response.job_id
              ? `/api/v4/export/download/${response.job_id}`
              : undefined);
          if (dlUrl) {
            const a = document.createElement('a');
            a.href = dlUrl;
            a.download = '';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
          }
        } else {
          exportMessage.value = response.error || 'Export failed';
        }
        console.log('VIDEO EXPORT - (4/4) finalizado', {
          exportMessage: exportMessage.value,
        });
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

    // Quick WebM export: records the composed <video> + canvas overlay as a WebM using MediaRecorder
    async function quickExportWebM() {
      try {
        const player = playerRef.value;
        if (!player) return;
        const videoEl: HTMLVideoElement | null = player.getVideoEl?.() || null;
        const overlayCanvas: HTMLCanvasElement | null =
          player.getOverlayCanvas?.() || null;
        const renderSize = player.getRenderSize?.() || null;
        if (!videoEl || !overlayCanvas || !renderSize) {
          console.warn('QuickExport: missing refs');
          return;
        }
        // Build a compositor canvas the same size as the visible render
        const comp = document.createElement('canvas');
        comp.width = overlayCanvas.width;
        comp.height = overlayCanvas.height;
        const ctx = comp.getContext('2d');
        if (!ctx) return;
        const stream = comp.captureStream(30);
        const opts: MediaRecorderOptions = {
          mimeType: 'video/webm;codecs=vp9',
        } as any;
        const recorder = new MediaRecorder(stream, opts);
        const chunks: BlobPart[] = [];
        recorder.ondataavailable = e => e.data && chunks.push(e.data);
        const done = new Promise<Blob>(resolve => {
          recorder.onstop = () =>
            resolve(new Blob(chunks, { type: 'video/webm' }));
        });
        recorder.start();
        const fps = 30;
        const interval = 1000 / fps;
        let running = true;
        let last = performance.now();
        // Ensure playback while recording
        videoEl.muted = true; // avoid echo
        await videoEl.play().catch(() => {});
        function loop(now: number) {
          if (!running) return;
          if (now - last >= interval) {
            last = now;
            // draw source video
            ctx.drawImage(videoEl, 0, 0, comp.width, comp.height);
            // draw overlay canvas on top
            ctx.drawImage(overlayCanvas, 0, 0);
          }
          requestAnimationFrame(loop);
        }
        requestAnimationFrame(loop);
        // Record for the duration of the timeline or until paused
        const durationMs = Math.min(
          (playback.value.duration || 10) * 1000,
          60000
        );
        await new Promise(r => setTimeout(r, durationMs));
        running = false;
        recorder.stop();
        const blob = await done;
        downloadBlob(
          blob,
          `${String(lastUploadFilename.value || 'export')}.webm`
        );
      } catch (err) {
        console.error('Quick export failed', err);
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
      // Fetch presets (may fail transiently if backend just restarted; frontend has a fallback)
      workflow.fetchPresets();
      // Recover last uploaded filename if the page was reloaded
      if (!workflow.lastUploadFilename.value && typeof window !== 'undefined') {
        const persisted = window.localStorage?.getItem('fs:lastUploadFilename');
        if (persisted) {
          console.log(
            'EDITOR MOUNT - recuperado lastUploadFilename do localStorage',
            { persisted }
          );
          workflow.lastUploadFilename.value = persisted;
        } else {
          console.log(
            'EDITOR MOUNT - tentando descobrir último arquivo no servidor'
          );
          workflow.refreshLatestFile().then(() => {
            if (workflow.lastUploadFilename.value) {
              console.log('EDITOR MOUNT - recuperado via API', {
                last: workflow.lastUploadFilename.value,
              });
            }
          });
        }
      }
    });

    onBeforeUnmount(() => {
      revokeVideoSource();
      revokeBackendPreviewUrl();
    });

    return {
      workflow,
      editorStore,
      subtitleStore,
      uploading,
      aligning,
      generating,
      error,
      lastUploadFilename,
      language,
      playback,
      selectedLayer,
      activeLayers,
      hasLayers,
      localTranscript,
      fileInputRef,
      pendingFile,
      videoSource,
      autoUpload,
      snapping,
      aspectPresets,
      alignmentTokens,
      canAlign,
      canGenerate,
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
      // Expose reorder handlers used by <TimelineEditor> to fix template warnings
      onReorderLayer,
      onReorderTrack,
      smartSplit,
      exportCaptions,
      exportVideoWithCaptions,
      canExportVideo,
      exportingVideo,
      exportMessage,
      playerRef,
      quickExportWebM,
      backendPreviewEnabled,
      backendPreviewUrl,
      hydrateEditorFromSubtitleStore,
      videoSrcEffective,
      openRenameLayer,
      snapInterval,
      charLevel,
      forceUppercase,
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

/* Responsividade geral do workspace */
@media (max-width: 1400px) {
  .workspace {
    gap: 16px;
  }
}

@media (max-width: 1200px) {
  .workspace {
    flex-direction: column;
  }
  .preview-column,
  .timeline-section {
    width: 100%;
  }
}

@media (max-width: 820px) {
  .transcript-actions {
    flex-wrap: wrap;
  }
  .transcript-actions button,
  .transcript-actions select {
    flex: 1 1 45%;
    min-width: 140px;
  }
}

.preview-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Quando não há layers, garantir que a coluna de preview não estoure a viewport vertical */
.preview-column {
  max-width: 100%;
}

.no-layers-hint {
  font-size: 0.8rem;
  line-height: 1.2rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.07);
  padding: 12px 14px;
  border-radius: 10px;
}

.no-layers-hint ol {
  margin: 6px 0 0 16px;
  padding: 0;
}

.no-layers-hint li {
  margin: 2px 0;
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
.inline-control {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  opacity: 0.9;
}
</style>
