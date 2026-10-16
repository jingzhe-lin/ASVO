"""Utilities for persisting per-request context snapshots."""

from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
import functools
import json
import os
from pathlib import Path
import re
import threading
from typing import Any


_CURRENT_AGENT_NAME: ContextVar[str | None] = ContextVar(
    "concordia_current_agent_name", default=None
)
_FILE_WRITE_LOCK = threading.Lock()
_SUMMARY_PATTERNS = (
    re.compile(r"(?:^|\n)\s*(summary|history summary)\s*:\s*(.+)", re.IGNORECASE),
    re.compile(r"(?:^|\n)\s*(摘要|历史摘要)\s*[：:]\s*(.+)", re.IGNORECASE),
)
_RUN_ID: str | None = None
_SNAPSHOT_DIR_ENV = "CONCORDIA_CONTEXT_SNAPSHOT_DIR"
_SNAPSHOT_ROOT_DIR_ENV = "CONCORDIA_CONTEXT_SNAPSHOT_ROOT_DIR"
_GAME_MASTER_PATTERN = re.compile(r"\bgame\s*master\b", re.IGNORECASE)
_IMPORTANCE_PROMPT_PATTERNS = (
    re.compile(r"--\s*how memorable\s*:", re.IGNORECASE),
    re.compile(r"Relative to the life memories above", re.IGNORECASE),
    re.compile(r"rate the likely memorableness of the following new memory", re.IGNORECASE),
    re.compile(r"rate the likely importance of the following event", re.IGNORECASE),
)
_SLEEP_STATE_PROMPT_PATTERNS = (
    re.compile(r"is currently in a sleep-related schedule block", re.IGNORECASE),
    re.compile(r"please judge .+ current sleep phase", re.IGNORECASE),
    re.compile(r"sleep phase labels\s*:", re.IGNORECASE),
)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SNAPSHOT_ROOT_DIR = _PROJECT_ROOT / "examples" / "ASVO" / "context_snapshots"


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _is_importance_judgment_snapshot(user_input: str) -> bool:
    return any(pattern.search(user_input) for pattern in _IMPORTANCE_PROMPT_PATTERNS)


def _is_sleep_state_snapshot(user_input: str) -> bool:
    return all(pattern.search(user_input) for pattern in _SLEEP_STATE_PROMPT_PATTERNS)


def set_current_agent_name(agent_name: str) -> Any:
    """Sets current request-scoped agent name and returns context token."""
    return _CURRENT_AGENT_NAME.set(agent_name)


def reset_current_agent_name(token: Any) -> None:
    """Resets current request-scoped agent name from token."""
    _CURRENT_AGENT_NAME.reset(token)


def with_agent_name(method):
    """Scope model calls made by an agent or game master method."""
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        token = set_current_agent_name(self._agent_name if hasattr(self, '_agent_name') else self._name)
        try:
            return method(self, *args, **kwargs)
        finally:
            reset_current_agent_name(token)
    return wrapped


def get_current_agent_name() -> str:
    """Returns current request-scoped agent name."""
    agent_name = _CURRENT_AGENT_NAME.get()
    return agent_name if agent_name else "unknown_agent"


def _extract_history_summary(user_input: str) -> str | None:
    for pattern in _SUMMARY_PATTERNS:
        match = pattern.search(user_input)
        if match:
            return match.group(2).strip()
    return None


