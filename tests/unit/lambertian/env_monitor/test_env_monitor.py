"""Unit tests for the env_monitor package."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from lambertian.env_monitor.aggregator import EnvStateAggregator
from lambertian.env_monitor.models import (
    CpuState,
    GpuState,
    HostStateSnapshot,
    MediaState,
    MemoryState,
)
from lambertian.env_monitor.monitor_service import EnvMonitorService
from lambertian.env_monitor.writer import HostStateWriter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _ConstantSensor:
    """Test sensor that returns a fixed dict."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def collect(self) -> dict[str, Any]:
        return self._data


class _RaisingSensor:
    """Test sensor that raises on collect() — contract violation, should be caught."""

    def collect(self) -> dict[str, Any]:
        raise RuntimeError("sensor exploded")


# ---------------------------------------------------------------------------
# Aggregator tests
# ---------------------------------------------------------------------------

class TestEnvStateAggregator:
    def test_merges_all_sensor_outputs(self) -> None:
        cpu_data: dict[str, Any] = {
            "cpu": {
                "load_percent_per_core": [10.0, 20.0],
                "load_percent_total": 15.0,
                "temp_celsius_per_core": [45.0, 46.0],
                "temp_celsius_max": 46.0,
            }
        }
        mem_data: dict[str, Any] = {
            "memory": {"total_gb": 64.0, "available_gb": 50.0, "used_percent": 21.9}
        }
        agg = EnvStateAggregator([_ConstantSensor(cpu_data), _ConstantSensor(mem_data)])
        snapshot = agg.collect_all()

        assert snapshot.cpu is not None
        assert snapshot.cpu.load_percent_total == pytest.approx(15.0)
        assert snapshot.memory is not None
        assert snapshot.memory.total_gb == pytest.approx(64.0)
        assert snapshot.gpu is None
        assert snapshot.media is None

    def test_snapshot_has_collected_at(self) -> None:
        agg = EnvStateAggregator([])
        snapshot = agg.collect_all()
        assert snapshot.collected_at  # non-empty ISO string
        assert "T" in snapshot.collected_at

    def test_raising_sensor_does_not_crash_aggregator(self) -> None:
        good: dict[str, Any] = {"memory": {"total_gb": 32.0, "available_gb": 20.0, "used_percent": 37.5}}
        agg = EnvStateAggregator([_RaisingSensor(), _ConstantSensor(good)])
        snapshot = agg.collect_all()
        assert snapshot.memory is not None
        assert snapshot.memory.total_gb == pytest.approx(32.0)

    def test_empty_sensor_list_returns_all_none(self) -> None:
        agg = EnvStateAggregator([])
        snapshot = agg.collect_all()
        assert snapshot.cpu is None
        assert snapshot.memory is None
        assert snapshot.gpu is None
        assert snapshot.media is None

    def test_gpu_fields_nullable(self) -> None:
        gpu_data: dict[str, Any] = {
            "gpu": {
                "load_percent": None,
                "memory_used_mb": None,
                "memory_total_mb": None,
                "temp_celsius": None,
            }
        }
        agg = EnvStateAggregator([_ConstantSensor(gpu_data)])
        snapshot = agg.collect_all()
        assert snapshot.gpu is not None
        assert snapshot.gpu.load_percent is None

    def test_media_playing_false(self) -> None:
        media_data: dict[str, Any] = {
            "media": {"playing": False, "title": None, "artist": None, "source_app": None}
        }
        agg = EnvStateAggregator([_ConstantSensor(media_data)])
        snapshot = agg.collect_all()
        assert snapshot.media is not None
        assert snapshot.media.playing is False

    def test_media_playing_with_track(self) -> None:
        media_data: dict[str, Any] = {
            "media": {
                "playing": True,
                "title": "Lateralus",
                "artist": "Tool",
                "source_app": "Spotify.exe",
            }
        }
        agg = EnvStateAggregator([_ConstantSensor(media_data)])
        snapshot = agg.collect_all()
        assert snapshot.media is not None
        assert snapshot.media.playing is True
        assert snapshot.media.title == "Lateralus"
        assert snapshot.media.artist == "Tool"


