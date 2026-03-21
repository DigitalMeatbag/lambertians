"""ComponentFactory — creates individual agent components. IS-5.4."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from lambertian.configuration.universe_config import Config
from lambertian.event_stream.event_log_writer import EventLogWriter
from lambertian.fitness.cursor_state import FitnessCursorStore
from lambertian.fitness.event_reader import EventStreamReader
from lambertian.fitness.pain_reader import PainHistoryReader
from lambertian.fitness.registry import build_default_registry
from lambertian.fitness.scorer import FitnessScorer
from lambertian.lifecycle.death_record_reader import DeathRecordReader
from lambertian.mcp_gateway.gateway import McpGateway
from lambertian.mcp_gateway.path_resolver import PathResolver
from lambertian.mcp_gateway.semantic_shim import SemanticShimRegistry, build_shim_registry
from lambertian.model_runtime.ollama_client import OllamaClient
from lambertian.pain_monitor.death_guard import DeathGuard
from lambertian.pain_monitor.delivery_queue import DeliveryQueue
from lambertian.pain_monitor.event_submitter import FilePainEventSubmitter
from lambertian.self_model.prompt_block_assembler import PromptBlockAssembler
from lambertian.self_model.self_model_writer import SelfModelWriter
from lambertian.turn_engine.compliance_client import ComplianceClient
from lambertian.turn_engine.self_prompt import SelfPromptGenerator
from lambertian.turn_engine.turn_state import TurnStateStore

_log = logging.getLogger(__name__)


class ComponentFactory:
    """Static factory methods for each agent component. Isolates construction for testability."""

    @staticmethod
    def create_event_log(config: Config) -> EventLogWriter:
        return EventLogWriter(config)

    @staticmethod
    def create_self_model_writer(config: Config, self_model_dir: Path) -> SelfModelWriter:
        return SelfModelWriter(config, self_model_dir)

    @staticmethod
    def create_death_reader(death_path: Path) -> DeathRecordReader:
        return DeathRecordReader(death_path)

    @staticmethod
    def create_death_guard(config: Config, death_path: Path) -> DeathGuard:
        return DeathGuard(config, death_path)

    @staticmethod
    def create_model_client(config: Config) -> OllamaClient:
        return OllamaClient(config)

    @staticmethod
    def create_shim_registry(config: Config) -> Optional[SemanticShimRegistry]:
        return build_shim_registry(config)

    @staticmethod
    def create_mcp_gateway(
        config: Config,
        runtime_root: Path,
        shim_registry: Optional[SemanticShimRegistry],
    ) -> McpGateway:
        return McpGateway(
            config,
            PathResolver(runtime_root, Path("config")),
            shim_registry=shim_registry,
        )

    @staticmethod
    def create_compliance_client(config: Config) -> ComplianceClient:
        return ComplianceClient(config)

    @staticmethod
    def create_block_assembler(config: Config) -> PromptBlockAssembler:
        constitution_text = Path(config.instance.constitution_path).read_text(encoding="utf-8")
        return PromptBlockAssembler(config, constitution_text)

    @staticmethod
    def create_turn_state(memory_dir: Path) -> TurnStateStore:
        return TurnStateStore(memory_dir)

    @staticmethod
    def create_self_prompt_gen(config: Config) -> SelfPromptGenerator:
        return SelfPromptGenerator(config)

    @staticmethod
    def create_delivery_queue(pain_root: Path) -> DeliveryQueue:
        return DeliveryQueue(pain_root / "delivery_queue.json")

    @staticmethod
    def create_pain_submitter(pain_root: Path) -> FilePainEventSubmitter:
        return FilePainEventSubmitter(pain_root / "event_queue.jsonl")

    @staticmethod
    def create_fitness_scorer(
        config: Config,
        fitness_state_path: Path,
        fitness_score_path: Path,
        event_stream_dir: Path,
        pain_root: Path,
    ) -> FitnessScorer:
        return FitnessScorer(
            config=config,
            registry=build_default_registry(quality_config=config.fitness.quality),
            cursor_store=FitnessCursorStore(fitness_state_path),
            event_reader=EventStreamReader(event_stream_dir),
            pain_reader=PainHistoryReader(pain_root / "pain_history.jsonl"),
            output_path=fitness_score_path,
        )
