from fastapi.testclient import TestClient

from osscheduler.web.server import app

client = TestClient(app)


def test_dashboard_and_presets_are_served():
    assert client.get("/").status_code == 200
    assert "starvation" in client.get("/api/presets").json()
    assert client.get("/api/algorithms").json()["rr"]["needs_quantum"] is True


def test_simulation_response_contains_trace_and_fairness_metrics():
    response = client.post("/api/simulate", json={"algorithm": "srtf", "processes": [
        {"pid": "P1", "arrival_time": 0, "burst_time": 4},
        {"pid": "P2", "arrival_time": 1, "burst_time": 1}]})
    assert response.status_code == 200
    data = response.json()
    assert data["analysis"]["jain"] > 0
    assert data["trace"]
    threshold = client.post("/api/simulate", json={"algorithm": "fcfs",
        "starvation_threshold": 0, "processes": [
            {"pid": "P1", "arrival_time": 0, "burst_time": 3},
            {"pid": "P2", "arrival_time": 0, "burst_time": 1}]}).json()
    assert threshold["analysis"]["starved_processes"] == ["P2"]


def test_comparison_monte_carlo_sweep_and_aging_endpoints():
    workload = {"processes": [{"pid": "P1", "arrival_time": 0, "burst_time": 3, "priority": 3},
                              {"pid": "P2", "arrival_time": 0, "burst_time": 1, "priority": 0}]}
    assert len(client.post("/api/compare", json=workload).json()) == 7
    assert len(client.post("/api/montecarlo", json={"runs": 2, "process_count": 2}).json()) == 7
    assert len(client.post("/api/quantum-sweep", json={**workload, "max_quantum": 3}).json()["points"]) == 3
    assert client.post("/api/aging-demo", json=workload).status_code == 200


def test_export_endpoint_downloads_requested_format():
    body = {"processes": [{"pid": "P1", "arrival_time": 0, "burst_time": 2}], "format": "pdf"}
    response = client.post("/api/export", json=body)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
