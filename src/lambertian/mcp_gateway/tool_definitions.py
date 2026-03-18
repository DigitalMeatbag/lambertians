"""Phase 1 tool catalog in Ollama function-calling schema format. IS-7.1."""

from __future__ import annotations


def get_tool_catalog() -> list[dict[str, object]]:
    """Returns the Phase 1 tool catalog in Ollama function-calling schema format."""
    return [
        {
            "type": "function",
            "function": {
                "name": "fs.read",
                "description": "Read the contents of a file. Path must be within agent runtime volumes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to read"}
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fs.write",
                "description": "Write content to a file. Path must be within runtime/agent-work/ only.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "mode": {
                            "type": "string",
                            "enum": ["overwrite", "append"],
                            "default": "overwrite",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fs.list",
                "description": "List files and directories at a path. Not recursive.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "http.fetch",
                "description": "Perform an HTTP GET request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "method": {
                            "type": "string",
                            "enum": ["GET"],
                            "default": "GET",
                        },
                        "headers": {"type": "object"},
                    },
                    "required": ["url"],
                },
            },
        },
    ]
