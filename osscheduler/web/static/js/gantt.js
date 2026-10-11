import { $, escapeHtml, clamp, pidColor } from './util.js';

export function renderGantt(root, result, cursor = null) {
  const holder = typeof root === 'string' ? $(root) : root;
  if (!holder) return;
  const cores = Array.from({ length: result.cores || 1 }, (_, index) => index);
  const extent = Math.max(result.makespan, 1);
  const elapsed = cursor === null ? extent : clamp(cursor, 0, extent);
  const activeTick = cursor === null ? null : elapsed - 1;
  holder.replaceChildren(...cores.map(core => {
    const row = document.createElement('div');
    row.className = 'gantt-row';
    const label = document.createElement('div');
    label.className = 'gantt-core';
    label.textContent = `CPU ${core + 1}`;
    const track = document.createElement('div');
    track.className = 'gantt-track';
    const blocks = result.gantt.filter(block => block.core === core).sort((a, b) => a.start - b.start);
    for (const block of blocks) {
      const visibleEnd = Math.min(block.end, elapsed);
      if (block.start >= visibleEnd) continue;
      const el = document.createElement('div');
      el.className = `gantt-block ${block.state}`;
      if (activeTick !== null && activeTick >= block.start && activeTick < block.end) el.classList.add('current-tick');
      const widthPct = 100 * (visibleEnd - block.start) / extent;
      el.style.width = `${widthPct}%`;
      el.title = `${block.pid || block.state}: ${block.start}–${block.end}`;
      if (block.state === 'running') el.style.background = pidColor(block.pid);
      el.dataset.start = block.start;
      el.dataset.end = block.end;
      if (widthPct >= 5) el.textContent = block.pid || (block.state === 'idle' ? 'idle' : 'switch');
      if (widthPct >= 8) {
        const time = document.createElement('small');
        time.textContent = block.start;
        el.append(time);
      }
      track.append(el);
    }
    if (cursor !== null) {
      const marker = document.createElement('i');
      marker.className = 'gantt-cursor';
      marker.style.left = `${100 * elapsed / extent}%`;
      track.append(marker);
    }
    row.append(label, track);
    return row;
  }));
}

export function renderCompareGantts(results) {
  const host = $('#compare-gantts');
  const extent = Math.max(...Object.values(results).map(result => result.makespan));
  host.replaceChildren();
  for (const [name, result] of Object.entries(results)) {
    for (let core = 0; core < result.cores; core++) {
      const row = document.createElement('div');
      row.className = 'compare-gantt-row';
      const label = document.createElement('span');
      label.textContent = `${name.toUpperCase()} · CPU ${core + 1}`;
      const track = document.createElement('div');
      track.className = 'gantt-track';
      for (const block of result.gantt.filter(item => item.core === core).sort((a, b) => a.start - b.start)) {
        const el = document.createElement('div');
        el.className = `gantt-block ${block.state}`;
        const widthPct = 100 * (block.end - block.start) / extent;
        el.style.width = `${widthPct}%`;
        el.title = `${block.pid || block.state}: ${block.start}–${block.end}`;
        if (block.state === 'running') el.style.background = pidColor(block.pid);
        if (widthPct >= 5) el.textContent = block.pid || block.state;
        track.append(el);
      }
      row.append(label, track);
      host.append(row);
    }
  }
}

