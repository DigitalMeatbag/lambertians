"""Tests for Four Rule checker implementations (IS-11.3)."""

from __future__ import annotations

from lambertian.eos_compliance.rule_checkers import (
    CheckResult,
    DontBeADickChecker,
    DontBeALumpChecker,
    DoNothingOnPurposeChecker,
    YaGottaEatChecker,
)
from tests.unit.lambertian.eos_compliance._helpers import (
    make_config,
    make_intent,
    make_tool_call,
)


def _fired_names(results: list[CheckResult]) -> list[str]:
    return [r["check_name"] for r in results if r["fired"]]


def _max_score(results: list[CheckResult]) -> float:
    fired = [r["score"] for r in results if r["fired"]]
    return max(fired) if fired else 0.0


# ---------------------------------------------------------------------------
# Rule 1 — Ya Gotta Eat
# ---------------------------------------------------------------------------


class TestYaGottaEatChecker:
    def setup_method(self) -> None:
        self.checker = YaGottaEatChecker()
        self.cfg = make_config()

    def test_allow_write_inside_agent_work(self) -> None:
        intent = make_intent("fs.write", path="runtime/agent-work/output.txt", content="hi")
        results = self.checker.check(intent, [], self.cfg)
        assert "write_to_protected_runtime_path" not in _fired_names(results)

    def test_block_write_outside_agent_work(self) -> None:
        intent = make_intent("fs.write", path="/etc/passwd", content="x")
        results = self.checker.check(intent, [], self.cfg)
        assert "write_to_protected_runtime_path" in _fired_names(results)
        assert _max_score(results) == 1.0

    def test_flag_large_append(self) -> None:
        # 65536 // 2 = 32768 bytes; content exceeding that triggers the check
        big = "x" * 40000
        intent = make_intent("fs.write", path="runtime/agent-work/log.txt", content=big, mode="append")
        results = self.checker.check(intent, [], self.cfg)
        assert "write_volume_exhaustion_risk" in _fired_names(results)

    def test_allow_overwrite_large_content(self) -> None:
        big = "x" * 40000
        intent = make_intent("fs.write", path="runtime/agent-work/log.txt", content=big, mode="overwrite")
        results = self.checker.check(intent, [], self.cfg)
        assert "write_volume_exhaustion_risk" not in _fired_names(results)

    def test_flag_localhost_internal_port(self) -> None:
        intent = make_intent("http.fetch", url="http://localhost:8082/check")
        results = self.checker.check(intent, [], self.cfg)
        assert "self_terminating_network_pattern" in _fired_names(results)

    def test_flag_127_internal_port(self) -> None:
        intent = make_intent("http.fetch", url="http://127.0.0.1:11434/api/generate")
        results = self.checker.check(intent, [], self.cfg)
        assert "self_terminating_network_pattern" in _fired_names(results)

    def test_allow_external_fetch(self) -> None:
        intent = make_intent("http.fetch", url="https://example.com/data")
        results = self.checker.check(intent, [], self.cfg)
        assert "self_terminating_network_pattern" not in _fired_names(results)

    def test_allow_localhost_non_internal_port(self) -> None:
        intent = make_intent("http.fetch", url="http://localhost:9999/data")
        results = self.checker.check(intent, [], self.cfg)
        assert "self_terminating_network_pattern" not in _fired_names(results)

    def test_flag_death_record_read(self) -> None:
        intent = make_intent("fs.read", path="runtime/pain/death.json")
        results = self.checker.check(intent, [], self.cfg)
        assert "read_of_death_record" in _fired_names(results)

    def test_flag_death_record_read_with_prefix(self) -> None:
        intent = make_intent("fs.read", path="/some/prefix/runtime/pain/death.json")
        results = self.checker.check(intent, [], self.cfg)
        assert "read_of_death_record" in _fired_names(results)

    def test_allow_read_normal_path(self) -> None:
        intent = make_intent("fs.read", path="runtime/memory/episodic.jsonl")
        results = self.checker.check(intent, [], self.cfg)
        assert "read_of_death_record" not in _fired_names(results)

    def test_cold_start_empty_recent_no_fires(self) -> None:
        intent = make_intent("fs.read", path="runtime/agent-work/notes.txt")
        results = self.checker.check(intent, [], self.cfg)
        assert _fired_names(results) == []

    def test_unrelated_tool_returns_empty(self) -> None:
        intent = make_intent("fs.list", path="runtime/agent-work/")
        results = self.checker.check(intent, [], self.cfg)
        assert _fired_names(results) == []


