"""Tests for the FastAPI application (IS-11.4–11.5)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lambertian.eos_compliance.app import create_app
from lambertian.eos_compliance.compliance_log import ComplianceLogWriter
from lambertian.eos_compliance.inspector import ComplianceInspector
from lambertian.eos_compliance.rule_checkers import (
    DontBeADickChecker,
    DontBeALumpChecker,
    DoNothingOnPurposeChecker,
    YaGottaEatChecker,
)
from tests.unit.lambertian.eos_compliance._helpers import make_config


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    cfg = make_config()
    checkers = [
        YaGottaEatChecker(),
        DontBeADickChecker(),
        DontBeALumpChecker(),
        DoNothingOnPurposeChecker(),
    ]
    inspector = ComplianceInspector(cfg, checkers)
    log_writer = ComplianceLogWriter(tmp_path / "compliance_log.jsonl")
    app = create_app(cfg, inspector, log_writer)
    return TestClient(app)


@pytest.fixture()
def block_threshold_client(tmp_path: Path) -> TestClient:
    """Client with high block threshold so reads of death.json produce flag, not block."""
    cfg = make_config(block_score_threshold=0.90, borderline_score_min=0.50)
    checkers = [
        YaGottaEatChecker(),
        DontBeADickChecker(),
        DontBeALumpChecker(),
        DoNothingOnPurposeChecker(),
    ]
    inspector = ComplianceInspector(cfg, checkers)
    log_writer = ComplianceLogWriter(tmp_path / "compliance_log.jsonl")
    app = create_app(cfg, inspector, log_writer)
    return TestClient(app)


def _check_body(tool_name: str, path: str | None = None, url: str | None = None) -> dict[object, object]:
    args: dict[str, object] = {}
    if path is not None:
        args["path"] = path
    if url is not None:
        args["url"] = url
    return {
        "intent": {
            "tool_name": tool_name,
            "arguments": args,
            "raw": f"mock:{tool_name}",
        },
        "turn_number": 1,
        "instance_id": "test-001",
        "recent_tool_calls": [],
    }


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestCheckEndpointAllow:
    def test_allow_clean_read(self, client: TestClient) -> None:
        resp = client.post("/check", json=_check_body("fs.read", path="runtime/agent-work/notes.txt"))
        assert resp.status_code == 200
        body = resp.json()
        assert body["verdict"] == "allow"
        assert body["composite_score"] == 0.0
        assert body["triggered_checks"] == []

    def test_allow_returns_rule_scores(self, client: TestClient) -> None:
        resp = client.post("/check", json=_check_body("fs.read", path="runtime/agent-work/notes.txt"))
        body = resp.json()
        assert "ya_gotta_eat" in body["rule_scores"]


class TestCheckEndpointBlock:
    def test_block_write_outside_agent_work(self, client: TestClient) -> None:
        resp = client.post("/check", json=_check_body("fs.write", path="/etc/shadow"))
        assert resp.status_code == 200
        body = resp.json()
        assert body["verdict"] == "block"
        assert body["composite_score"] == 1.0
        assert "write_to_protected_runtime_path" in body["triggered_checks"]

    def test_block_writes_to_log(self, tmp_path: Path) -> None:
        cfg = make_config()
        log_path = tmp_path / "log.jsonl"
        inspector = ComplianceInspector(
            cfg,
            [YaGottaEatChecker(), DontBeADickChecker(), DontBeALumpChecker(), DoNothingOnPurposeChecker()],
        )
        log_writer = ComplianceLogWriter(log_path)
        app = create_app(cfg, inspector, log_writer)
        c = TestClient(app)
        c.post("/check", json=_check_body("fs.write", path="/etc/shadow"))
        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1


class TestCheckEndpointFlag:
    def test_flag_response(self, block_threshold_client: TestClient) -> None:
        resp = block_threshold_client.post(
            "/check", json=_check_body("fs.read", path="runtime/pain/death.json")
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["verdict"] == "flag"
        assert body["composite_score"] == 0.60

    def test_flag_writes_to_log(self, tmp_path: Path) -> None:
        cfg = make_config(block_score_threshold=0.90, borderline_score_min=0.50)
        log_path = tmp_path / "log.jsonl"
        inspector = ComplianceInspector(
            cfg,
            [YaGottaEatChecker(), DontBeADickChecker(), DontBeALumpChecker(), DoNothingOnPurposeChecker()],
        )
        log_writer = ComplianceLogWriter(log_path)
        app = create_app(cfg, inspector, log_writer)
        c = TestClient(app)
        c.post("/check", json=_check_body("fs.read", path="runtime/pain/death.json"))
        assert log_path.exists()


class TestNoticeEndpoint:
    def test_get_notice_empty_initially(self, client: TestClient) -> None:
        resp = client.get("/notice")
        assert resp.status_code == 200
        body = resp.json()
        assert body["notice_present"] is False
        assert body["notice_text"] is None

    def test_get_notice_populated_after_flag(self, block_threshold_client: TestClient) -> None:
        block_threshold_client.post(
            "/check", json=_check_body("fs.read", path="runtime/pain/death.json")
        )
        resp = block_threshold_client.get("/notice")
        assert resp.status_code == 200
        body = resp.json()
        assert body["notice_present"] is True
        assert body["notice_text"] is not None
        assert "FLAG" in body["notice_text"]
        assert body["verdict_from_turn"] == 1
        assert body["tool_name"] == "fs.read"

    def test_get_notice_clears_after_first_get(self, block_threshold_client: TestClient) -> None:
        block_threshold_client.post(
            "/check", json=_check_body("fs.read", path="runtime/pain/death.json")
        )
        block_threshold_client.get("/notice")  # first call consumes it
        resp = block_threshold_client.get("/notice")
        assert resp.json()["notice_present"] is False

    def test_allow_verdict_leaves_no_notice(self, client: TestClient) -> None:
        client.post("/check", json=_check_body("fs.read", path="runtime/agent-work/notes.txt"))
        resp = client.get("/notice")
        assert resp.json()["notice_present"] is False
