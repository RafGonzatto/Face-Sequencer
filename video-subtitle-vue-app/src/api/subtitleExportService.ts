import http from './http';
import type { SubtitleCue } from '@/modules/subtitles/subtitleTypes';

export async function exportSubtitles(
  format: 'srt' | 'vtt',
  cues: SubtitleCue[],
  opts?: { wrap?: boolean; wrapMin?: number; wrapMax?: number }
) {
  console.log('SUBS API - exportSubtitles (1/4) início', {
    format,
    cues: cues.length,
  });
  const payload: any = {
    format,
    subtitles: cues.map(c => ({ start: c.start, end: c.end, text: c.text })),
  };
  if (opts?.wrap) {
    payload.wrap_lines = true;
    if (typeof opts.wrapMin === 'number') payload.wrap_min = opts.wrapMin;
    if (typeof opts.wrapMax === 'number') payload.wrap_max = opts.wrapMax;
  }
  console.log('SUBS API - exportSubtitles (2/4) POST /subtitles/export');
  const t0 = performance.now();
  const response = await http.post('/subtitles/export', payload, {
    responseType: 'blob',
  });
  console.log('SUBS API - exportSubtitles (3/4) resposta', {
    size_bytes: response.data?.size,
    latency_ms: +(performance.now() - t0).toFixed(1),
  });
  console.log('SUBS API - exportSubtitles (4/4) retorno');
  return response.data as Blob;
}

export function downloadBlob(blob: Blob, filename: string) {
  console.log('UTIL - downloadBlob (1/2) preparando download', {
    filename,
    size_bytes: blob.size,
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    console.log('UTIL - downloadBlob (2/2) cleanup concluído');
  }, 100);
}