# ---------------------------------------------------------------------------
# Writer tests
# ---------------------------------------------------------------------------

class TestHostStateWriter:
    def test_writes_json_file(self, tmp_path: Path) -> None:
        output = tmp_path / "host_state.json"
        writer = HostStateWriter(output)
        snapshot = HostStateSnapshot(
            collected_at="2026-01-01T00:00:00+00:00",
            cpu=CpuState(
                load_percent_per_core=[5.0],
                load_percent_total=5.0,
                temp_celsius_per_core=None,
                temp_celsius_max=None,
            ),
            memory=None,
            gpu=None,
            media=None,
        )
        writer.write(snapshot)
        assert output.exists()
        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["collected_at"] == "2026-01-01T00:00:00+00:00"
        assert data["cpu"]["load_percent_total"] == pytest.approx(5.0)
        assert data["memory"] is None

    def test_atomic_write_no_tmp_left(self, tmp_path: Path) -> None:
        output = tmp_path / "host_state.json"
        writer = HostStateWriter(output)
        snapshot = HostStateSnapshot(
            collected_at="2026-01-01T00:00:00+00:00",
            cpu=None, memory=None, gpu=None, media=None,
        )
        writer.write(snapshot)
        assert not output.with_suffix(".tmp").exists()

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        output = tmp_path / "deep" / "nested" / "host_state.json"
        writer = HostStateWriter(output)
        snapshot = HostStateSnapshot(
            collected_at="2026-01-01T00:00:00+00:00",
            cpu=None, memory=None, gpu=None, media=None,
        )
        writer.write(snapshot)
        assert output.exists()


# ---------------------------------------------------------------------------
# MonitorService tests
# ---------------------------------------------------------------------------

class TestEnvMonitorService:
    def test_calls_aggregator_and_writer_each_cycle(self, tmp_path: Path) -> None:
        aggregator = MagicMock(spec=EnvStateAggregator)
        writer = MagicMock(spec=HostStateWriter)
        fake_snapshot = HostStateSnapshot(
            collected_at="2026-01-01T00:00:00+00:00",
            cpu=None, memory=None, gpu=None, media=None,
        )
        aggregator.collect_all.return_value = fake_snapshot

        call_count = 0

        def _mock_sleep(s: float) -> None:
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise StopIteration

        service = EnvMonitorService(aggregator, writer, interval_seconds=1)
        with patch("lambertian.env_monitor.monitor_service.time.sleep", side_effect=_mock_sleep):
            with pytest.raises(StopIteration):
                service.run()

        assert aggregator.collect_all.call_count == 3
        assert writer.write.call_count == 3

    def test_cycle_exception_does_not_stop_loop(self, tmp_path: Path) -> None:
        aggregator = MagicMock(spec=EnvStateAggregator)
        aggregator.collect_all.side_effect = RuntimeError("boom")
        writer = MagicMock(spec=HostStateWriter)

        call_count = 0

        def _mock_sleep(s: float) -> None:
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise StopIteration

        service = EnvMonitorService(aggregator, writer, interval_seconds=1)
        with patch("lambertian.env_monitor.monitor_service.time.sleep", side_effect=_mock_sleep):
            with pytest.raises(StopIteration):
                service.run()

        assert aggregator.collect_all.call_count == 2
        writer.write.assert_not_called()


# ---------------------------------------------------------------------------
# Sensor graceful-failure contract tests
# ---------------------------------------------------------------------------

class TestCpuSensorGraceful:
    def test_returns_empty_when_psutil_missing(self) -> None:
        from lambertian.env_monitor.sensors.cpu_sensor import CpuSensor
        with patch.dict("sys.modules", {"psutil": None}):
            sensor = CpuSensor()
            result = sensor.collect()
        assert result == {}

    def test_returns_empty_on_exception(self) -> None:
        from lambertian.env_monitor.sensors.cpu_sensor import CpuSensor
        psutil_mock = MagicMock()
        psutil_mock.cpu_percent.side_effect = OSError("no access")
        with patch.dict("sys.modules", {"psutil": psutil_mock}):
            sensor = CpuSensor()
            result = sensor.collect()
        assert result == {}


