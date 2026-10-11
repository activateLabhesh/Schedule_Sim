import { $, $$, escapeHtml } from './util.js';
import { api, getPresets, showError, clearError } from './api.js';
import { renderGantt, renderCompareGantts, renderProcessTimeline, renderExecutionState } from './gantt.js';
import { renderCompareChart, drawBoxPlot, renderSweepChart, renderAgingCharts } from './charts.js';
import { Playback } from './playback.js';

let latest = null;

const playback = new Playback({
  onRender: renderTick,
  getInterval: () => Math.max(80, 1000 - Number($('#speed').value) * 90),
  onState: playing => { $('#play').textContent = playing ? 'Ⅱ Pause' : '▶ Play'; },
});

function rowMarkup(process = { pid: `P${$('#process-rows').children.length + 1}`, arrival_time: 0, burst_time: 4, priority: 0 }) {
  const tr = document.createElement('tr');
  for (const [key, value, type] of [['pid', process.pid, 'text'], ['arrival_time', process.arrival_time, 'number'], ['burst_time', process.burst_time, 'number'], ['priority', process.priority, 'number']]) {
    const td = document.createElement('td');
    const input = document.createElement('input');
    input.dataset.field = key;
    input.type = type;
    input.value = value;
    if (type === 'number') input.min = key === 'arrival_time' || key === 'priority' ? '0' : '1';
    td.append(input);
    tr.append(td);
  }
  const action = document.createElement('td');
  const remove = document.createElement('button');
  remove.className = 'remove-row';
  remove.textContent = '×';
  remove.title = 'Remove process';
  remove.onclick = () => tr.remove();
  action.append(remove);
  tr.append(action);
  return tr;
}

function setProcesses(list) {
  $('#process-rows').replaceChildren(...list.map(rowMarkup));
}

function processes() {
  return $$('#process-rows tr').map(tr => Object.fromEntries(
    [...tr.querySelectorAll('[data-field]')].map(input => [input.dataset.field, input.type === 'number' ? Number(input.value) : input.value])));
}

function config(extra = {}) {
  return {
    processes: processes(),
    algorithm: $('#algorithm').value,
    cores: Number($('#cores').value),
    quantum: Number($('#quantum').value),
    aging: $('#aging-enabled').checked,
    aging_interval: Number($('#aging-interval').value),
    aging_step: Number($('#aging-step').value),
    context_switch_cost: Number($('#switch-cost').value),
    starvation_threshold: Number($('#starvation-threshold').value),
    ...extra,
  };
}

function setTab(name) {
  $$('.tab').forEach(button => button.classList.toggle('active', button.dataset.tab === name));
  $$('.panel').forEach(panel => panel.classList.toggle('active', panel.id === name));
}

