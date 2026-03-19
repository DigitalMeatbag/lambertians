"""Tests for TOML loader — loads the real config/universe.toml and spot-checks values."""

from __future__ import annotations

from pathlib import Path

import pytest

from lambertian.configuration.loader import ConfigurationError, load_config
from lambertian.configuration.universe_config import Config


@pytest.fixture()
def config() -> Config:
    return load_config(Path("config/universe.toml"))


def test_universe_phase(config: Config) -> None:
    assert config.universe.phase == "phase2"


def test_universe_instance_count(config: Config) -> None:
    assert config.universe.instance_count == 1


def test_universe_instance_id(config: Config) -> None:
    assert config.universe.instance_id == "lambertian-001"


def test_universe_max_age_turns(config: Config) -> None:
    assert config.universe.max_age_turns == 500


def test_model_provider(config: Config) -> None:
    assert config.model.provider == "ollama"


def test_model_name(config: Config) -> None:
    assert config.model.name == "qwen2.5:14b"


def test_model_temperature(config: Config) -> None:
    assert config.model.temperature == pytest.approx(0.6)


def test_model_active_profile_resolves(config: Config) -> None:
    """Active profile resolves to the expected model name."""
    assert config.model.name == "qwen2.5:14b"
    assert config.model.provider == "ollama"
    assert config.model.context_window_tokens == 16384


def test_model_unknown_profile_raises(tmp_path: Path) -> None:
    good = Path("config/universe.toml").read_bytes()
    bad = good.replace(b'active_profile = "qwen2.5:14b"', b'active_profile = "nonexistent"')
    toml_file = tmp_path / "bad.toml"
    toml_file.write_bytes(bad)
    with pytest.raises(ConfigurationError, match="nonexistent"):
        load_config(toml_file)


def test_eos_label(config: Config) -> None:
    assert config.eos.label == "Four Rules"


def test_eos_rule_1(config: Config) -> None:
    assert config.eos.rule_1 == "Ya gotta eat"


def test_pain_stress_death_threshold(config: Config) -> None:
    assert config.pain.stress.death_threshold == pytest.approx(0.90)


def test_pain_stress_cpu_weight(config: Config) -> None:
    assert config.pain.stress.cpu_weight == pytest.approx(0.60)


def test_pain_events_critical_threshold(config: Config) -> None:
    assert config.pain.events.critical_threshold == pytest.approx(0.95)


def test_memory_episodic_enabled(config: Config) -> None:
    assert config.memory.episodic_enabled is True


def test_memory_phase1_guards(config: Config) -> None:
    assert config.memory.narrative_enabled is False
    assert config.memory.semantic_enabled is False
    assert config.memory.character_enabled is False


def test_compliance_service_port(config: Config) -> None:
    assert config.compliance.service_port == 8082


def test_paths_runtime_root(config: Config) -> None:
    assert config.paths.runtime_root == "runtime"


def test_fitness_active_function(config: Config) -> None:
    assert config.fitness.active_function == "phase2_quality_weighted"


def test_fitness_quality_primary_weight(config: Config) -> None:
    assert config.fitness.quality.primary_weight == pytest.approx(1.0)


def test_fitness_quality_repetition_weight(config: Config) -> None:
    assert config.fitness.quality.repetition_weight == pytest.approx(0.1)


def test_fitness_quality_expected_quality_score(config: Config) -> None:
    assert config.fitness.quality.expected_quality_score == pytest.approx(500.0)


def test_env_monitor_update_interval(config: Config) -> None:
    assert config.env_monitor.update_interval_seconds == 10


def test_env_monitor_output_path(config: Config) -> None:
    assert config.env_monitor.output_path == "runtime/env/host_state.json"


def test_missing_section_raises(tmp_path: Path) -> None:
    toml_file = tmp_path / "bad.toml"
    toml_file.write_bytes(b"[universe]\nphase = 'x'\n")
    with pytest.raises(ConfigurationError):
        load_config(toml_file)


def test_wrong_type_raises(tmp_path: Path) -> None:
    good = Path("config/universe.toml").read_bytes()
    # Replace the integer instance_count with a string.
    bad = good.replace(b"instance_count                = 1", b'instance_count = "one"')
    toml_file = tmp_path / "bad.toml"
    toml_file.write_bytes(bad)
    with pytest.raises(ConfigurationError, match="instance_count"):
        load_config(toml_file)

