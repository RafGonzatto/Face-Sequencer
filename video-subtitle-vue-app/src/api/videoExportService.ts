import http from './http';

export interface SubtitleSegmentPayload {
  id: string;
  text: string;
  start_time: number;
  end_time: number;
  confidence?: number;
  style_overrides?: Record<string, any>;
  karaoke?: Record<string, any>;
}

export interface ExportVideoPayload {
  inputVideoPath: string;
  outputFilename: string;
  presetName?: string;
  subtitleSegments: SubtitleSegmentPayload[];
  customSettings?: Record<string, any>;
}

export interface ExportVideoResponse {
  success: boolean;
  job_id?: string;
  output_path?: string;
  download_url?: string;
  file_size_mb?: number;
  processing_time?: number;
  error?: string;
}

export async function exportVideoWithSubtitles(
  payload: ExportVideoPayload
): Promise<ExportVideoResponse> {
  console.log('VIDEO API - exportVideoWithSubtitles (1/4) início', {
    input: payload.inputVideoPath,
    output: payload.outputFilename,
    preset: payload.presetName,
    segments: payload.subtitleSegments.length,
  });
  console.log(
    'VIDEO API - exportVideoWithSubtitles (2/4) POST /v4/export/video-with-subtitles'
  );
  const t0 = performance.now();
  const { data } = await http.post(
    '/v4/export/video-with-subtitles',
    {
      input_video_path: payload.inputVideoPath,
      output_filename: payload.outputFilename,
      preset_name: payload.presetName,
      subtitle_segments: payload.subtitleSegments,
      custom_settings: payload.customSettings,
    },
    { validateStatus: () => true }
  );
  console.log('VIDEO API - exportVideoWithSubtitles (3/4) resposta', {
    success: data?.success,
    job_id: data?.job_id,
    latency_ms: +(performance.now() - t0).toFixed(1),
    output_path: data?.output_path,
  });
  console.log('VIDEO API - exportVideoWithSubtitles (4/4) retorno');
  return data as ExportVideoResponse;
}
