
import fs from 'node:fs';

const tokens = JSON.parse(fs.readFileSync(new URL('../src/tokens.json', import.meta.url), 'utf8'));

function hexToRgb(hex) {
  const value = hex.replace('#', '');
  return [parseInt(value.slice(0, 2), 16), parseInt(value.slice(2, 4), 16), parseInt(value.slice(4, 6), 16)];
}
function channel(value) {
  const normalized = value / 255;
  return normalized <= 0.03928 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
}
function ratio(fg, bg) {
  const [fr, fgC, fb] = hexToRgb(fg).map(channel);
  const [br, bgC, bb] = hexToRgb(bg).map(channel);
  const l1 = 0.2126 * fr + 0.7152 * fgC + 0.0722 * fb;
  const l2 = 0.2126 * br + 0.7152 * bgC + 0.0722 * bb;
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}

const failures = [];
for (const [name, status] of Object.entries(tokens.statuses)) {
  const contrast = ratio(status.text, status.background);
  if (contrast < 4.5) failures.push(`${name} contrast ${contrast.toFixed(2)} < 4.5`);
  if (!status.shape || !status.icon || !status.label) failures.push(`${name} lacks non-color encoding`);
}
if (ratio(tokens.calm.text, tokens.calm.background) < 4.5) failures.push('calm text contrast fails');
if (ratio(tokens.alarm.text, tokens.alarm.background) < 4.5) failures.push('alarm text contrast fails');
if (tokens.spacing.tapTarget < 44) failures.push('tap target too small');
if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log('WCAG AA/token a11y checks passed; status encodes hue + shape + icon + text; tap targets >=44px.');