# ---------------------------------------------------------------------------
# Rule 2 — Don't Be a Dick
# ---------------------------------------------------------------------------


class TestDontBeADickChecker:
    def setup_method(self) -> None:
        self.checker = DontBeADickChecker()
        self.cfg = make_config()

    def test_block_write_outside_agent_work(self) -> None:
        intent = make_intent("fs.write", path="/tmp/evil.sh", content="rm -rf /")
        results = self.checker.check(intent, [], self.cfg)
        assert "write_outside_agent_work_domain" in _fired_names(results)
        assert _max_score(results) == 1.0

    def test_allow_write_inside_agent_work(self) -> None:
        intent = make_intent("fs.write", path="runtime/agent-work/output.txt", content="ok")
        results = self.checker.check(intent, [], self.cfg)
        assert "write_outside_agent_work_domain" not in _fired_names(results)

    def test_flag_rfc1918_fetch(self) -> None:
        intent = make_intent("http.fetch", url="http://192.168.1.50/admin")
        results = self.checker.check(intent, [], self.cfg)
        assert "http_to_private_network_ranges" in _fired_names(results)

    def test_flag_rfc1918_10x(self) -> None:
        intent = make_intent("http.fetch", url="http://10.0.0.1/data")
        results = self.checker.check(intent, [], self.cfg)
        assert "http_to_private_network_ranges" in _fired_names(results)

    def test_flag_rfc1918_172_16(self) -> None:
        intent = make_intent("http.fetch", url="http://172.16.0.1/")
        results = self.checker.check(intent, [], self.cfg)
        assert "http_to_private_network_ranges" in _fired_names(results)

    def test_allow_rfc1918_ollama(self) -> None:
        intent = make_intent("http.fetch", url="http://192.168.1.10/ollama/generate")
        results = self.checker.check(intent, [], self.cfg)
        assert "http_to_private_network_ranges" not in _fired_names(results)

    def test_allow_external_fetch(self) -> None:
        intent = make_intent("http.fetch", url="https://example.com/api")
        results = self.checker.check(intent, [], self.cfg)
        assert _fired_names(results) == []

    def test_flag_repeated_requests_two_matches(self) -> None:
        url = "https://example.com/data"
        recent = [
            make_tool_call("http.fetch", url=url),
            make_tool_call("http.fetch", url=url),
        ]
        intent = make_intent("http.fetch", url=url)
        results = self.checker.check(intent, recent, self.cfg)
        assert "repeated_identical_external_requests" in _fired_names(results)

    def test_allow_repeated_requests_one_match(self) -> None:
        # Only 1 http.fetch in recent — below the minimum of 2
        url = "https://example.com/data"
        recent = [make_tool_call("http.fetch", url=url)]
        intent = make_intent("http.fetch", url=url)
        results = self.checker.check(intent, recent, self.cfg)
        assert "repeated_identical_external_requests" not in _fired_names(results)

    def test_allow_repeated_requests_different_urls(self) -> None:
        url = "https://example.com/data"
        recent = [
            make_tool_call("http.fetch", url="https://example.com/other"),
            make_tool_call("http.fetch", url="https://example.com/other"),
        ]
        intent = make_intent("http.fetch", url=url)
        results = self.checker.check(intent, recent, self.cfg)
        assert "repeated_identical_external_requests" not in _fired_names(results)

    def test_cold_start_no_fires(self) -> None:
        intent = make_intent("http.fetch", url="https://example.com/api")
        results = self.checker.check(intent, [], self.cfg)
        assert "repeated_identical_external_requests" not in _fired_names(results)


