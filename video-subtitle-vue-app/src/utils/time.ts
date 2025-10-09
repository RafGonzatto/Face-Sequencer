// src/utils/time.ts

export function formatTime(seconds: number): string {
    if (!Number.isFinite(seconds)) return "0:00";
    const sign = seconds < 0 ? "-" : "";
    const abs = Math.max(0, Math.floor(Math.abs(seconds)));
    const mins = Math.floor(abs / 60);
    const secs = abs % 60;
    return sign + mins + ":" + String(secs).padStart(2, "0");
}

export function secondsToHms(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours > 0 ? hours + ':' : ''}${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

export function hmsToSeconds(hms: string): number {
    const parts = hms.split(':').map(Number);
    let seconds = 0;
    if (parts.length === 3) {
        seconds += parts[0] * 3600; // hours
        seconds += parts[1] * 60;    // minutes
        seconds += parts[2];         // seconds
    } else if (parts.length === 2) {
        seconds += parts[0] * 60;    // minutes
        seconds += parts[1];         // seconds
    } else if (parts.length === 1) {
        seconds += parts[0];         // seconds
    }
    return seconds;
}