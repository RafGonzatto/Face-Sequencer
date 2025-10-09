// src/utils/formatting.ts

export function formatTime(seconds: number): string {
    if (!Number.isFinite(seconds)) return "0:00";
    const sign = seconds < 0 ? "-" : "";
    const abs = Math.max(0, Math.floor(Math.abs(seconds)));
    const mins = Math.floor(abs / 60);
    const secs = abs % 60;
    return sign + mins + ":" + String(secs).padStart(2, "0");
}

export function escapeHtml(text: string | null): string {
    if (text == null) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\n/g, "<br>");
}

export function clamp(value: number, min: number, max: number): number {
    return Math.min(Math.max(value, min), max);
}

export function hexToRgba(hex: string, alpha: number): string {
    if (!hex) return "";
    let value = String(hex).replace("#", "").trim();
    if (!value) return "";
    if (value.length === 3) {
        value = value
            .split("")
            .map((ch) => ch + ch)
            .join("");
    }
    const int = parseInt(value, 16);
    if (Number.isNaN(int)) return hex;
    const r = (int >> 16) & 255;
    const g = (int >> 8) & 255;
    const b = int & 255;
    const a = typeof alpha === "number" ? clamp(alpha, 0, 1) : 1;
    return `rgba(${r}, ${g}, ${b}, ${a})`;
}