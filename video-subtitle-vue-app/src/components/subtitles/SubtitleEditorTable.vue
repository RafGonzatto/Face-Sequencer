<template>
  <div class="subtitle-editor" tabindex="0" @keydown.stop.prevent="handleKey">
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>In (s)</th>
          <th>Out (s)</th>
          <th>CPS</th>
          <th>Texto</th>
          <th>Ações</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(c, i) in localCues"
          :key="i"
          :class="{
            active: i === effectiveSelection,
            overlap: hasOverlap(i),
            invalid: c.end <= c.start,
            dense: calcCps(c) > cpsWarnThreshold,
          }"
          @click="selectRow(i)"
          @dblclick="seek(c.start)"
        >
          <td>{{ i + 1 }}</td>
          <td>
            <input
              type="number"
              step="0.01"
              v-model.number="c.start"
              @change="emitChange(i)"
              @blur="emitChange(i)"
            />
          </td>
          <td>
            <input
              type="number"
              step="0.01"
              v-model.number="c.end"
              @change="emitChange(i)"
              @blur="emitChange(i)"
            />
          </td>
          <td class="cps">{{ calcCps(c).toFixed(1) }}</td>
          <td class="text-cell">
            <textarea
              v-model="c.text"
              @change="emitChange(i)"
              @blur="emitChange(i)"
            />
          </td>
          <td class="actions">
            <button @click="seek(c.start)">▶</button>
            <button @click="addAfter(i)">＋</button>
            <button @click="splitCue(i)" :disabled="c.text.trim().length < 4">
              ✂
            </button>
            <button
              @click="mergeWithNext(i)"
              :disabled="i === localCues.length - 1"
            >
              ⇄
            </button>
            <button @click="remove(i)" :disabled="localCues.length === 1">
              🗑
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <div class="legend">
      <span class="badge overlap">Overlap</span>
      <span class="badge invalid">End <= Start</span>
      <span class="badge dense">CPS alto (&gt; {{ cpsWarnThreshold }})</span>
    </div>
    <div class="bulk-tools">
      <div class="tool-item">
        <label>Shift (s):</label>
        <input type="number" step="0.05" v-model.number="shiftSeconds" />
        <button @click="applyShift" :disabled="!shiftSeconds">Aplicar</button>
        <button @click="undoShift" :disabled="!canUndo">Desfazer</button>
      </div>
      <div class="tool-item">
        <label>CPS Máx:</label>
        <input type="number" step="1" v-model.number="cpsWarnThreshold" />
      </div>
      <div class="tool-item">
        <button @click="normalizeAll">Normalizar Overlaps</button>
      </div>
      <div class="tool-item stats">
        <span>Total: {{ localCues.length }}</span>
        <span>Overlaps: {{ overlapCount }}</span>
        <span>Média CPS: {{ avgCps.toFixed(1) }}</span>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType, ref, watch, computed } from 'vue';
import type { SubtitleCue } from '@/modules/subtitles/subtitleTypes';

interface EditorProps {
  cues: SubtitleCue[];
  activeIndex: number | null;
}