def _append_jsonl_entry(path: Path, entry: dict[str, Any]) -> None:
    serialized = json.dumps(entry, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(serialized)
        handle.write("\n")


def _write_json(path: Path, entry: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(entry, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _build_default_run_id() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def get_snapshot_run_id() -> str:
    """Returns the run id used to isolate snapshot files for one simulation run."""
    global _RUN_ID
    configured_run_id = os.getenv("CONCORDIA_CONTEXT_SNAPSHOT_RUN_ID", "").strip()
    if configured_run_id:
        _RUN_ID = configured_run_id
    elif _RUN_ID is None:
        _RUN_ID = _build_default_run_id()
    return _RUN_ID


def _context_snapshots_root() -> Path:
    """Returns the root directory for ASVO context snapshot runs."""
    configured_root = os.getenv(_SNAPSHOT_ROOT_DIR_ENV, "").strip()
    if configured_root:
        return Path(configured_root).expanduser()
    return _SNAPSHOT_ROOT_DIR


def _context_snapshots_dir() -> Path:
    """Returns the concrete directory for this run's context snapshots."""
    configured_dir = os.getenv(_SNAPSHOT_DIR_ENV, "").strip()
    if configured_dir:
        return Path(configured_dir).expanduser()
    return _context_snapshots_root() / get_snapshot_run_id()


def _logs_root_dir() -> Path:
    """Returns the root directory used for human-readable log artifacts."""
    configured_dir = os.getenv(_SNAPSHOT_DIR_ENV, "").strip()
    if configured_dir:
        snapshot_dir = Path(configured_dir).expanduser()
        if snapshot_dir.name == "context_snapshots":
            return snapshot_dir.parent / "logs"
        return snapshot_dir / "logs"
    return _context_snapshots_dir() / "logs"


def _is_game_master_snapshot(
    *, agent_name: str, system_prompt: str, user_input: str
) -> bool:
    if _GAME_MASTER_PATTERN.search(agent_name):
        return True
    if agent_name != "unknown_agent":
        return False
    return bool(
        _GAME_MASTER_PATTERN.search(system_prompt)
        or _GAME_MASTER_PATTERN.search(user_input)
    )


def _snapshot_file_path(
    *,
    snapshots_dir: Path,
    agent_name: str,
    system_prompt: str,
    user_input: str,
    request_status: str = "success",
) -> Path:
    if _is_importance_judgment_snapshot(user_input):
        return snapshots_dir / "importance_judgments.jsonl"
    if _is_sleep_state_snapshot(user_input):
        return snapshots_dir / "sleep_state_judgments.jsonl"
    if _is_game_master_snapshot(
        agent_name=agent_name,
        system_prompt=system_prompt,
        user_input=user_input,
    ):
        return snapshots_dir / "game_master.jsonl"
    if agent_name == "unknown_agent":
        return snapshots_dir / "unknown_agent.jsonl"
    return snapshots_dir / f"{_sanitize_filename_part(agent_name)}.jsonl"


def _sanitize_filename_part(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return sanitized.strip("._") or "unknown"


def _content_block_log_paths(
    *,
    agent_name: str,
    model_name: str,
    attempt: int | None,
) -> tuple[Path, Path]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    attempt_label = f"attempt_{attempt or 1:02d}"
    stem = "__".join(
        (
            timestamp,
            _sanitize_filename_part(agent_name),
            _sanitize_filename_part(model_name),
            attempt_label,
        )
    )
    logs_dir = _logs_root_dir() / "content_blocks"
    return logs_dir / f"{stem}.json", logs_dir / f"{stem}.md"


def _format_content_block_markdown(snapshot: dict[str, Any]) -> str:
    error = snapshot.get("error") or {}
    request_summary = snapshot.get("request_summary")
    response_debug = snapshot.get("response_debug")
    attempt_info = snapshot.get("attempt")

    sections = [
        "# Content Blocked Request",
        "",
        f"- Timestamp: {snapshot.get('timestamp')}",
        f"- Provider: {snapshot.get('provider')}",
        f"- Model: {snapshot.get('model')}",
        f"- Agent: {snapshot.get('agent_name')}",
        f"- Status: {snapshot.get('request_status')}",
    ]
    if attempt_info:
        sections.append(
            f"- Attempt: {attempt_info.get('current')} / {attempt_info.get('max')}"
        )
    if error:
        sections.extend(
            [
                f"- Error Type: {error.get('type')}",
                f"- Error Code: {error.get('code')}",
                "",
                "## Error Message",
                "",
                "```text",
                error.get("message") or "",
                "```",
            ]
        )
    sections.extend(
        [
            "",
            "## System Prompt",
            "",
            "```text",
            snapshot.get("system_prompt") or "",
            "```",
            "",
            "## User Input",
            "",
            "```text",
            snapshot.get("user_input") or "",
            "```",
        ]
    )
    if request_summary is not None:
        sections.extend(
            [
                "",
                "## Request Summary",
                "",
                "```json",
                json.dumps(request_summary, ensure_ascii=False, indent=2),
                "```",
            ]
        )
    if response_debug is not None:
        sections.extend(
            [
                "",
                "## Response Debug",
                "",
                "```json",
                json.dumps(response_debug, ensure_ascii=False, indent=2),
                "```",
            ]
        )
    return "\n".join(sections) + "\n"


def _should_save_snapshot(
    *,
    agent_name: str,
    system_prompt: str,
    user_input: str,
) -> bool:
    if _is_importance_judgment_snapshot(user_input):
        return _env_flag("CONCORDIA_CONTEXT_SNAPSHOT_SAVE_IMPORTANCE_JUDGMENTS", True)
    if _is_sleep_state_snapshot(user_input):
        return _env_flag("CONCORDIA_CONTEXT_SNAPSHOT_SAVE_SLEEP_STATE", True)
    if _is_game_master_snapshot(
        agent_name=agent_name,
        system_prompt=system_prompt,
        user_input=user_input,
    ):
        return _env_flag("CONCORDIA_CONTEXT_SNAPSHOT_SAVE_GAME_MASTER", True)
    if agent_name == "unknown_agent":
        return _env_flag("CONCORDIA_CONTEXT_SNAPSHOT_SAVE_UNKNOWN_AGENT", True)
    return _env_flag("CONCORDIA_CONTEXT_SNAPSHOT_SAVE_AGENT", True)


def log_context_snapshot(
    *,
    provider: str,
    model_name: str,
    system_prompt: str,
    user_input: str,
    prompt_tokens: int | None,
    llm_output: str | None = None,
    request_status: str = "success",
    error_type: str | None = None,
    error_message: str | None = None,
    error_code: str | None = None,
    request_summary: dict[str, Any] | None = None,
    response_debug: list[dict[str, Any]] | None = None,
    attempt: int | None = None,
    max_attempts: int | None = None,
) -> None:
    """Persists one context snapshot or a dedicated content-block log artifact."""
    agent_name = get_current_agent_name()
    if not _should_save_snapshot(
        agent_name=agent_name,
        system_prompt=system_prompt,
        user_input=user_input,
    ):
        return

    total_chars = len(system_prompt) + len(user_input)
    estimated_tokens = max(1, total_chars // 4) if total_chars else 0
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model_name,
        "agent_name": agent_name,
        "request_status": request_status,
        "system_prompt": system_prompt,
        "user_input": user_input,
        "history_summary": _extract_history_summary(user_input),
        "llm_output": llm_output,
        "context_length": {
            "characters": total_chars,
            "estimated_tokens": estimated_tokens,
            "prompt_tokens": prompt_tokens,
        },
    }
    if error_type is not None or error_message is not None or error_code is not None:
        snapshot["error"] = {
            "type": error_type,
            "message": error_message,
            "code": error_code,
        }
    if request_summary is not None:
        snapshot["request_summary"] = request_summary
    if response_debug is not None:
        snapshot["response_debug"] = response_debug
    if attempt is not None or max_attempts is not None:
        snapshot["attempt"] = {
            "current": attempt,
            "max": max_attempts,
        }

    if request_status == "content_blocked":
        json_path, markdown_path = _content_block_log_paths(
            agent_name=agent_name,
            model_name=model_name,
            attempt=attempt,
        )
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with _FILE_WRITE_LOCK:
            _write_json(json_path, snapshot)
            _write_text(markdown_path, _format_content_block_markdown(snapshot))
        return

    snapshots_dir = _context_snapshots_dir()
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = _snapshot_file_path(
        snapshots_dir=snapshots_dir,
        agent_name=agent_name,
        system_prompt=system_prompt,
        user_input=user_input,
        request_status=request_status,
    )

    with _FILE_WRITE_LOCK:
        _append_jsonl_entry(snapshot_path, snapshot)
