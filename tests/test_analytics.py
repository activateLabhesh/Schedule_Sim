from osscheduler.analytics import aging_demo, monte_carlo, quantum_sweep
from osscheduler.metrics import analyze_result
from osscheduler.engine import simulate
from osscheduler.models import Process


def test_fairness_and_little_law_report_has_expected_fields():
    result = simulate([Process("P1", 0, 2), Process("P2", 0, 2)], "fcfs")
    data = analyze_result(result)
    assert 0 < data["jain"] <= 1
    assert 0 <= data["gini"] <= 1
    assert "absolute_error" in data["little_law"]


def test_seeded_monte_carlo_is_deterministic():
    assert monte_carlo(runs=3, process_count=4, seed=7) == monte_carlo(runs=3, process_count=4, seed=7)


def test_sweep_and_aging_demo_return_plot_data():
    workload = [Process("P1", 0, 5, 5), Process("P2", 0, 2, 0)]
    assert len(quantum_sweep(workload, max_quantum=4)["points"]) == 4
    demo = aging_demo(workload)
    assert demo["priority_history"]
    assert demo["without_aging"].algorithm == "priority"
