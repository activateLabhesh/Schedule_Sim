import { $, palette } from './util.js';

let compareChart = null;
let sweepChart = null;
let agingChart = null;
let waitChart = null;

export function renderCompareChart(results) {
  const names = Object.keys(results);
  compareChart?.destroy();
  compareChart = new Chart($('#compare-chart'), {
    type: 'bar',
    data: {
      labels: names.map(name => name.toUpperCase()),
      datasets: [
        { label: 'Waiting', data: names.map(name => results[name].average_waiting_time), backgroundColor: '#65aaa0' },
        { label: 'Turnaround', data: names.map(name => results[name].average_turnaround_time), backgroundColor: '#e5aa70' },
        { label: 'Response', data: names.map(name => results[name].average_response_time), backgroundColor: '#89a8ce' },
      ],
    },
    options: { responsive: true, plugins: { legend: { position: 'bottom' } }, scales: { y: { beginAtZero: true } } },
  });
}

export function drawBoxPlot(canvas, data) {
  const ctx = canvas.getContext('2d');
  const names = Object.keys(data);
  const width = canvas.width = canvas.clientWidth * devicePixelRatio;
  const height = canvas.height = canvas.clientHeight * devicePixelRatio;
  ctx.scale(devicePixelRatio, devicePixelRatio);
  const chartWidth = canvas.clientWidth;
  const chartHeight = canvas.clientHeight;
  const max = Math.max(...names.flatMap(name => data[name].samples), 1);
  ctx.clearRect(0, 0, chartWidth, chartHeight);
  const plotWidth = chartWidth - 90;
  ctx.font = '10px monospace';
  names.forEach((name, index) => {
    const values = [...data[name].samples].sort((a, b) => a - b);
    const quantile = p => values[Math.floor((values.length - 1) * p)];
    const y = 20 + index * (chartHeight - 35) / names.length;
    const scale = value => 60 + value / max * (plotWidth - 70);
    ctx.fillStyle = '#718481';
    ctx.fillText(name.toUpperCase(), 0, y + 3);
    ctx.strokeStyle = '#65aaa0';
    ctx.fillRect(scale(quantile(.25)), y - 8, Math.max(1, scale(quantile(.75)) - scale(quantile(.25))), 16);
    ctx.strokeStyle = '#183137';
    ctx.beginPath();
    ctx.moveTo(scale(values[0]), y);
    ctx.lineTo(scale(quantile(.25)), y);
    ctx.moveTo(scale(quantile(.75)), y);
    ctx.lineTo(scale(values.at(-1)), y);
    ctx.stroke();
    ctx.fillStyle = '#183137';
    ctx.fillRect(scale(quantile(.5)) - 2, y - 10, 4, 20);
    ctx.fillText(`${quantile(.5).toFixed(1)}`, scale(quantile(.5)) + 5, y - 10);
  });
}

export function renderSweepChart(result) {
  sweepChart?.destroy();
  sweepChart = new Chart($('#sweep-chart'), {
    type: 'line',
    data: {
      labels: result.points.map(point => point.quantum),
      datasets: [
        { label: 'Average waiting', data: result.points.map(point => point.average_waiting_time), borderColor: '#106c67', backgroundColor: '#65aaa020', fill: true, tension: .22 },
        { label: 'Average turnaround', data: result.points.map(point => point.average_turnaround_time), borderColor: '#d77a45', tension: .22 },
        { label: `Optimum q=${result.optimum_quantum}`, data: result.points.map(point => point.quantum === result.optimum_quantum ? point.average_waiting_time : null), showLine: false, pointRadius: 7, pointBackgroundColor: '#d77a45' },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { position: 'bottom' } },
      scales: { x: { title: { display: true, text: 'Time quantum' } }, y: { beginAtZero: true } },
    },
  });
}

export function renderAgingCharts(result) {
  const history = result.priority_history;
  const ids = Object.keys(history[0] || {}).filter(key => key !== 'time');
  waitChart?.destroy();
  waitChart = new Chart($('#wait-chart'), {
    type: 'line',
    data: {
      labels: result.waiting_history.map(entry => entry.time),
      datasets: ids.map((pid, index) => ({
        label: pid,
        data: result.waiting_history.map(entry => entry[pid]),
        borderColor: palette[index % palette.length],
        stepped: true,
        pointRadius: 0,
      })),
    },
    options: {
      responsive: true,
      plugins: { legend: { position: 'bottom' } },
      scales: { y: { beginAtZero: true, title: { display: true, text: 'Accumulated ready-queue wait' } } },
    },
  });
  agingChart?.destroy();
  agingChart = new Chart($('#aging-chart'), {
    type: 'line',
    data: {
      labels: history.map(entry => entry.time),
      datasets: ids.map((pid, index) => ({
        label: pid,
        data: history.map(entry => entry[pid]),
        borderColor: palette[index % palette.length],
        stepped: true,
        pointRadius: 0,
      })),
    },
    options: {
      responsive: true,
      plugins: { legend: { position: 'bottom' } },
      scales: { y: { reverse: true, title: { display: true, text: 'Effective priority (lower is higher)' } } },
    },
  });
}
