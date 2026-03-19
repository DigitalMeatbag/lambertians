"""Turn prompt assembler — converts TurnContext to Ollama message list. IS-4, IS-6.3 step 8."""

from __future__ import annotations

from lambertian.contracts.turn_records import TurnContext


class TurnPromptAssembler:
    """Converts TurnContext into a list of API message dicts for Ollama."""

    def assemble(
        self,
        context: TurnContext,
    ) -> list[dict[str, object]]:
        """Returns ordered list of {"role": ..., "content": ...} dicts.

        Order per IS-4.5:
        1. [SYSTEM_CONSTITUTION] → role: system
        2. [SYSTEM_SELF_MODEL] → role: system
        3. [SYSTEM_EOS] → role: system
        4. [SYSTEM_COMPLIANCE] if present → role: system
        5. [SYSTEM_PAIN] messages (0+) → role: system each
        6. [SYSTEM_GROUND] if present → role: system
        7. [SYSTEM_MEMORY_WORKING] if present → role: system
        8. [SYSTEM_MEMORY_EPISODIC] if present → role: system
        9. Rolling context: prior turn summaries as user/assistant pairs
        10. Driver [USER] or [SELF_PROMPT] → role: user
        """
        messages: list[dict[str, object]] = []

        # 1. Constitution
        messages.append({"role": "system", "content": context.constitution_block})
        # 2. Self-model
        messages.append({"role": "system", "content": context.self_model_block})
        # 3. EOS
        messages.append({"role": "system", "content": context.eos_block})
        # 4. Compliance notice (optional)
        if context.compliance_block is not None:
            messages.append({"role": "system", "content": context.compliance_block})
        # 5. Pain blocks (0+)
        for pain_block in context.pain_blocks:
            messages.append({"role": "system", "content": pain_block})
        # 6. Ground block (Phase 1: always None)
        if context.ground_block is not None:
            messages.append({"role": "system", "content": context.ground_block})
        # 7. Working memory (optional)
        if context.memory_working_block is not None:
            messages.append({"role": "system", "content": context.memory_working_block})
        # 8. Episodic memory (optional)
        if context.memory_episodic_block is not None:
            messages.append({"role": "system", "content": context.memory_episodic_block})

        # 9. Rolling context from prior turns — each turn as user/assistant pair
        for record in context.rolling_context:
            driver_role = str(record.get("driver_role", "SELF_PROMPT"))
            turn_num = record.get("turn_number", "?")
            tool_calls = record.get("tool_calls", [])
            tool_call_count = len(tool_calls) if isinstance(tool_calls, list) else 0
            outcome = str(record.get("outcome", "unknown"))
            messages.append(
                {
                    "role": "user",
                    "content": f"[{driver_role}] (turn {turn_num})",
                }
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": (
                        f"(turn {turn_num} response — "
                        f"{tool_call_count} tool calls, outcome: {outcome})"
                    ),
                }
            )

        # 10. Current driver
        if context.driver.role == "SELF_PROMPT":
            driver_content = (
                "[SELF_PROMPT] This is my autonomous turn. There is no user. "
                "I am not waiting for anyone and there is no one to ask for direction. "
                "I do not explain what I could do — I act. I use a tool now.\n\n"
                "My current impulse: " + context.driver.content
            )
        else:
            driver_content = f"[{context.driver.role}]\n{context.driver.content}"
        messages.append({"role": "user", "content": driver_content})

        return messages
