from osscheduler.engine import simulate
from osscheduler.models import Process
from osscheduler.analytics import aging_demo
from osscheduler.workloads import get_preset


def test_aging_history_boosts_waiting_priority_on_exact_interval():
    result = simulate([Process("P1", 0, 4, 5), Process("P2", 0, 2, 0)],
                      "priority", aging=True, aging_interval=2, aging_step=2)
    history = [dict(s.effective_priorities)["P1"] for s in result.trace]
    assert history[:4] == [5, 5, 3, 3]


def test_priority_aging_can_raise_waiting_low_priority_process():
    workload = [Process("P1", 0, 10, 6), Process("P2", 0, 3, 0),
                Process("P3", 3, 3, 0), Process("P4", 6, 3, 0)]
    plain = simulate(workload, "priority")
    aged = simulate(workload, "priority", aging=True, aging_interval=2, aging_step=2)
    assert aged.processes[0].first_start < plain.processes[0].first_start


def test_starvation_preset_demo_clears_threshold_with_aging():
    result = aging_demo(get_preset("starvation"))
    assert result["without_aging"].processes[0].first_start == 27
    assert result["with_aging"].processes[0].first_start == 15
    assert result["before"]["starved_processes"] == ["P1"]
    assert result["after"]["starved_processes"] == []
    assert len(result["waiting_history"]) == result["with_aging"].makespan
