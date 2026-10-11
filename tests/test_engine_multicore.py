from osscheduler.engine import simulate
from osscheduler.models import Process


def test_multicore_has_no_process_double_execution_and_conserves_bursts():
    workload = [Process("P1", 0, 7), Process("P2", 0, 4), Process("P3", 1, 3)]
    result = simulate(workload, "srtf", cores=2)
    for snapshot in result.trace:
        busy = [pid for pid in snapshot.running if pid]
        assert len(busy) == len(set(busy))
    for process in workload:
        ran = sum(b.end - b.start for b in result.gantt
                  if b.pid == process.pid and b.state == "running")
        assert ran == process.burst_time
    for core in range(2):
        blocks = sorted((b for b in result.gantt if b.core == core), key=lambda b: b.start)
        assert all(a.end <= b.start for a, b in zip(blocks, blocks[1:]))


def test_context_switch_overhead_is_visible_and_counted():
    result = simulate([Process("P1", 0, 1), Process("P2", 0, 1)],
                      "fcfs", context_switch_cost=2)
    assert result.context_switches == 1
    assert result.switching_overhead == 2
    assert result.makespan == 4
    assert sum(b.end - b.start for b in result.gantt if b.state == "switching") == 2


def test_preemptive_context_switch_delays_execution_and_updates_response_metrics():
    result = simulate([Process("P1", 0, 4), Process("P2", 1, 1)],
                      "srtf", context_switch_cost=1)
    assert result.context_switches == 2
    assert result.switching_overhead == 2
    assert result.makespan == 7
    assert [p.waiting_time for p in result.processes] == [3, 1]