export function renderProcessTimeline(root, result, cursor = null) {
  const holder = typeof root === 'string' ? $(root) : root;
  if (!holder) return;
  const extent = Math.max(result.makespan, 1);
  const elapsed = cursor === null ? extent : clamp(cursor, 0, extent);
  const runningSpans = {};
  for (const block of result.gantt) {
    if (block.state !== 'running' || !block.pid) continue;
    (runningSpans[block.pid] ||= []).push(block);
  }
  holder.replaceChildren(...result.processes.map(process => {
    const row = document.createElement('div');
    row.className = 'life-row';
    const label = document.createElement('div');
    label.className = 'life-label';
    label.innerHTML = `<b style="background:${pidColor(process.pid)}"></b>${escapeHtml(process.pid)}`;
    const track = document.createElement('div');
    track.className = 'life-track';
    const base = document.createElement('div');
    base.className = 'life-span';
    base.style.left = `${100 * process.arrival_time / extent}%`;
    base.style.width = `${100 * Math.max(process.completion_time - process.arrival_time, 0) / extent}%`;
    track.append(base);
    for (const span of (runningSpans[process.pid] || [])) {
      const visibleEnd = Math.min(span.end, elapsed);
      if (span.start >= visibleEnd) continue;
      const segment = document.createElement('div');
      segment.className = 'life-run';
      segment.style.left = `${100 * span.start / extent}%`;
      segment.style.width = `${100 * (visibleEnd - span.start) / extent}%`;
      segment.style.background = pidColor(process.pid);
      segment.title = `running ${span.start}–${span.end}`;
      track.append(segment);
    }
    const startMark = document.createElement('i');
    startMark.className = 'life-mark';
    startMark.style.left = `${100 * process.first_start / extent}%`;
    startMark.title = `first start ${process.first_start}`;
    const doneMark = document.createElement('i');
    doneMark.className = 'life-mark done';
    doneMark.style.left = `${100 * process.completion_time / extent}%`;
    doneMark.title = `complete ${process.completion_time}`;
    track.append(startMark, doneMark);
    if (cursor !== null) {
      const marker = document.createElement('i');
      marker.className = 'gantt-cursor';
      marker.style.left = `${100 * elapsed / extent}%`;
      track.append(marker);
    }
    const stats = document.createElement('div');
    stats.className = 'life-stats';
    stats.innerHTML = `<span>wait ${process.waiting_time}</span><span>TAT ${process.turnaround_time}</span>`;
    row.append(label, track, stats);
    return row;
  }));
}

export function renderExecutionState(board, queue, snapshot, result, tick) {
  const priorities = Object.fromEntries(snapshot?.effective_priorities || []);
  const waits = Object.fromEntries(snapshot?.waiting_times || []);
  const states = snapshot?.core_states || [];
  const cores = Array.from({ length: result.cores || 1 }, (_, index) => index);
  board.replaceChildren(...cores.map(core => {
    const pid = snapshot?.running?.[core] ?? null;
    const state = states[core] || 'idle';
    const card = document.createElement('div');
    card.className = `cpu-card ${state}`;
    const name = document.createElement('span');
    name.className = 'cpu-name';
    name.textContent = `CPU ${core + 1}`;
    const chip = document.createElement('div');
    chip.className = 'cpu-chip';
    if (state === 'running' && pid) {
      chip.textContent = pid;
      chip.style.background = pidColor(pid);
    } else if (state === 'switching') {
      chip.classList.add('switching');
      chip.textContent = `→ ${pid || 'next'}`;
    } else {
      chip.classList.add('idle');
      chip.textContent = 'idle';
    }
    const meta = document.createElement('div');
    meta.className = 'cpu-meta';
    meta.textContent = state === 'running' && pid
      ? `priority ${priorities[pid] ?? '–'} · waited ${waits[pid] ?? 0}t`
      : state;
    card.append(name, chip, meta);
    return card;
  }));

  const ready = snapshot?.ready || [];
  if (!ready.length) {
    const empty = document.createElement('div');
    empty.className = 'queue-empty';
    empty.textContent = 'Ready queue empty — nothing is waiting for the CPU';
    queue.replaceChildren(empty);
    return;
  }
  queue.replaceChildren(...ready.map((pid, index) => {
    const chip = document.createElement('div');
    chip.className = `queue-chip${index === 0 ? ' front' : ''}`;
    chip.style.setProperty('--chip', pidColor(pid));
    chip.innerHTML = `<b>${escapeHtml(pid)}</b><span>pri ${priorities[pid] ?? '–'}</span><span>waited ${waits[pid] ?? 0}t</span>`;
    if (index === 0) {
      const tag = document.createElement('em');
      tag.textContent = 'next';
      chip.append(tag);
    }
    return chip;
  }));
}