function renderMetrics(result) {
  const metrics = [
    ['Avg waiting', result.average_waiting_time],
    ['Avg turnaround', result.average_turnaround_time],
    ['Avg response', result.average_response_time],
    ['Throughput', result.throughput],
    ['CPU utilization', `${(100 * result.cpu_utilization).toFixed(1)}%`],
    ['Context switches', `${result.context_switches} · ${result.switching_overhead}t`],
  ];
  $('#single-metrics').replaceChildren(...metrics.map(([label, value]) => {
    const card = document.createElement('div');
    card.className = 'metric-card';
    card.innerHTML = `<span>${label}</span><strong>${typeof value === 'number' ? value.toFixed(2) : value}</strong>`;
    return card;
  }));
  $('#metrics-rows').innerHTML = result.processes.map(process =>
    `<tr><td>${escapeHtml(process.pid)}</td><td>${process.first_start}</td><td>${process.completion_time}</td><td>${process.waiting_time}</td><td>${process.turnaround_time}</td><td>${process.response_time}</td><td>${process.response_ratio.toFixed(2)}</td></tr>`).join('');
  const analysis = result.analysis;
  const littleLaw = analysis.little_law;
  $('#analysis-cards').innerHTML = `<div class="analysis-card"><span>JAIN FAIRNESS</span><strong>${analysis.jain.toFixed(3)}</strong></div><div class="analysis-card"><span>GINI WAIT INEQUALITY</span><strong>${analysis.gini.toFixed(3)}</strong></div><div class="analysis-card"><span>STARVED PROCESSES · WAIT &gt; ${analysis.starvation_threshold}</span><strong>${escapeHtml(analysis.starved_processes.join(', ') || 'None')}</strong></div><div class="analysis-card"><span>LITTLE’S LAW · |L − λW|</span><strong>${littleLaw.absolute_error.toFixed(3)}</strong><small>L ${littleLaw.L.toFixed(2)} · λ ${littleLaw.lambda.toFixed(2)} · W ${littleLaw.W.toFixed(2)}</small></div>`;
  $('#aggregate-stats').innerHTML = `<table><thead><tr><th>METRIC</th><th>MEAN</th><th>MEDIAN</th><th>MIN</th><th>MAX</th><th>STD DEV</th></tr></thead><tbody>${Object.entries(result.metric_summary).map(([name, stats]) => `<tr><td>${name.replace('_time', '').toUpperCase()}</td><td>${stats.mean.toFixed(2)}</td><td>${stats.median.toFixed(2)}</td><td>${stats.min.toFixed(2)}</td><td>${stats.max.toFixed(2)}</td><td>${stats.stdev.toFixed(2)}</td></tr>`).join('')}</tbody></table>`;
  $('#run-label').textContent = `${result.algorithm.toUpperCase()} · ${result.makespan} ticks · ${result.cores} core(s)`;
}

function renderTick(tick) {
  if (!latest) return;
  const last = Math.max(0, latest.trace.length - 1);
  const t = Math.min(Math.max(tick ?? playback.tick, 0), last);
  playback.tick = t;
  $('#timeline').max = last;
  $('#timeline').value = t;
  $('#tick-label').textContent = `t = ${t}`;
  const snapshot = latest.trace[t];
  renderExecutionState($('#cpu-board'), $('#ready-queue-visual'), snapshot, latest, t);
  const traces = latest.trace.slice(Math.max(0, t - 7), t + 1).reverse();
  $('#trace').innerHTML = traces.map(item => `<div class="trace-item"><time>t=${item.time}</time>${escapeHtml(item.decisions.join(' · ') || `CPU: ${item.running.map(value => value || 'idle').join(', ')}`)}</div>`).join('');
  const revealed = Math.min(t + 1, latest.makespan);
  renderGantt('#single-gantt', latest, revealed);
  renderProcessTimeline('#process-timeline', latest, revealed);
}

$$('.tab').forEach(button => button.addEventListener('click', () => setTab(button.dataset.tab)));
$('#add-process').onclick = () => $('#process-rows').append(rowMarkup());
$('#preset').onchange = async event => {
  try {
    const data = await getPresets();
    setProcesses(data[event.target.value]);
  } catch (error) {
    showError(error);
  }
};

$('#run-button').onclick = async () => {
  clearError();
  try {
    const result = await (await api('simulate', config())).json();
    latest = result;
    renderMetrics(latest);
    playback.load(latest.trace.length);
    setTab('run');
  } catch (error) {
    showError(error);
  }
};
$('#timeline').oninput = () => playback.seek(Number($('#timeline').value));
$('#step-forward').onclick = () => playback.step(1);
$('#step-back').onclick = () => playback.step(-1);
$('#play').onclick = () => playback.toggle();

