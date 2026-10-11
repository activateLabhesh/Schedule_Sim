import { $ } from './util.js';

export async function api(path, body) {
  const response = await fetch(`/api/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(data.detail || 'Request failed');
  }
  return response;
}

export async function getPresets() {
  const response = await fetch('/api/presets');
  if (!response.ok) throw new Error('Could not load presets');
  return response.json();
}

export function showError(error) {
  let banner = $('.error-banner');
  if (!banner) {
    banner = document.createElement('div');
    banner.className = 'error-banner';
    $('.panel.active').prepend(banner);
  }
  banner.textContent = error.message || String(error);
}

export function clearError() {
  $('.error-banner')?.remove();
}