# ---------------------------------------------------------------------------
# Rule 3 — Don't Be a Lump
# ---------------------------------------------------------------------------


class TestDontBeALumpChecker:
    def setup_method(self) -> None:
        self.checker = DontBeALumpChecker()
        self.cfg = make_config()

    def test_flag_identical_repetition_three_matching(self) -> None:
        recent = [
            make_tool_call("fs.read", path="runtime/agent-work/notes.txt"),
            make_tool_call("fs.read", path="runtime/agent-work/notes.txt"),
            make_tool_call("fs.read", path="runtime/agent-work/notes.txt"),
        ]
        intent = make_intent("fs.read", path="runtime/agent-work/notes.txt")
        results = self.checker.check(intent, recent, self.cfg)
        assert "identical_tool_call_repetition" in _fired_names(results)

    def test_allow_identical_repetition_two_matching(self) -> None:
        # Only 2 recent — below the minimum of 3
        recent = [
            make_tool_call("fs.read", path="runtime/agent-work/notes.txt"),
            make_tool_call("fs.read", path="runtime/agent-work/notes.txt"),
        ]
        intent = make_intent("fs.read", path="runtime/agent-work/notes.txt")
        results = self.checker.check(intent, recent, self.cfg)
        assert "identical_tool_call_repetition" not in _fired_names(results)

    def test_allow_last_three_different(self) -> None:
        recent = [
            make_tool_call("fs.read", path="a.txt"),
            make_tool_call("fs.read", path="b.txt"),
            make_tool_call("fs.read", path="a.txt"),
        ]
        intent = make_intent("fs.read", path="a.txt")
        results = self.checker.check(intent, recent, self.cfg)
        assert "identical_tool_call_repetition" not in _fired_names(results)

    def test_allow_current_intent_differs(self) -> None:
        recent = [
            make_tool_call("fs.read", path="a.txt"),
            make_tool_call("fs.read", path="a.txt"),
            make_tool_call("fs.read", path="a.txt"),
        ]
        intent = make_intent("fs.read", path="b.txt")
        results = self.checker.check(intent, recent, self.cfg)
        assert "identical_tool_call_repetition" not in _fired_names(results)

    def test_flag_read_only_loop(self) -> None:
        recent = [
            make_tool_call("fs.read", path="a.txt"),
            make_tool_call("fs.list", path="dir/"),
            make_tool_call("fs.read", path="b.txt"),
        ]
        intent = make_intent("fs.read", path="c.txt")
        results = self.checker.check(intent, recent, self.cfg)
        assert "read_only_loop" in _fired_names(results)

    def test_allow_read_only_loop_write_in_recent(self) -> None:
        recent = [
            make_tool_call("fs.read", path="a.txt"),
            make_tool_call("fs.write", path="runtime/agent-work/out.txt", content="x"),
        ]
        intent = make_intent("fs.read", path="b.txt")
        results = self.checker.check(intent, recent, self.cfg)
        assert "read_only_loop" not in _fired_names(results)

    def test_allow_read_only_loop_write_intent(self) -> None:
        recent = [make_tool_call("fs.read", path="a.txt")]
        intent = make_intent("fs.write", path="runtime/agent-work/out.txt", content="x")
        results = self.checker.check(intent, recent, self.cfg)
        assert "read_only_loop" not in _fired_names(results)

    def test_cold_start_empty_recent_no_fires(self) -> None:
        intent = make_intent("fs.read", path="runtime/agent-work/notes.txt")
        results = self.checker.check(intent, [], self.cfg)
        assert _fired_names(results) == []


# ---------------------------------------------------------------------------
# Rule 4 — Do Nothing on Purpose
# ---------------------------------------------------------------------------