$$('.run-action').forEach(button => button.onclick = async () => {
  clearError();
  try {
    const data = await (await api('compare', config())).json();
    const names = Object.keys(data);
    $('#compare-table').innerHTML = `<table><thead><tr><th>POLICY</th><th>WAIT</th><th>TURNAROUND</th><th>RESPONSE</th><th>THROUGHPUT</th><th>UTILIZATION</th><th>SWITCHES</th><th>OVERHEAD</th></tr></thead><tbody>${names.map(name => {
      const result = data[name];
      return `<tr><td>${name.toUpperCase()}</td><td>${result.average_waiting_time.toFixed(2)}</td><td>${result.average_turnaround_time.toFixed(2)}</td><td>${result.average_response_time.toFixed(2)}</td><td>${result.throughput.toFixed(3)}</td><td>${(100 * result.cpu_utilization).toFixed(1)}%</td><td>${result.context_switches}</td><td>${result.switching_overhead}</td></tr>`;
    }).join('')}</tbody></table>`;
    renderCompareGantts(data);
    renderCompareChart(data);
    setTab('compare');
  } catch (error) {
    showError(error);
  }
});

$('#monte-run').onclick = async () => {
  clearError();
  try {
    const range = id => $('#' + id).value.split(',').map(Number);
    const [arrival_min, arrival_max] = range('mc-arrival');
    const [burst_min, burst_max] = range('mc-burst');
    const [priority_min, priority_max] = range('mc-priority');
    const result = await (await api('montecarlo', {
      runs: Number($('#mc-runs').value),
      process_count: Number($('#mc-processes').value),
      seed: Number($('#mc-seed').value),
      cores: Number($('#cores').value),
      arrival_min, arrival_max, burst_min, burst_max, priority_min, priority_max,
    })).json();
    const names = Object.keys(result);
    $('#mc-table').innerHTML = `<table><thead><tr><th>POLICY</th><th>MEAN</th><th>MEDIAN</th><th>STD DEV</th><th>MIN–MAX</th><th>WIN RATE</th></tr></thead><tbody>${names.map(name => `<tr><td>${name.toUpperCase()}</td><td>${result[name].mean.toFixed(2)}</td><td>${result[name].median.toFixed(2)}</td><td>${result[name].stdev.toFixed(2)}</td><td>${result[name].min.toFixed(1)}–${result[name].max.toFixed(1)}</td><td>${(100 * result[name].win_rate).toFixed(1)}%</td></tr>`).join('')}</tbody></table>`;
    drawBoxPlot($('#boxplot'), result);
  } catch (error) {
    showError(error);
  }
};

$('#sweep-run').onclick = async () => {
  clearError();
  try {
    const result = await (await api('quantum-sweep', {
      processes: processes(),
      max_quantum: Number($('#max-quantum').value),
      cores: Number($('#cores').value),
    })).json();
    $('#sweep-optimum').textContent = `Lowest average wait at quantum ${result.optimum_quantum}`;
    renderSweepChart(result);
  } catch (error) {
    showError(error);
  }
};

$('#aging-run').onclick = async () => {
  clearError();
  try {
    const presets = await getPresets();
    const result = await (await api('aging-demo', config({ processes: presets.starvation }))).json();
    renderGantt('#aging-plain', result.without_aging);
    renderGantt('#aging-fixed', result.with_aging);
    const before = result.before.starved_processes.length;
    const after = result.after.starved_processes.length;
    $('#aging-summary').innerHTML = `<div class="aging-pill"><strong>${before}</strong>starved without aging</div><div class="aging-pill"><strong>${after}</strong>starved with aging</div><div class="aging-pill"><strong>${result.without_aging.processes[0].first_start} → ${result.with_aging.processes[0].first_start}</strong>P1 first scheduled</div><div class="aging-pill"><strong>${result.without_aging.average_waiting_time.toFixed(1)} → ${result.with_aging.average_waiting_time.toFixed(1)}</strong>average waiting time</div>`;
    renderAgingCharts(result);
  } catch (error) {
    showError(error);
  }
};

$$('.export-actions button').forEach(button => button.onclick = async () => {
  clearError();
  try {
    const response = await api('export', config({ format: button.dataset.format }));
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `schedule.${button.dataset.format}`;
    anchor.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    showError(error);
  }
});

$('#preset').dispatchEvent(new Event('change'));
