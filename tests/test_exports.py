import json

from osscheduler.engine import simulate
from osscheduler.export import to_csv, to_json, to_pdf
from osscheduler.models import Process


def test_json_and_csv_exports_contain_process_metrics():
    result = simulate([Process("P1", 0, 2), Process("P2", 1, 1)], "fcfs")
    assert json.loads(to_json(result))["processes"][0]["pid"] == "P1"
    assert "pid,arrival_time,burst_time" in to_csv(result)
    assert "P2" in to_csv(result)


def test_pdf_export_is_a_valid_pdf_document():
    result = simulate([Process("P1", 0, 2)], "fcfs")
    assert to_pdf(result).startswith(b"%PDF")
