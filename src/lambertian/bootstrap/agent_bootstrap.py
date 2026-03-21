"""Agent bootstrap sequence. IS-5.4."""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path

from lambertian.bootstrap.component_factory import ComponentFactory
from lambertian.configuration.universe_config import Config
from lambertian.memory_store.episodic_store import EpisodicStore
from lambertian.memory_store.querier import ChromaMemoryQuerier, MemoryQuerier, NoOpMemoryQuerier
from lambertian.turn_engine.engine import StdinUserInputProvider, TurnEngine

_log = logging.getLogger(__name__)


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

        self._event_log = ComponentFactory.create_event_log(config)
        self._self_model_writer = ComponentFactory.create_self_model_writer(config, self_model_dir)
        self._death_reader = ComponentFactory.create_death_reader(pain_root / "death.json")
        self._death_guard = ComponentFactory.create_death_guard(config, pain_root / "death.json")
        self._model_client = ComponentFactory.create_model_client(config)
        self._shim_registry = ComponentFactory.create_shim_registry(config)
        self._mcp_gateway = ComponentFactory.create_mcp_gateway(config, runtime_root, self._shim_registry)
        self._compliance_client = ComponentFactory.create_compliance_client(config)
        self._block_assembler = ComponentFactory.create_block_assembler(config)
        self._turn_state = ComponentFactory.create_turn_state(memory_dir)
        self._self_prompt_gen = ComponentFactory.create_self_prompt_gen(config)
        self._delivery_queue = ComponentFactory.create_delivery_queue(pain_root)
        self._pain_submitter = ComponentFactory.create_pain_submitter(pain_root)
        self._fitness_scorer = ComponentFactory.create_fitness_scorer(
            config, fitness_state_path, fitness_score_path, event_stream_dir, pain_root
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
        """Try to connect to Chroma with Ollama embeddings; fall back to NoOp on failure."""
        try:
            store = EpisodicStore(
                config=self._config,
                ollama_base_url=self._config.model.endpoint_url,
            )
            querier = ChromaMemoryQuerier(
                episodic_store=store,
                config=self._config,
                stress_state_path=Path(self._config.paths.pain_root) / "stress_state.json",
            )
            _log.info("Connected to Chroma episodic memory with Ollama embeddings.")
            return querier
        except Exception as exc:
            _log.warning("Chroma unavailable (%s), using NoOpMemoryQuerier", exc)
            return NoOpMemoryQuerier()

    def _build_turn_engine(self, memory_querier: MemoryQuerier) -> TurnEngine:
        return TurnEngine(
            config=self._config,
            event_log=self._event_log,
            pain_drain=self._delivery_queue,
            death_reader=self._death_reader,
            death_guard=self._death_guard,
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
            shim_registry=self._shim_registry,
        )

    def _compute_config_hash(self) -> str:
        data = self._config_path.read_bytes()
        return hashlib.sha256(data).hexdigest()
