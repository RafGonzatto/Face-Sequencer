import http from './http';

export interface GenerateSubtitlesPayload {
  filename: string;
  text: string;
  language?: string;
  platform_preset?: string;
  character_level?: boolean;
  uppercase?: boolean;
}

export async function generateSubtitles(payload: GenerateSubtitlesPayload) {
  console.log('SUBS API - generateSubtitles (1/4) início', {
    filename: payload.filename,
    text_len: payload.text.length,
    language: payload.language,
    platform: payload.platform_preset,
  });
  console.log('SUBS API - generateSubtitles (2/4) POST /subtitles/generate');
  const t0 = performance.now();
  const response = await http.post('/subtitles/generate', payload, {
    validateStatus: () => true,
  });
  const data = response.data || {};
  console.log('SUBS API - generateSubtitles (3/4) resposta', {
    status: response.status,
    subtitles: data?.subtitles?.length,
    fallback: !!data?.fallback || response.status === 206,
    latency_ms: +(performance.now() - t0).toFixed(1),
  });
  const merged = { status: response.status, ...data } as any;
  console.log('SUBS API - generateSubtitles (4/4) retorno');
  return merged;
}

export async function listPresets() {
  try {
    console.log('SUBS API - listPresets (1/4) início');
    console.log('SUBS API - listPresets (2/4) GET /subtitles/presets');
    const t0 = performance.now();
    const maxAttempts = 3;
    let lastErr: any = null;
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const { data } = await http.get('/subtitles/presets');
        console.log('SUBS API - listPresets (3/4) resposta', {
          count: Object.keys(data?.presets || {}).length,
          latency_ms: +(performance.now() - t0).toFixed(1),
          attempt,
        });
        console.log('SUBS API - listPresets (4/4) retorno');
        return data.presets || {};
      } catch (err: any) {
        lastErr = err;
        const isConnRefused =
          !err?.status &&
          /ECONNREFUSED|Network Error/i.test(String(err?.message || err));
        if (attempt < maxAttempts && isConnRefused) {
          const backoff = 250 * attempt;
          console.warn(
            `SUBS API - listPresets retry ${attempt}/${maxAttempts - 1} after ${backoff}ms due to transient network error`
          );
          await new Promise(r => setTimeout(r, backoff));
          continue;
        }
        throw err;
      }
    }
    throw lastErr;
  } catch (e: any) {
    // If backend returned fallback inside error response structure
    const presets = e?.raw?.response?.data?.presets ||
      e?.presets || {
        basic: {
          name: 'Basic',
          aspect_ratio: '16:9',
          resolution: '1920x1080',
          max_duration: 600,
          style: {
            fontFamily: 'Arial',
            fontSize: 32,
            color: '#FFFFFF',
            bgColor: 'rgba(0,0,0,0.6)',
            bgOpacity: 1,
            padding: 8,
            borderRadius: 4,
            textAlign: 'center',
            marginY: 40,
            maxWidth: 80,
          },
        },
      };
    console.warn('SUBS API - listPresets (fallback)', presets);
    return presets;
  }
}
