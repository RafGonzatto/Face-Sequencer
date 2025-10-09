import http from './http';

export interface UploadResponse {
  success: boolean;
  filename: string;
  size: number;
  file_hash: string;
  message: string;
}
export interface AudioFileEntry {
  filename: string;
  size: number;
  mtime: number;
}

export async function uploadAudio(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append('audio', file, file.name);
  console.log('AUDIO API - uploadAudio (1/4) início', {
    filename: file.name,
    size_bytes: file.size,
    size_mb: (file.size / (1024 * 1024)).toFixed(2),
  });
  console.log('AUDIO API - uploadAudio (2/4) preparando POST /audio/upload');
  const started = performance.now();
  const { data } = await http.post('/audio/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  console.log('AUDIO API - uploadAudio (3/4) resposta recebida', {
    latency_ms: +(performance.now() - started).toFixed(1),
    success: data?.success,
    serverFilename: data?.filename,
  });
  console.log('AUDIO API - uploadAudio (4/4) retornando ao caller');
  return data;
}

export async function listAudioFiles(
  latest = false
): Promise<AudioFileEntry[]> {
  console.log('AUDIO API - listAudioFiles (1/4) início', { latest });
  console.log('AUDIO API - listAudioFiles (2/4) GET /audio/files');
  const t0 = performance.now();
  const { data } = await http.get('/audio/files', {
    params: latest ? { latest: true } : {},
  });
  console.log('AUDIO API - listAudioFiles (3/4) resposta', {
    count: data?.files?.length || 0,
    latency_ms: +(performance.now() - t0).toFixed(1),
  });
  const files = data.files || [];
  console.log('AUDIO API - listAudioFiles (4/4) retorno ao caller', {
    count: files.length,
  });
  return files;
}

export async function alignBasic(payload: {
  filename: string;
  text: string;
  language?: string;
}) {
  console.log('AUDIO API - alignBasic (1/4) início', {
    ...payload,
    text_len: payload.text.length,
  });
  console.log('AUDIO API - alignBasic (2/4) POST /audio/align');
  const t0 = performance.now();
  const { data } = await http.post('/audio/align', payload);
  console.log('AUDIO API - alignBasic (3/4) resposta', {
    latency_ms: +(performance.now() - t0).toFixed(1),
    tokens: data?.alignment?.tokens?.length,
  });
  console.log('AUDIO API - alignBasic (4/4) retorno');
  return data;
}