export default defineComponent({
  name: 'SubtitleEditorTable',
  props: {
    cues: { type: Array as PropType<SubtitleCue[]>, required: true },
    activeIndex: { type: Number, required: false, default: null },
  },
  emits: ['update:cues', 'seek', 'select'],
  setup(
    props: EditorProps,
    ctx: { emit: (event: 'update:cues' | 'seek', payload?: any) => void }
  ) {
    const emit = ctx.emit;
    const localCues = ref<SubtitleCue[]>([]);
    const internalSelection = ref<number | null>(null);
    const shiftSeconds = ref<number | null>(null);
    const lastSnapshot = ref<SubtitleCue[] | null>(null);
    const cpsWarnThreshold = ref(20); // characters per second threshold

    watch(
      () => props.cues,
      (v: SubtitleCue[]) => {
        localCues.value = v.map((c: SubtitleCue) => ({ ...c }));
      },
      { immediate: true, deep: true }
    );

    function normalize(i: number) {
      const c = localCues.value[i];
      if (c.end <= c.start) c.end = c.start + 0.5;
    }

    function sortAndEmit() {
      localCues.value.sort(
        (a: SubtitleCue, b: SubtitleCue) => a.start - b.start
      );
      emit(
        'update:cues',
        localCues.value.map((c: SubtitleCue) => ({ ...c }))
      );
    }

    function emitChange(i: number) {
      normalize(i);
      sortAndEmit();
    }

    function addAfter(i: number) {
      const base = localCues.value[i];
      const mid = base.start + (base.end - base.start) / 2;
      localCues.value.splice(i + 1, 0, {
        start: mid,
        end: mid + 1,
        text: '...',
      });
      sortAndEmit();
    }

    function remove(i: number) {
      if (localCues.value.length === 1) return;
      localCues.value.splice(i, 1);
      sortAndEmit();
    }

    function seek(t: number) {
      emit('seek', t);
    }

    function hasOverlap(i: number) {
      const c = localCues.value[i];
      const prev = localCues.value[i - 1];
      if (prev && c.start < prev.end) return true;
      return false;
    }

    function calcCps(cue: SubtitleCue) {
      const dur = Math.max(0.01, cue.end - cue.start);
      const chars = (cue.text || '').replace(/\s+/g, ' ').trim().length;
      return chars / dur;
    }

    function splitCue(i: number) {
      const c = localCues.value[i];
      const text = c.text.trim();
      if (text.length < 4) return;
      const midIndex = Math.floor(text.length / 2);
      // try to split at nearest space after mid, else before
      let splitAt = text.indexOf(' ', midIndex);
      if (splitAt === -1) {
        splitAt = text.lastIndexOf(' ', midIndex);
        if (splitAt === -1) splitAt = midIndex;
      }
      const left = text.slice(0, splitAt).trim();
      const right = text.slice(splitAt).trim();
      const totalDur = c.end - c.start;
      const leftRatio = left.length / (left.length + right.length || 1);
      const newMid = c.start + totalDur * leftRatio;
      c.text = left;
      c.end = newMid;
      localCues.value.splice(i + 1, 0, {
        start: newMid,
        end: c.end + (totalDur * (1 - leftRatio) || 1),
        text: right || '...',
      });
      sortAndEmit();
    }

    function mergeWithNext(i: number) {
      if (i >= localCues.value.length - 1) return;
      const a = localCues.value[i];
      const b = localCues.value[i + 1];
      a.text = (a.text + ' ' + b.text).replace(/\s+/g, ' ').trim();
      a.end = Math.max(a.end, b.end);
      localCues.value.splice(i + 1, 1);
      sortAndEmit();
    }

    function snapshot() {
      lastSnapshot.value = localCues.value.map((c: SubtitleCue) => ({ ...c }));
    }

    function applyShift() {
      if (shiftSeconds.value === null) return;
      snapshot();
      const delta = shiftSeconds.value;
      localCues.value.forEach((c: SubtitleCue) => {
        c.start = Math.max(0, c.start + delta);
        c.end = Math.max(c.start + 0.01, c.end + delta);
      });
      sortAndEmit();
    }

    function undoShift() {
      if (!lastSnapshot.value) return;
      localCues.value = lastSnapshot.value.map((c: SubtitleCue) => ({ ...c }));
      sortAndEmit();
      lastSnapshot.value = null;
    }

    function normalizeAll() {
      // Ensure strictly increasing without overlap, minimal 0.1s gap
      const minGap = 0.0;
      localCues.value.sort(
        (a: SubtitleCue, b: SubtitleCue) => a.start - b.start
      );
      for (let i = 1; i < localCues.value.length; i++) {
        const prev = localCues.value[i - 1];
        const cur = localCues.value[i];
        if (cur.start < prev.end + minGap) {
          const shiftNeeded = prev.end + minGap - cur.start;
          cur.start += shiftNeeded;
          if (cur.end <= cur.start) cur.end = cur.start + 0.5;
        }
      }
      sortAndEmit();
    }

    const canUndo = () => !!lastSnapshot.value;

    function selectRow(i: number) {
      internalSelection.value = i;
      emit('select', i);
    }

    const effectiveSelection = computed(() => {
      return internalSelection.value !== null
        ? internalSelection.value
        : (props.activeIndex ?? null);
    });

    function currentCueIndex() {
      return effectiveSelection.value !== null ? effectiveSelection.value : 0;
    }

    function nudgeStart(delta: number) {
      const idx = currentCueIndex();
      const cue = localCues.value[idx];
      if (!cue) return;
      cue.start = Math.max(0, cue.start + delta);
      if (cue.end <= cue.start) cue.end = cue.start + 0.05;
      emitChange(idx);
    }

    function nudgeEnd(delta: number) {
      const idx = currentCueIndex();
      const cue = localCues.value[idx];
      if (!cue) return;
      cue.end = Math.max(cue.start + 0.05, cue.end + delta);
      emitChange(idx);
    }

    function removeCurrent() {
      const idx = currentCueIndex();
      remove(idx);
    }

    function mergeWithPrevious() {
      const idx = currentCueIndex();
      if (idx <= 0) return;
      const prev = localCues.value[idx - 1];
      const cur = localCues.value[idx];
      prev.text = (prev.text + ' ' + cur.text).replace(/\s+/g, ' ').trim();
      prev.end = Math.max(prev.end, cur.end);
      localCues.value.splice(idx, 1);
      internalSelection.value = idx - 1;
      sortAndEmit();
    }

    function handleKey(e: KeyboardEvent) {
      const key = e.key;
      const ctrl = e.ctrlKey || e.metaKey;
      const shift = e.shiftKey;
      if (ctrl && key === 'Enter') {
        splitCue(currentCueIndex());
        return;
      }
      if (ctrl && (key === 'm' || key === 'M')) {
        mergeWithNext(currentCueIndex());
        return;
      }
      if (ctrl && (key === 'b' || key === 'B')) {
        mergeWithPrevious();
        return;
      }
      if (key === 'Delete') {
        removeCurrent();
        return;
      }
      if (key === 'ArrowUp') {
        const idx = currentCueIndex();
        internalSelection.value = Math.max(0, idx - 1);
        return;
      }
      if (key === 'ArrowDown') {
        const idx = currentCueIndex();
        internalSelection.value = Math.min(localCues.value.length - 1, idx + 1);
        return;
      }
      // Nudge timings
      if (key === 'ArrowLeft') {
        if (ctrl && shift) {
          nudgeEnd(-0.1);
        } else if (ctrl) {
          nudgeStart(-0.05);
        } else if (shift) {
          nudgeEnd(-0.05);
        }
        return;
      }
      if (key === 'ArrowRight') {
        if (ctrl && shift) {
          nudgeEnd(0.1);
        } else if (ctrl) {
          nudgeStart(0.05);
        } else if (shift) {
          nudgeEnd(0.05);
        }
        return;
      }
    }

    const overlapCount = computed(() =>
      localCues.value.reduce(
        (acc: number, _c: SubtitleCue, i: number) =>
          acc + (hasOverlap(i) ? 1 : 0),
        0
      )
    );
    const avgCps = computed(() => {
      if (!localCues.value.length) return 0;
      const sum = localCues.value.reduce(
        (acc: number, c: SubtitleCue) => acc + calcCps(c),
        0
      );
      return sum / localCues.value.length;
    });

    return {
      localCues,
      emitChange,
      addAfter,
      remove,
      seek,
      hasOverlap,
      calcCps,
      splitCue,
      mergeWithNext,
      shiftSeconds,
      applyShift,
      undoShift,
      canUndo,
      normalizeAll,
      cpsWarnThreshold,
      selectRow,
      handleKey,
      effectiveSelection,
      nudgeStart,
      nudgeEnd,
      overlapCount,
      avgCps,
    };
  },
});
</script>