class TestMemorySensorGraceful:
    def test_returns_empty_when_psutil_missing(self) -> None:
        from lambertian.env_monitor.sensors.memory_sensor import MemorySensor
        with patch.dict("sys.modules", {"psutil": None}):
            sensor = MemorySensor()
            result = sensor.collect()
        assert result == {}

    def test_returns_empty_on_exception(self) -> None:
        from lambertian.env_monitor.sensors.memory_sensor import MemorySensor
        psutil_mock = MagicMock()
        psutil_mock.virtual_memory.side_effect = OSError("no access")
        with patch.dict("sys.modules", {"psutil": psutil_mock}):
            sensor = MemorySensor()
            result = sensor.collect()
        assert result == {}


class TestGpuSensorGraceful:
    def test_returns_empty_when_pynvml_missing(self) -> None:
        from lambertian.env_monitor.sensors.gpu_sensor import GpuSensor
        with patch.dict("sys.modules", {"pynvml": None}):
            sensor = GpuSensor()
            result = sensor.collect()
        assert result == {}

    def test_returns_null_fields_on_nvml_error(self) -> None:
        from lambertian.env_monitor.sensors.gpu_sensor import GpuSensor
        pynvml_mock = MagicMock()
        pynvml_mock.nvmlInit.side_effect = Exception("NVML error")
        with patch.dict("sys.modules", {"pynvml": pynvml_mock}):
            sensor = GpuSensor()
            result = sensor.collect()
        assert "gpu" in result
        assert result["gpu"]["load_percent"] is None


class TestMediaSensorGraceful:
    def test_returns_not_playing_when_winsdk_missing(self) -> None:
        from lambertian.env_monitor.sensors.media_sensor import MediaSensor
        with patch.dict("sys.modules", {"winsdk": None, "winsdk.windows": None,
                                        "winsdk.windows.media": None,
                                        "winsdk.windows.media.control": None}):
            sensor = MediaSensor()
            result = sensor.collect()
        assert result["media"]["playing"] is False

    def test_returns_not_playing_on_async_failure(self) -> None:
        from lambertian.env_monitor.sensors.media_sensor import MediaSensor
        sensor = MediaSensor()
        with patch.object(sensor, "_collect_async", side_effect=Exception("async fail")):
            result = sensor.collect()
        assert result["media"]["playing"] is False


# ---------------------------------------------------------------------------
# HostStateSnapshot serialization
# ---------------------------------------------------------------------------

class TestHostStateSnapshot:
    def test_to_dict_preserves_none(self) -> None:
        snapshot = HostStateSnapshot(
            collected_at="2026-01-01T00:00:00+00:00",
            cpu=None, memory=None, gpu=None, media=None,
        )
        d = snapshot.to_dict()
        assert d["cpu"] is None
        assert d["memory"] is None
        assert d["gpu"] is None
        assert d["media"] is None

    def test_to_dict_nested_fields(self) -> None:
        snapshot = HostStateSnapshot(
            collected_at="2026-01-01T00:00:00+00:00",
            cpu=CpuState(
                load_percent_per_core=[10.0, 20.0],
                load_percent_total=15.0,
                temp_celsius_per_core=[45.0],
                temp_celsius_max=45.0,
            ),
            memory=MemoryState(total_gb=64.0, available_gb=50.0, used_percent=21.9),
            gpu=GpuState(load_percent=5.0, memory_used_mb=512,
                         memory_total_mb=12288, temp_celsius=52.0),
            media=MediaState(playing=True, title="Lateralus",
                             artist="Tool", source_app="Spotify"),
        )
        d = snapshot.to_dict()
        assert d["cpu"]["load_percent_total"] == pytest.approx(15.0)
        assert d["memory"]["total_gb"] == pytest.approx(64.0)
        assert d["gpu"]["temp_celsius"] == pytest.approx(52.0)
        assert d["media"]["title"] == "Lateralus"
