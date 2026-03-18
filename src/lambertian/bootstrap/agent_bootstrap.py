"""Agent bootstrap sequence. IS-5.4."""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Any

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
from lambertian.memory_store.querier import MemoryQuerier, NoOpMemoryQuerier
from lambertian.model_runtime.ollama_client import OllamaClient
from lambertian.pain_monitor.delivery_queue import DeliveryQueue
from lambertian.pain_monitor.event_submitter import FilePainEventSubmitter
from lambertian.self_model.prompt_block_assembler import PromptBlockAssembler
from lambertian.self_model.self_model_writer import SelfModelWriter
from lambertian.turn_engine.compliance_client import ComplianceClient
from lambertian.turn_engine.engine import StdinUserInputProvider, TurnEngine
from lambertian.turn_engine.self_prompt import SelfPromptGenerator
from lambertian.turn_engine.turn_state import TurnStateStore

_log = logging.getLogger(__name__)


class ChromaMemoryQuerier:
    """Chroma-backed episodic memory querier."""

    def __init__(self, client: Any, config: Config) -> None:
        # Any: chromadb.HttpClient — chromadb is an optional runtime dependency
        self._client = client
        self._config = config
        self._collection = client.get_or_create_collection("episodic")

    def query_episodic(self, text: str, top_k: int) -> list[str]:
        # Any: chromadb query result — untyped third-party return
        results: Any = self._collection.query(
            query_texts=[text],
            n_results=top_k,
        )
        docs: list[str] = []
        for doc_list in results.get("documents", []):
            docs.extend(str(d) for d in doc_list)
        return docs

    def write_episodic(self, content: str, metadata: dict[str, str]) -> str:
        import uuid

        doc_id = str(uuid.uuid4())
        self._collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id],
        )
        return doc_id


class AgentBootstrap:
    """Agent startup sequence. IS-5.4."""

    def __init__(self, config: Config, config_path: Path) -> None:
        self._config = config
        self._config_path = config_path
        self._start_time = time.monotonic()

        memory_dir = Path(config.paths.memory_root)
        pain_root = Path(config.paths.pain_root)
        runtime_root = Path(config.paths.runtime_root)
        self_model_dir = Path(config.paths.self_model_file).parent
        fitness_score_path = Path(config.paths.fitness_file)
        fitness_state_path = fitness_score_path.parent / "state.json"
        event_stream_dir = Path(config.paths.event_stream_file).parent

        self._event_log = EventLogWriter(config)
        self._self_model_writer = SelfModelWriter(config, self_model_dir)
        self._death_reader = DeathRecordReader(pain_root / "death.json")
        self._model_client = OllamaClient(config)
        self._mcp_gateway = McpGateway(
            config,
            PathResolver(runtime_root, Path("config")),
        )
        self._compliance_client = ComplianceClient(config)
        self._block_assembler = PromptBlockAssembler(config)
        self._turn_state = TurnStateStore(memory_dir)
        self._self_prompt_gen = SelfPromptGenerator(config)
        self._delivery_queue = DeliveryQueue(pain_root / "delivery_queue.json")
        self._pain_submitter = FilePainEventSubmitter(pain_root / "event_queue.jsonl")
        self._fitness_scorer = FitnessScorer(
            config=config,
            registry=build_default_registry(),
            cursor_store=FitnessCursorStore(fitness_state_path),
            event_reader=EventStreamReader(event_stream_dir),
            pain_reader=PainHistoryReader(pain_root / "pain_history.jsonl"),
            output_path=fitness_score_path,
        )

    def run(self) -> None:
        """Execute bootstrap steps, then enter turn loop."""
        # Step 4: Write self_model.json.
        self._self_model_writer.write()

        # Step 5: Initialize working memory (no-op if absent — TurnStateStore handles it).

        # Step 6: Connect to Chroma (graceful fallback to NoOp).
        memory_querier = self._connect_memory()

        # Step 7: Read initial stress scalar (graceful fallback — read-only, agent doesn't block).
        # Stress state is managed by pain_monitor; agent reads it passively if needed.

        # Step 8: Write STARTUP event.
        elapsed = time.monotonic() - self._start_time
        self._event_log.write_event(
            "STARTUP",
            0,
            "agent",
            {
                "bootstrap_duration_seconds": elapsed,
                "config_hash": self._compute_config_hash(),
                "model_name": self._config.model.name,
                # [ASSUMED: 1 — UniverseConfig has no generation field in IS-1; Phase 1 always generation 1]
                "instance_generation": 1,
            },
        )

        # Step 9: Enter turn loop.
        engine = self._build_turn_engine(memory_querier)
        engine.run()

    def _connect_memory(self) -> MemoryQuerier:
        """Try to connect to Chroma; fall back to NoOp on failure."""
        try:
            import chromadb

            client: Any = chromadb.HttpClient(host="chroma", port=8000)
            client.get_or_create_collection("episodic")
            _log.info("Connected to Chroma episodic memory.")
            return ChromaMemoryQuerier(client, self._config)
        except Exception as exc:
            _log.warning("Chroma unavailable (%s), using NoOpMemoryQuerier", exc)
            return NoOpMemoryQuerier()

    def _build_turn_engine(self, memory_querier: MemoryQuerier) -> TurnEngine:
        return TurnEngine(
            config=self._config,
            event_log=self._event_log,
            pain_drain=self._delivery_queue,
            death_reader=self._death_reader,
            model_client=self._model_client,
            mcp_gateway=self._mcp_gateway,
            compliance_client=self._compliance_client,
            memory_querier=memory_querier,
            block_assembler=self._block_assembler,
            turn_state=self._turn_state,
            self_prompt_gen=self._self_prompt_gen,
            user_input_provider=StdinUserInputProvider(),
            pain_submitter=self._pain_submitter,
            fitness_scorer=self._fitness_scorer,
        )

    def _compute_config_hash(self) -> str:
        data = self._config_path.read_bytes()
        return hashlib.sha256(data).hexdigest()