<style scoped>
.subtitle-editor {
  max-width: 100%;
  overflow-x: auto;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 8px;
  background: #1f2125;
  font-size: 12px;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  border: 1px solid #333;
  padding: 4px 6px;
  vertical-align: top;
}
th {
  background: #2a2d31;
}
tr.active {
  outline: 2px solid #3b82f6;
}
tr.overlap td {
  background: rgba(255, 193, 7, 0.1);
}
tr.invalid td {
  background: rgba(255, 99, 99, 0.15);
}
tr.dense td {
  background: rgba(138, 43, 226, 0.12);
}
.cps {
  width: 52px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
input[type='number'] {
  width: 70px;
  background: #111;
  color: #eee;
  border: 1px solid #444;
}
textarea {
  width: 100%;
  min-height: 48px;
  resize: vertical;
  background: #111;
  color: #eee;
  border: 1px solid #444;
}
.actions button {
  margin-right: 4px;
  background: #333;
  color: #eee;
  border: 1px solid #555;
  padding: 2px 6px;
  cursor: pointer;
}
.actions button:hover {
  background: #444;
}
.actions button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.legend {
  margin-top: 6px;
  display: flex;
  gap: 8px;
}
.badge {
  font-size: 10px;
  padding: 2px 4px;
  border-radius: 3px;
  background: #333;
}
.badge.overlap {
  background: #8a6d1d;
}
.badge.invalid {
  background: #7a2e2e;
}
.badge.dense {
  background: #4b2a7a;
}
.bulk-tools {
  margin-top: 10px;
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  font-size: 11px;
}
.bulk-tools .tool-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.bulk-tools input {
  width: 70px;
  background: #111;
  color: #eee;
  border: 1px solid #444;
  padding: 2px 4px;
}
.bulk-tools button {
  background: #333;
  color: #eee;
  border: 1px solid #555;
  padding: 2px 8px;
  cursor: pointer;
}
.bulk-tools button:hover {
  background: #444;
}
</style>
