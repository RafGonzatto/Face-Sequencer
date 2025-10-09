// src/modules/subtitles/subtitleParser.ts

interface SubtitleCue {
  start: number;
  end: number;
  text: string;
}

export function parseSRT(data: string): SubtitleCue[] {
  const cues: SubtitleCue[] = [];
  const cueBlocks = data.split(/\n\s*\n/);

  cueBlocks.forEach(block => {
    const lines = block.split('\n');
    if (lines.length < 3) return;

    const timeLine = lines[1];
    const [start, end] = timeLine.split(' --> ').map(timeString => {
      const [hours, minutes, seconds] = timeString.split(':');
      return (
        parseInt(hours) * 3600 +
        parseInt(minutes) * 60 +
        parseFloat(seconds.replace(',', '.'))
      );
    });

    const text = lines.slice(2).join('\n').trim();
    cues.push({ start, end, text });
  });

  return cues;
}

export function parseVTT(data: string): SubtitleCue[] {
  const cues: SubtitleCue[] = [];
  const lines = data.split('\n');
  let currentCue: SubtitleCue | null = null;

  lines.forEach(line => {
    if (line.includes('-->')) {
      if (currentCue) {
        cues.push(currentCue);
      }
      const [start, end] = line.split(' --> ').map(timeString => {
        const [hours, minutes, seconds] = timeString.split(':');
        return (
          parseInt(hours) * 3600 +
          parseInt(minutes) * 60 +
          parseFloat(seconds)
        );
      });
      currentCue = { start, end, text: '' };
    } else if (currentCue) {
      currentCue.text += line.trim() + ' ';
    }
  });

  if (currentCue) {
    cues.push(currentCue);
  }

  return cues.map(cue => ({
    ...cue,
    text: cue.text.trim(),
  }));
}