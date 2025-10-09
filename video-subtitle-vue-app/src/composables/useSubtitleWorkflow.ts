import { ref } from 'vue';
import { uploadAudio, listAudioFiles, alignBasic } from '@/api/audioService';
import { generateSubtitles, listPresets } from '@/api/subtitlesService';
import { useSubtitleStore } from '@/store/subtitleStore';

export function useSubtitleWorkflow() {
  const uploading = ref(false);
  const aligning = ref(false);
  const generating = ref(false);
  const lastUploadFilename = ref<string | null>(null);
  const rawText = ref('');
  const language = ref('pt-BR');
  const platformPreset = ref('youtube-landscape');
  const presets = ref<Record<string, any>>({});
  const alignment = ref<any | null>(null);
  const error = ref<string | null>(null);
  const lastGenerationWasFallback = ref(false);

  const subtitleStore = useSubtitleStore();

  async function fetchPresets() {
    presets.value = await listPresets();
  }

  async function doUpload(file: File) {
    error.value = null;
    uploading.value = true;
    try {
      console.log('UPLOAD VIDEO - (1/4) Início do processo de upload', {
        filename: file.name,
        size_bytes: file.size,
        size_mb: (file.size / (1024 * 1024)).toFixed(2),
        type: file.type,
        lastUploadAnterior: lastUploadFilename.value,
        timestamp: new Date().toISOString(),
      });

      console.log(
        'UPLOAD VIDEO - (2/4) Preparando envio para API /audio/upload',
        {
          formField: 'audio',
          expectedResponse: 'filename, file_hash',
        }
      );

      const resp = await uploadAudio(file);

      console.log('UPLOAD VIDEO - (3/4) Resposta recebida do servidor', {
        serverFilename: resp.filename,
        file_hash: (resp as any).file_hash,
        receivedAt: new Date().toISOString(),
      });

      lastUploadFilename.value = resp.filename;
      try {
        if (typeof window !== 'undefined') {
          window.localStorage?.setItem('fs:lastUploadFilename', resp.filename);
        }
      } catch {}

      console.log('UPLOAD VIDEO - (4/4) Estado atualizado no client', {
        lastUploadFilename: lastUploadFilename.value,
        uploading: uploading.value,
        alignmentJaExiste: Boolean(alignment.value),
        possuiTextoBruto: rawText.value.length > 0,
      });
    } catch (e: any) {
      console.error('UPLOAD VIDEO - ERRO', {
        message: e?.message,
        stack: e?.stack,
      });
      error.value = e?.message || 'Upload failed';
    } finally {
      uploading.value = false;
    }
  }

  async function doAlign() {
    if (!lastUploadFilename.value || !rawText.value.trim()) {
      error.value = 'Arquivo ou texto faltando';
      return;
    }
    aligning.value = true;
    error.value = null;
    try {
      const resp = await alignBasic({
        filename: lastUploadFilename.value,
        text: rawText.value,
        language: language.value,
      });
      alignment.value = resp.alignment;
    } catch (e: any) {
      error.value = e?.message || 'Alinhamento falhou';
    } finally {
      aligning.value = false;
    }
  }

  function normalizeSpacedText(t: string) {
    // Collapse patterns like "C O M O" -> "COMO" but keep normal spaced words
    // Heuristic: if a token is single letters separated by spaces, remove spaces.
    return t
      .replace(/(?:^|\b)([A-ZÁÉÍÓÚÃÕÂÊÔÇ](?:\s+[A-ZÁÉÍÓÚÃÕÂÊÔÇ]))+(?=\b)/g, m =>
        m.replace(/\s+/g, '')
      )
      .replace(/(?:^|\b)([a-záéíóúãõâêôç](?:\s+[a-záéíóúãõâêôç]))+(?=\b)/g, m =>
        m.replace(/\s+/g, '')
      );
  }

  async function doGenerate(opts?: {
    character_level?: boolean;
    uppercase?: boolean;
  }) {
    console.log('SUBS WORKFLOW - generate DEBUG entrada', {
      rawText_value: rawText.value,
      rawText_length: rawText.value?.length || 0,
      rawText_trimmed_length: rawText.value?.trim()?.length || 0,
      lastUploadFilename: lastUploadFilename.value,
    });
    // Attempt auto-recovery of last filename if missing
    if (!lastUploadFilename.value) {
      console.warn(
        'SUBS WORKFLOW - generate: tentando recuperar último arquivo no servidor...'
      );
      try {
        await refreshLatestFile();
        console.log('SUBS WORKFLOW - generate: após refreshLatestFile', {
          recoveredFilename: lastUploadFilename.value,
        });
      } catch (e) {
        console.warn('SUBS WORKFLOW - generate: refreshLatestFile falhou', e);
      }
      // Fallback: tentar localStorage (persistido pelo EditorPage)
      if (!lastUploadFilename.value && typeof window !== 'undefined') {
        const persisted = window.localStorage?.getItem('fs:lastUploadFilename');
        if (persisted) {
          lastUploadFilename.value = persisted;
          console.log('SUBS WORKFLOW - generate: recuperado via localStorage', {
            recoveredFilename: lastUploadFilename.value,
          });
        }
      }
    }
    if (!lastUploadFilename.value || !rawText.value.trim()) {
      error.value = 'Arquivo ou texto faltando';
      console.warn('SUBS WORKFLOW - generate ABORT (inputs faltando)', {
        hasFilename: !!lastUploadFilename.value,
        text_len: rawText.value?.length || 0,
        rawText_actual: rawText.value,
      });
      return;
    }
    generating.value = true;
    error.value = null;
    try {
      console.log('SUBS WORKFLOW - generate (1/4) início', {
        filename: lastUploadFilename.value,
        text_len: rawText.value.length,
        language: language.value,
        platform: platformPreset.value,
      });
      console.log('SUBS WORKFLOW - generate (2/4) chamando generateSubtitles');
      const resp: any = await generateSubtitles({
        filename: lastUploadFilename.value,
        text: rawText.value,
        language: language.value,
        platform_preset: platformPreset.value,
        character_level: opts?.character_level ?? false,
        uppercase: opts?.uppercase ?? false,
      });
      lastGenerationWasFallback.value = !!resp.fallback || resp.status === 206;
      const rawSubs = Array.isArray(resp.subtitles) ? resp.subtitles : [];
      if (!Array.isArray(resp.subtitles)) {
        console.warn(
          'SUBS WORKFLOW - generate aviso: resp.subtitles não é array',
          {
            type: typeof resp.subtitles,
            value: resp.subtitles,
          }
        );
      }
      const doNormalize = !opts?.character_level;
      const subs = rawSubs.map((s: any) => ({
        id: s.id,
        // Collapse spaced letters only when char-level mode is OFF
        text: doNormalize ? normalizeSpacedText(s.text || '') : s.text || '',
        start: s.start_ms / 1000,
        end: s.end_ms / 1000,
        confidence: s.confidence,
      }));
      subtitleStore.setSubtitles(subs);
      console.log('SUBS WORKFLOW - generate (3/4) legendas processadas', {
        count: subs.length,
      });
      console.log('SUBS WORKFLOW - generate (4/4) estado atualizado');
    } catch (e: any) {
      error.value = e?.message || 'Geração de legendas falhou';
      console.error('SUBS WORKFLOW - generate erro', e);
    } finally {
      generating.value = false;
    }
  }

  async function refreshLatestFile() {
    const files = await listAudioFiles(true);
    if (files.length) {
      lastUploadFilename.value = files[0].filename;
    }
  }

  return {
    uploading,
    aligning,
    generating,
    lastUploadFilename,
    rawText,
    language,
    platformPreset,
    presets,
    alignment,
    error,
    lastGenerationWasFallback,
    fetchPresets,
    doUpload,
    doAlign,
    doGenerate,
    refreshLatestFile,
  };
}
