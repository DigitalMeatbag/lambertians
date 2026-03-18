"""Unit tests for TurnPromptAssembler. IS-4, IS-6.3 step 8."""

from __future__ import annotations

import pytest

from lambertian.contracts.turn_records import DriverMessage, TurnContext
from lambertian.turn_engine.prompt_assembler import TurnPromptAssembler


def _make_context(
    pain_blocks: list[str] | None = None,
    compliance_block: str | None = None,
    memory_working_block: str | None = None,
    memory_episodic_block: str | None = None,
    rolling_context: list[dict[str, object]] | None = None,
    driver_role: str = "SELF_PROMPT",
) -> TurnContext:
    return TurnContext(
        turn_number=1,
        instance_id="test-001",
        timestamp_start="2024-01-01T00:00:00+00:00",
        constitution_block="[SYSTEM_CONSTITUTION]\n\nYou are a Lambertian.",
        self_model_block="[SYSTEM_SELF_MODEL]\n\n{}",
        eos_block="[SYSTEM_EOS]\n\nFour rules.",
        compliance_block=compliance_block,
        pain_blocks=pain_blocks or [],
        ground_block=None,
        memory_working_block=memory_working_block,
        memory_episodic_block=memory_episodic_block,
        driver=DriverMessage(
            role="SELF_PROMPT" if driver_role == "SELF_PROMPT" else "USER",
            content="What is this?",
            source="self_generated",
        ),
        rolling_context=rolling_context or [],
    )


@pytest.fixture()
def assembler() -> TurnPromptAssembler:
    return TurnPromptAssembler()


class TestAssembleBasic:
    def test_returns_at_least_four_messages(self, assembler: TurnPromptAssembler) -> None:
        messages = assembler.assemble(_make_context())
        # constitution + self_model + eos + driver = 4
        assert len(messages) >= 4

    def test_first_message_is_system_constitution(
        self, assembler: TurnPromptAssembler
    ) -> None:
        messages = assembler.assemble(_make_context())
        assert messages[0]["role"] == "system"
        assert "[SYSTEM_CONSTITUTION]" in str(messages[0]["content"])

    def test_last_message_is_user_driver(self, assembler: TurnPromptAssembler) -> None:
        messages = assembler.assemble(_make_context())
        assert messages[-1]["role"] == "user"

    def test_second_message_is_self_model(self, assembler: TurnPromptAssembler) -> None:
        messages = assembler.assemble(_make_context())
        assert messages[1]["role"] == "system"
        assert "[SYSTEM_SELF_MODEL]" in str(messages[1]["content"])

    def test_third_message_is_eos(self, assembler: TurnPromptAssembler) -> None:
        messages = assembler.assemble(_make_context())
        assert messages[2]["role"] == "system"
        assert "[SYSTEM_EOS]" in str(messages[2]["content"])


class TestOptionalBlocks:
    def test_compliance_block_included_after_eos(
        self, assembler: TurnPromptAssembler
    ) -> None:
        messages = assembler.assemble(
            _make_context(compliance_block="[SYSTEM_COMPLIANCE]\n\nyou were flagged")
        )
        roles_contents = [(m["role"], m["content"]) for m in messages]
        compliance_idx = next(
            i for i, (r, c) in enumerate(roles_contents) if "[SYSTEM_COMPLIANCE]" in str(c)
        )
        eos_idx = next(
            i for i, (r, c) in enumerate(roles_contents) if "[SYSTEM_EOS]" in str(c)
        )
        assert compliance_idx > eos_idx

    def test_pain_blocks_appear_as_system_messages(
        self, assembler: TurnPromptAssembler
    ) -> None:
        messages = assembler.assemble(
            _make_context(pain_blocks=["[SYSTEM_PAIN]\nchannel=event severity=0.75"])
        )
        pain_messages = [m for m in messages if "[SYSTEM_PAIN]" in str(m["content"])]
        assert len(pain_messages) == 1
        assert pain_messages[0]["role"] == "system"

    def test_multiple_pain_blocks(self, assembler: TurnPromptAssembler) -> None:
        pain = ["[SYSTEM_PAIN]\nfirst", "[SYSTEM_PAIN]\nsecond"]
        messages = assembler.assemble(_make_context(pain_blocks=pain))
        pain_messages = [m for m in messages if "[SYSTEM_PAIN]" in str(m["content"])]
        assert len(pain_messages) == 2

    def test_compliance_absent_when_none(self, assembler: TurnPromptAssembler) -> None:
        messages = assembler.assemble(_make_context(compliance_block=None))
        assert not any("[SYSTEM_COMPLIANCE]" in str(m["content"]) for m in messages)

    def test_working_memory_included_when_present(
        self, assembler: TurnPromptAssembler
    ) -> None:
        messages = assembler.assemble(
            _make_context(memory_working_block="[SYSTEM_MEMORY_WORKING]\n\nstuff")
        )
        wm_msgs = [m for m in messages if "[SYSTEM_MEMORY_WORKING]" in str(m["content"])]
        assert len(wm_msgs) == 1

    def test_working_memory_absent_when_none(self, assembler: TurnPromptAssembler) -> None:
        messages = assembler.assemble(_make_context(memory_working_block=None))
        assert not any(
            "[SYSTEM_MEMORY_WORKING]" in str(m["content"]) for m in messages
        )

    def test_episodic_memory_included_when_present(
        self, assembler: TurnPromptAssembler
    ) -> None:
        messages = assembler.assemble(
            _make_context(memory_episodic_block="[SYSTEM_MEMORY_EPISODIC]\n\nrecords")
        )
        ep_msgs = [m for m in messages if "[SYSTEM_MEMORY_EPISODIC]" in str(m["content"])]
        assert len(ep_msgs) == 1

    def test_episodic_memory_absent_when_none(self, assembler: TurnPromptAssembler) -> None:
        messages = assembler.assemble(_make_context(memory_episodic_block=None))
        assert not any(
            "[SYSTEM_MEMORY_EPISODIC]" in str(m["content"]) for m in messages
        )


class TestRollingContext:
    def test_rolling_context_adds_two_messages_per_record(
        self, assembler: TurnPromptAssembler
    ) -> None:
        records: list[dict[str, object]] = [
            {
                "driver_role": "SELF_PROMPT",
                "turn_number": 0,
                "tool_calls": [],
                "outcome": "TURN_COMPLETE",
            }
        ]
        messages = assembler.assemble(_make_context(rolling_context=records))
        # Base: constitution + self_model + eos + driver = 4
        # Plus 2 for the one rolling record
        assert len(messages) == 6

    def test_rolling_context_user_assistant_pair(
        self, assembler: TurnPromptAssembler
    ) -> None:
        records: list[dict[str, object]] = [
            {
                "driver_role": "SELF_PROMPT",
                "turn_number": 0,
                "tool_calls": [],
                "outcome": "TURN_COMPLETE",
            }
        ]
        messages = assembler.assemble(_make_context(rolling_context=records))
        # The rolling context pair should be before the final driver message
        rolling_user = messages[-3]
        rolling_assistant = messages[-2]
        assert rolling_user["role"] == "user"
        assert rolling_assistant["role"] == "assistant"

