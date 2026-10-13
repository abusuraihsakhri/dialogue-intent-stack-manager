"""Regression tests for genuine stack behavior, CSV parsing, and API boundaries."""
import copy
import csv

import pytest
from fastapi.testclient import TestClient

from intent_stack.stack import IntentStack
from intent_stack.cli import parse_csv_bool as parse_legacy_csv_bool
from cli import main, parse_csv_bool
from agents.api import app
from agents.supervisor import SystemSupervisor
from agents.models import SystemTaskPayload
from agents.base import SecurityException


def test_nested_interruption_and_resume():
    stack = IntentStack(max_depth=3)
    main_frame = stack.push("Write paper", {"section": "methods"})
    stack.push("Check reference")
    assert stack.depth == 2
    assert stack.snapshot()["frames"][0]["state"] == "suspended"
    assert stack.active["intent"] == "Check reference"
    popped = stack.pop()
    assert popped["state"] == "completed"
    assert stack.active["id"] == main_frame["id"]
    assert stack.active["context"]["section"] == "methods"
    stack.pop()
    assert stack.active is None
    with pytest.raises(IndexError):
        stack.pop()


def test_snapshot_round_trip_and_tamper_rejection():
    stack = IntentStack(max_depth=2)
    stack.push("Primary", {"notes": "Safe"})
    stack.push("Interrupt")
    snapshot = stack.snapshot()
    restored = IntentStack(max_depth=2)
    restored.restore(snapshot)
    assert restored.snapshot() == snapshot
    snapshot["frames"][0]["context"]["notes"] = "Mutated"
    assert restored.snapshot()["frames"][0]["context"]["notes"] == "Safe"
    invalid = copy.deepcopy(restored.snapshot())
    invalid["frames"][0]["state"] = "active"
    with pytest.raises(ValueError):
        restored.restore(invalid)
    assert restored.depth == 2
    with pytest.raises(OverflowError):
        restored.push("Overflow")


@pytest.mark.parametrize("parser", [parse_csv_bool, parse_legacy_csv_bool])
@pytest.mark.parametrize(("raw", "expected"), [
    ("TRUE", True), ("False", False), ("0", False), ("1", True),
    (" yes ", True), ("no", False), ("", False), (None, False),
])
def test_boolean_parser(parser, raw, expected):
    assert parser(raw) is expected


@pytest.mark.parametrize("parser", [parse_csv_bool, parse_legacy_csv_bool])
def test_boolean_parser_rejects_unrecognized(parser):
    with pytest.raises(ValueError):
        parser("maybe")


def test_batch_false_is_not_critical(tmp_path):
    source = tmp_path / "input.csv"
    target = tmp_path / "output.csv"
    source.write_text(
        "task_id,target_identifier,primary_metric,secondary_metric,is_critical_flag,status_descriptor\n"
        "X,KEY-1,5,2,False,NOMINAL\n"
        "Y,KEY-2,5,2,True,NOMINAL\n", encoding="utf-8"
    )
    assert main(["batch", "-i", str(source), "-o", str(target)]) == 0
    with target.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["overall_urgency"] == "ROUTINE"
    assert rows[1]["overall_urgency"] == "CRITICAL_STAT_PANIC"


def test_nested_identifier_rejected():
    supervisor = SystemSupervisor()
    payload = SystemTaskPayload(task_id="safe", target_identifier="KEY", primary_metric=1.0,
                                attributes={"notes": ["patient@example.com"]})
    with pytest.raises(SecurityException):
        supervisor.process_task(payload)


def test_api_serves_browser_and_prometheus_format():
    client = TestClient(app)
    assert client.get("/").status_code == 200
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "# TYPE system_tasks_total counter" in response.text
    assert "text/plain" in response.headers["content-type"]
    blocked = client.post("/api/audit", json={
        "task_id": "safe", "target_identifier": "KEY", "primary_metric": 1.0,
        "attributes": {"note": "patient@example.com"}
    })
    assert blocked.status_code == 422
    assert "patient@example.com" not in blocked.text
