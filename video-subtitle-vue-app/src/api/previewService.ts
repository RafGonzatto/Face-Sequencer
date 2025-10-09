import http from './http';

export interface PreviewFramePayload {
  inputVideoPath: string;
  time: number; // seconds
  presetName?: string;
  subtitleSegments: Array<{
    id: string;
    text: string;
    start_time: number;
    end_time: number;
    confidence?: number;
    style_overrides?: Record<string, any>;
    karaoke?: Record<string, any>;
  }>;
  customSettings?: Record<string, any>;
}

export async function getPreviewFrameUrl(
  payload: PreviewFramePayload
): Promise<string> {
  const { data, status } = await http.post(
    '/v4/export/preview-frame',
    {
      input_video_path: payload.inputVideoPath,
      time: payload.time,
      preset_name: payload.presetName,
      subtitle_segments: payload.subtitleSegments,
      custom_settings: payload.customSettings,
    },
    { responseType: 'blob', validateStatus: () => true }
  );
  if (status !== 200) {
    throw new Error('Preview request failed');
  }
  // Axios with responseType: 'blob' should give us a Blob with the real content-type
  const blob: Blob = data as Blob;
  // Basic guards: ensure we got a PNG with non-zero size
  const isPng = (blob.type || '').toLowerCase().includes('image/png');
  if (!isPng || !(blob.size > 0)) {
    throw new Error(
      `Preview returned invalid blob (type=${blob.type}, size=${blob.size})`
    );
  }
  return URL.createObjectURL(blob);
}
