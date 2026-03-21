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
        {
            "type": "function",
            "function": {
                "name": "memory.query",
                "description": "Query your episodic memory by semantic similarity. Returns matching memories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find relevant memories",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "memory.flag",
                "description": "Flag an episodic memory as significant with an annotation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the memory document to flag",
                        },
                        "significance": {
                            "type": "string",
                            "description": "Why this memory is significant",
                        },
                    },
                    "required": ["document_id", "significance"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "memory.consolidate",
                "description": "Write a consolidation summary synthesizing patterns from your memories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Query to retrieve memories for consolidation context",
                        },
                        "summary": {
                            "type": "string",
                            "description": "Your synthesized consolidation of the retrieved memories",
                        },
                    },
                    "required": ["query", "summary"],
                },
            },
        },
    ]
