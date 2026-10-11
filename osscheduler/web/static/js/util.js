export const $ = (selector) => document.querySelector(selector);
export const $$ = (selector) => [...document.querySelectorAll(selector)];
export const palette = ['#a5cb72','#65aaa0','#e5aa70','#89a8ce','#d58978','#b4a0ca','#70b8bc','#d2c66f','#86bd91'];
export const escapeHtml = (value) => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
export const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

export function pidColor(pid) {
  const match = String(pid).match(/\d+/);
  const index = (match ? Number(match[0]) : 1) - 1;
  return palette[((index % palette.length) + palette.length) % palette.length];
}
