# CPU Scheduling Simulator — Comparative Analysis & Starvation Prevention (Aging)

A Python-based simulator that implements and compares multiple CPU scheduling
algorithms, with a focus on demonstrating and solving the starvation problem in
priority-based scheduling.

---

## 1. Topic & Scope

**Algorithms implemented:**

| Algorithm | Type | Notes |
|---|---|---|
| First Come First Served (FCFS) | Non-preemptive | Baseline, shows convoy effect |
| Shortest Job First (SJF) | Non-preemptive | Optimal avg waiting time |
| Shortest Remaining Time First (SRTF) | Preemptive | Preemptive SJF |
| Priority Scheduling | Non-preemptive | With and without Aging |
| Preemptive Priority Scheduling | Preemptive | Higher priority interrupts |
| Round Robin (RR) | Preemptive | Configurable time quantum |
| Multi-Level Queue (MLQ) | Composite | Multiple priority classes, each with its own internal algorithm |

**Core features:**

- Process input (arrival time, burst time, priority) — CLI or web UI
- Gantt chart visualization for each algorithm
- Performance metrics: average waiting time, average turnaround time,
  response time, throughput, CPU utilization
- Side-by-side comparison table/graph across all algorithms
- Aging module: dedicated demo showing a low-priority process starving under
  plain Priority Scheduling, then getting scheduled successfully once aging is
  applied — with a waiting-time-over-time graph showing priority boost
- Context switch overhead as a configurable parameter
- Exportable report (CSV/JSON/PDF) of all metrics

**OS Concepts Demonstrated:** CPU Scheduling, Process Management, Starvation &
Aging, Multi-Level Queue Scheduling, Performance Analysis.

---

## 2. Locked Design Decisions

- **UI**: local web app (FastAPI + vanilla SPA + Chart.js, vendored locally —
  no CDN dependency at runtime).
- **Advanced features in scope** (all six):
  1. Monte Carlo comparison suite
  2. Fairness & starvation analytics
  3. RR quantum sweep
  4. Live animated playback
  5. Educational decision trace
  6. Multi-core (k CPUs) simulation
- **Exports**: CSV + JSON + PDF (reportlab — built-in chart primitives, no
  matplotlib needed).
- **Priority convention**: lower number = higher priority (classic textbook),
  documented everywhere in UI and docs.
- **Time model**: integer ticks, 1 tick = 1 time unit; deterministic
  tie-breaking by PID.
- **Environment**: Python 3.14; `numpy`, `pandas`, `pytest`, `rich`, `uvicorn`
  already installed; `fastapi` + `reportlab` installed into a `.venv`
  (PyPI network access confirmed).

---

## 3. Features Beyond the Base Scope

1. **Monte Carlo comparison** — run all algorithms over N seeded random
   workloads; distributions, win-rates, std dev; custom JS box-plot renderer
   (Chart.js core has no boxplot) plus stats tables.
2. **Fairness & starvation analytics** — Jain's fairness index, Gini
   coefficient of waiting times, per-process starvation detector
   (wait > threshold), aging effectiveness before/after report,
   Little's Law verification panel (L ≈ λW).
3. **RR quantum sweep** — auto-run RR over quantum = 1..K, chart avg
   waiting/turnaround vs quantum with optimum marked.
4. **Live animated playback** — play/pause/step at configurable speed with an
   animated Gantt cursor, ready-queue visual, and current CPU state sync.
5. **Educational decision trace** — "why P2 was chosen over P3 at t=7" event
   log per tick, synced with playback.
6. **Multi-core (k CPUs) simulation** — global ready queue, per-core dispatch;
   verified via invariants.
7. **Context-switch overhead** — ideal vs effective metrics, switch counts per
   algorithm.
8. **Textbook verification suite** — pytest cases replicating Galvin textbook
   examples so correctness is provable.
9. **Presets** — convoy effect (FCFS), classic starvation scenario,
   aging-fixed scenario, mixed random.

---

## 4. Architecture

```
OsScheduler/
├── pyproject.toml / requirements.txt / README.md
├── osscheduler/
│   ├── models.py          # Process, GanttBlock, TickSnapshot, ScheduleResult, DecisionEvent
│   ├── engine.py          # k-core tick loop: admission → aging → dispatch/preempt → ctx-switch → execute
│   ├── aging.py           # aging strategies (interval + boost step, clamped at 0), priority history
│   ├── workloads.py       # presets (convoy, starvation, aging-fix, mixed) + seeded random generator
│   ├── metrics.py         # per-process & aggregate metrics, Jain's index, Gini, starvation detector, Little's Law check
│   ├── analytics.py       # compare-all, Monte Carlo, quantum sweep
│   ├── export.py          # CSV, JSON, PDF report (reportlab: tables + native Gantt/line/bar charts)
│   ├── algorithms/
│   │   ├── base.py        # Scheduler ABC: pick_next(ready, running, t), should_preempt(...)
│   │   ├── fcfs.py  sjf.py  srtf.py  priority.py  preemptive_priority.py  rr.py  mlq.py
│   │   └── __init__.py    # registry + metadata (preemptive?, needs quantum?, supports aging?)
│   ├── cli.py             # rich CLI: run / compare / sweep / demo-aging / export
│   └── web/
│       ├── server.py      # FastAPI: /api/simulate, /compare, /montecarlo, /quantum-sweep, /aging-demo, /presets, /export
│       ├── schemas.py     # pydantic request/response models
│       └── static/        # index.html, css/app.css, js/{app,gantt,playback,charts,api}.js, vendor/chart.js
└── tests/                 # test_algorithms, test_aging, test_metrics, test_engine_multicore, test_analytics
```

