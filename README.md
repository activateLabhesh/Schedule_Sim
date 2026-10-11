# OS Scheduler Lab

A local CPU scheduling simulator for comparing FCFS, SJF, SRTF, priority,
preemptive priority, Round Robin, and Multi-Level Queue scheduling. It includes
priority aging, context-switch overhead, multi-core execution, schedule traces,
fairness analysis, workload experiments, and CSV/JSON/PDF exports.

Priority uses the classic textbook convention: **a lower number means a higher
priority**. Time is measured in integer ticks, and stable ties use PID order.

## Install and launch

Python 3.11 or newer is required.

```sh
python -m pip install -e .
uvicorn osscheduler.web.server:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The interface and Chart.js
are served locally; no CDN is required at runtime.

## CLI

```sh
# Run one algorithm on a preset or custom workload
osscheduler run --algorithm srtf --process P1,0,8 --process P2,1,4

# Compare all seven algorithms
osscheduler compare --preset convoy

# Sweep RR quantum from one through the maximum
osscheduler sweep --preset mixed --max-quantum 16

# Demonstrate the priority starvation case before and after aging
osscheduler demo-aging --aging-interval 3 --aging-step 2

# Export CSV, JSON, or PDF
osscheduler export --algorithm priority --preset aging-fix --format pdf --output report.pdf
```

Custom process values use `PID,ARRIVAL,BURST[,PRIORITY]`. A workload can also
be selected from `convoy`, `starvation`, `aging-fix`, and `mixed` (seeded random).

## Python API

```python
from osscheduler import Process, simulate

workload = [
    Process("P1", arrival_time=0, burst_time=5, priority=2),
    Process("P2", arrival_time=1, burst_time=3, priority=0),
]
result = simulate(workload, "preemptive_priority", aging=True,
                  aging_interval=4, aging_step=1, cores=1,
                  context_switch_cost=1)
print(result.average_waiting_time, result.gantt, result.trace)
```

`simulate` accepts `cores`, `quantum`, `aging`, `aging_interval`,
`aging_step`, and `context_switch_cost`. Each process needs a unique PID,
non-negative arrival time, and positive burst time.

## Web API

- `GET /api/presets`
- `POST /api/simulate`
- `POST /api/compare`
- `POST /api/montecarlo`
- `POST /api/quantum-sweep`
- `POST /api/aging-demo`
- `POST /api/export` (`format`: `csv`, `json`, or `pdf`)

## Included analysis

Per-process outputs include start, completion, turnaround, waiting, response,
and response-ratio measures. Aggregate summaries include mean, median, range,
and standard deviation. Fairness uses Jain’s index and the Gini coefficient;
the starvation report checks waiting time against a threshold. The Little’s
Law panel reports time-average ready-queue length, throughput, average wait,
and the difference between `L` and `λW`.

Monte Carlo runs use deterministic seeds and expose workload ranges, metric
distributions, win rates, and a local JavaScript box-plot renderer. The RR sweep
marks the quantum with the lowest average waiting time. The aging lab compares
fixed priority with aging and plots both accumulated ready wait and effective
priority over time.

## Scheduling models

- **FCFS** runs the earliest arrival first and keeps it on the CPU until it
  finishes. Long jobs can hold up a queue of short jobs (the convoy effect).
- **SJF** chooses the shortest available burst and runs it to completion.
- **SRTF** re-evaluates remaining burst time each tick and can preempt the
  current process when a shorter job arrives.
- **Priority** chooses the smallest priority number and is non-preemptive.
- **Preemptive priority** also re-evaluates priority every tick.
- **Round Robin** rotates processes through a ready queue after each quantum.
- **Multi-Level Queue** divides priority values into ordered classes. The
  default class policies are FCFS for the highest class, SJF for the next, and
  Round Robin for lower classes.

Priority aging changes a waiting process’s effective priority using
`max(0, base_priority - floor(wait / aging_interval) × aging_step)`. Waiting
time accumulates while a process is ready, and effective priorities never go
below zero. The starvation preset provides a stream of short high-priority jobs
that keeps a low-priority process waiting; aging moves it earlier in the
schedule.

The multi-core engine uses a global ready set and dispatches at integer ticks.
It records a per-tick ready queue, effective priorities, CPU state, and
selection explanation. Context-switch cost is charged when a core changes
directly from one process to another. It is visible in the Gantt chart and
included in completion, response, and utilization metrics.

## Verify

```sh
python -m pytest -q
```

The suite covers textbook schedules, algorithm invariants, aging, multi-core
execution, context switches, analytics determinism, exports, and API routes.
