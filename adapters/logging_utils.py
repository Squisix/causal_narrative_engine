"""
adapters/logging_utils.py - Logging utilities for AI interactions

Saves prompts, responses, and errors to JSONL files partitioned by world_id.
"""

import os
import json
from datetime import datetime, timezone
from typing import Any


def log_ai_interaction(
    world_id: str,
    adapter_name: str,
    system_prompt: str,
    user_prompt: str,
    raw_response: Any,
    success: bool,
    error_msg: str | None = None,
) -> None:
    """
    Logs an AI adapter interaction to a JSONL file per world.

    The log directory is 'logs/' at the project root.
    Files are named 'world_<world_id>.jsonl'.
    """
    # Check if logging is enabled via environment variable
    enabled = os.getenv("ENABLE_AI_LOGGING", "true").lower() in ("true", "1", "yes")
    if not enabled:
        return

    # Root folder is the parent of 'adapters'
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_dir = os.path.join(root_dir, "logs")
    
    try:
        os.makedirs(logs_dir, exist_ok=True)
    except Exception as e:
        print(f"[ERROR] Failed to create logs directory '{logs_dir}': {e}")
        # Fallback to current working directory 'logs'
        logs_dir = "logs"
        os.makedirs(logs_dir, exist_ok=True)

    file_path = os.path.join(logs_dir, f"world_{world_id}.jsonl")

    # Parse JSON if raw_response is a string containing JSON
    response_data = raw_response
    if isinstance(raw_response, str):
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        try:
            response_data = json.loads(cleaned)
        except Exception:
            response_data = raw_response

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "adapter": adapter_name,
        "success": success,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "raw_response": response_data,
        "error": error_msg,
    }

    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[ERROR] Failed to write AI interaction log to '{file_path}': {e}")
