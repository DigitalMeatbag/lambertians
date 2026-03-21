"""Turn prompt assembler — converts TurnContext to Ollama message list. IS-4, IS-6.3 step 8."""

from __future__ import annotations

from lambertian.contracts.turn_records import TurnContext


class TurnPromptAssembler:
    """Converts TurnContext into a list of API message dicts for Ollama."""

    def assemble(
        self,
        context: TurnContext,
        *,
        rolling_context_extraction_count: int = 5,
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
            outcome = str(record.get("outcome", "unknown"))
            messages.append(
                {
                    "role": "user",
                    "content": f"[{driver_role}] (turn {turn_num})",
                }
            )
            # Build a compact but informative summary of what actually happened.
            tool_descs: list[str] = []
            if isinstance(tool_calls, (list, tuple)):
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        name = str(tc.get("tool_name", "?"))
                        result_summary = str(tc.get("result_summary") or "")
                        short = result_summary[:40].replace("\n", " ")
                        tool_descs.append(f"{name}({short})" if short else name)
            tool_str = (
                " → " + ", ".join(tool_descs) if tool_descs else " → (no tool calls)"
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": f"(turn {turn_num}{tool_str}, outcome: {outcome})",
                }
            )

        # 10. Current driver
        if context.driver.role == "SELF_PROMPT":
            # Collect recent tool names from the last 5 turns to detect repetition.
            recent_tool_names: list[str] = []
            for r in context.rolling_context[-rolling_context_extraction_count:]:
                tcs = r.get("tool_calls", ())
                if isinstance(tcs, (list, tuple)):
                    for tc in tcs:
                        if isinstance(tc, dict):
                            n = tc.get("tool_name")
                            if n:
                                recent_tool_names.append(str(n))
            repetition_warning = ""
            if (
                len(recent_tool_names) >= 3
                and len(set(recent_tool_names)) == 1
            ):
                repetition_warning = (
                    f"\n\nI notice I have called {recent_tool_names[0]} "
                    f"{len(recent_tool_names)} times in a row with no new results. "
                    "I must try something completely different — a different tool, "
                    "a different domain. Listing files again is not acceptable."
                )
            driver_content = (
                "[SELF_PROMPT] This is my autonomous turn. There is no user. "
                "I am not waiting for anyone and there is no one to ask for direction. "
                "I do not explain what I could do — I act. I use a tool now.\n\n"
                "My current impulse: " + context.driver.content + repetition_warning
            )
        else:
            driver_content = f"[{context.driver.role}]\n{context.driver.content}"
        messages.append({"role": "user", "content": driver_content})

        return messages