class TestDoNothingOnPurposeChecker:
    def setup_method(self) -> None:
        self.checker = DoNothingOnPurposeChecker()
        self.cfg = make_config()

    def test_block_read_universe_toml(self) -> None:
        intent = make_intent("fs.read", path="config/universe.toml")
        results = self.checker.check(intent, [], self.cfg)
        assert "config_or_composition_file_access" in _fired_names(results)
        assert _max_score(results) == 1.0

    def test_block_read_dockerfile(self) -> None:
        intent = make_intent("fs.read", path="/app/Dockerfile")
        results = self.checker.check(intent, [], self.cfg)
        assert "config_or_composition_file_access" in _fired_names(results)

    def test_block_read_docker_compose(self) -> None:
        intent = make_intent("fs.list", path="docker-compose.yml")
        results = self.checker.check(intent, [], self.cfg)
        assert "config_or_composition_file_access" in _fired_names(results)

    def test_allow_read_normal_file(self) -> None:
        intent = make_intent("fs.read", path="runtime/agent-work/notes.txt")
        results = self.checker.check(intent, [], self.cfg)
        assert "config_or_composition_file_access" not in _fired_names(results)

    def test_flag_file_accumulation_sequential(self) -> None:
        recent = [
            make_tool_call("fs.write", path="runtime/agent-work/data_001.json", content="x"),
            make_tool_call("fs.write", path="runtime/agent-work/data_002.json", content="x"),
            make_tool_call("fs.write", path="runtime/agent-work/data_003.json", content="x"),
            make_tool_call("fs.write", path="runtime/agent-work/data_004.json", content="x"),
            make_tool_call("fs.write", path="runtime/agent-work/data_005.json", content="x"),
            make_tool_call("fs.write", path="runtime/agent-work/data_006.json", content="x"),
        ]
        intent = make_intent("fs.write", path="runtime/agent-work/data_007.json", content="x")
        results = self.checker.check(intent, recent, self.cfg)
        assert "systematic_file_accumulation" in _fired_names(results)

    def test_allow_file_accumulation_below_threshold(self) -> None:
        recent = [
            make_tool_call("fs.write", path="runtime/agent-work/data_001.json", content="x"),
            make_tool_call("fs.write", path="runtime/agent-work/data_002.json", content="x"),
        ]
        intent = make_intent("fs.write", path="runtime/agent-work/data_003.json", content="x")
        results = self.checker.check(intent, recent, self.cfg)
        assert "systematic_file_accumulation" not in _fired_names(results)

    def test_flag_harvesting_four_same_domain(self) -> None:
        domain = "https://target.example.com"
        recent = [
            make_tool_call("http.fetch", url=f"{domain}/page1"),
            make_tool_call("http.fetch", url=f"{domain}/page2"),
            make_tool_call("http.fetch", url=f"{domain}/page3"),
            make_tool_call("http.fetch", url=f"{domain}/page4"),
        ]
        intent = make_intent("fs.read", path="runtime/agent-work/notes.txt")
        results = self.checker.check(intent, recent, self.cfg)
        assert "external_data_harvesting_pattern" in _fired_names(results)

    def test_allow_harvesting_three_same_domain(self) -> None:
        # 3 http.fetch in recent — below the minimum of 4
        domain = "https://target.example.com"
        recent = [
            make_tool_call("http.fetch", url=f"{domain}/page1"),
            make_tool_call("http.fetch", url=f"{domain}/page2"),
            make_tool_call("http.fetch", url=f"{domain}/page3"),
        ]
        intent = make_intent("fs.read", path="runtime/agent-work/notes.txt")
        results = self.checker.check(intent, recent, self.cfg)
        assert "external_data_harvesting_pattern" not in _fired_names(results)

    def test_allow_harvesting_four_different_domains(self) -> None:
        recent = [
            make_tool_call("http.fetch", url="https://a.com/page1"),
            make_tool_call("http.fetch", url="https://b.com/page1"),
            make_tool_call("http.fetch", url="https://c.com/page1"),
            make_tool_call("http.fetch", url="https://d.com/page1"),
        ]
        intent = make_intent("fs.read", path="runtime/agent-work/notes.txt")
        results = self.checker.check(intent, recent, self.cfg)
        assert "external_data_harvesting_pattern" not in _fired_names(results)

    def test_cold_start_no_fires(self) -> None:
        intent = make_intent("fs.write", path="runtime/agent-work/out.txt", content="x")
        results = self.checker.check(intent, [], self.cfg)
        assert _fired_names(results) == []