---

## 5. Engine Spec (the heart — built once, all features ride on it)

- **Multi-core from day one**: `k` CPUs (default 1), global ready queue; each
  core dispatches per algorithm rules. RR keeps a per-CPU quantum; MLQ cores
  pick from the highest-priority non-empty class queue. Verified by invariant
  tests (no core overlaps, Σrun ticks = Σbursts).
- **Per-tick trace**: every tick emits — per-core state (pid/idle/switching),
  ordered ready queue with *effective priorities*, and decision events with
  human-readable reasons ("P2 preempted P1: remaining 3 < 7"). This single
  trace powers Gantt, playback, decision log, and aging charts.
- **Context-switch overhead**: configurable cost in ticks; CPU enters
  `switching` state; report shows ideal vs effective metrics and switch counts
  per algorithm.
- **Aging**: `effective_priority = max(0, priority − floor(wait / aging_interval) × boost_step)`;
  full priority-over-time history recorded per process. Implemented as a
  reusable hook — the same Priority algorithm runs with/without it.

---

## 6. Metrics

**Per process**: arrival, burst, start (first run), completion,
TAT = C − A, WT = TAT − B, RT = first_start − A, response ratio,
effective priority at run, waiting-time series (for aging visualization).

**Aggregate**: avg/median/min/max/std of WT, TAT, RT; throughput; CPU
utilization % (busy ticks / total); context switches; total switching overhead;
fairness (Jain's index, Gini coefficient); starvation report (processes with
wait > threshold).

**Little's Law panel**: L = time-average ready-queue length, λ = throughput,
W = avg waiting time → display |L − λW| check.

---

## 7. Web UI (tabbed dashboard)

1. **Configure** — editable process table, presets, params: quantum, aging
   interval/step, ctx-switch cost, cores k, seed; input validation.
2. **Single Run** — per-core Gantt, metric cards, per-process table, playback
   (play/pause/step/speed) with ready-queue visual and synced decision-trace
   panel.
3. **Compare All** — table + grouped bar charts + per-core Gantt heatmap
   across all algorithms on one workload.
4. **Monte Carlo** — N, process count, ranges → box plots + win-rate + stats
   table.
5. **Quantum Sweep** — RR curve over quantum range.
6. **Aging Lab** — the showcase: starvation preset side-by-side (without vs
   with aging), Gantt both ways, waiting-time-over-time chart, priority-boost
   graph, explanatory text.
7. **Export** — CSV / JSON / PDF download buttons.

**Backend endpoints**: `GET /api/presets`; `POST /api/simulate`,
`/api/compare`, `/api/montecarlo`, `/api/quantum-sweep`, `/api/aging-demo`,
`/api/export`.

---

## 8. Testing & Verification

- Textbook (Galvin) hand-computed examples per algorithm.
- Aging: starved process eventually runs; boost schedule exact.
- Invariants: TAT = WT + B for all; utilization ≤ 100%; trace consistent with
  Gantt; multi-core non-overlap; Monte Carlo determinism by seed.
- Edge cases: idle gaps, simultaneous arrivals, all-equal priorities,
  quantum = 1 vs quantum ≥ max burst equivalence property.
- Run: `pytest`.

---

## 9. Milestones (each ends runnable + tested)

1. **Scaffold + engine + FCFS/SJF/SRTF + metrics** → pytest green
2. **Priority ± Aging, Preemptive Priority, RR, MLQ** → pytest green
3. **Analytics + exports (CSV/JSON/PDF)** → CLI usable end-to-end
4. **FastAPI backend** → endpoints return correct JSON
5. **Frontend: configure + single run + Gantt + playback + trace**
6. **Frontend: compare / Monte Carlo / sweep / aging lab + exports**
7. **Polish**: README with algorithm explainers (course-report ready),
   presets, final QA

---

## 10. Dependencies

- `.venv` with: `fastapi`, `uvicorn`, `reportlab` (PyPI network confirmed).
- Already present: `pytest`, `rich`, `numpy`, `pandas`.
- Frontend: Chart.js vendored into `osscheduler/web/static/vendor/`.
