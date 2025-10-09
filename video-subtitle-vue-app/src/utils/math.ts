// src/utils/math.ts
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export function lerp(start: number, end: number, fraction: number): number {
  return start + (end - start) * fraction;
}

export function toDegrees(radians: number): number {
  return radians * (180 / Math.PI);
}

export function toRadians(degrees: number): number {
  return degrees * (Math.PI / 180);
}

export function randomInRange(min: number, max: number): number {
  return Math.random() * (max - min) + min;
}