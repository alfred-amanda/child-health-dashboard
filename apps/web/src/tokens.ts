
import rawTokens from './tokens.json';

export const tokens = rawTokens;

export type StatusKey = keyof typeof tokens.statuses;

function hexToRgb(hex: string): [number, number, number] {
  const value = hex.replace('#', '');
  return [Number.parseInt(value.slice(0, 2), 16), Number.parseInt(value.slice(2, 4), 16), Number.parseInt(value.slice(4, 6), 16)];
}

function channel(value: number): number {
  const normalized = value / 255;
  return normalized <= 0.03928 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
}

export function contrastRatio(foreground: string, background: string): number {
  const [fr, fg, fb] = hexToRgb(foreground).map(channel);
  const [br, bg, bb] = hexToRgb(background).map(channel);
  const l1 = 0.2126 * fr + 0.7152 * fg + 0.0722 * fb;
  const l2 = 0.2126 * br + 0.7152 * bg + 0.0722 * bb;
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}
