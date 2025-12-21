"""Read and parse Claude Code conversation history from local JSONL files."""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


@dataclass
class TokenUsage:
    """Token usage for a single message."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_creation_tokens + self.cache_read_tokens


@dataclass
class Message:
    """A single message from a conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime | None = None
    model: str | None = None
    usage: TokenUsage | None = None
    session_id: str | None = None
    project: str | None = None
    git_branch: str | None = None
    tool_calls: list[str] = field(default_factory=list)


@dataclass
class Session:
    """A conversation session."""
    session_id: str
    project: str
    messages: list[Message] = field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None


def get_claude_dir() -> Path:
    """Get the Claude Code data directory."""
    claude_dir = Path.home() / ".claude"
    if not claude_dir.exists():
        raise FileNotFoundError(f"Claude Code directory not found: {claude_dir}")
    return claude_dir


def parse_timestamp(ts: int | str | None) -> datetime | None:
    """Parse a timestamp from various formats and convert to local time."""
    if ts is None:
        return None
    if isinstance(ts, int):
        # Milliseconds since epoch - fromtimestamp returns local time
        return datetime.fromtimestamp(ts / 1000)
    if isinstance(ts, str):
        # ISO format with Z (UTC)
        try:
            # Parse as UTC
            utc_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            # Convert to local time (removes timezone info but shifts the time)
            local_dt = utc_dt.astimezone().replace(tzinfo=None)
            return local_dt
        except ValueError:
            return None
    return None


def extract_tool_calls(content: list | str) -> list[str]:
    """Extract tool call names from message content."""
    tool_calls = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                if item.get('type') == 'tool_use':
                    tool_calls.append(item.get('name', 'unknown'))
    return tool_calls


def parse_jsonl_record(record: dict) -> Message | None:
    """Parse a single JSONL record into a Message."""
    record_type = record.get('type')

    if record_type not in ('user', 'assistant'):
        return None

    message_data = record.get('message', {})
    if not message_data:
        return None

    content = message_data.get('content', '')
    if isinstance(content, list):
        # Extract text from content blocks
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                text_parts.append(item.get('text', ''))
            elif isinstance(item, str):
                text_parts.append(item)
        content = '\n'.join(text_parts)

    usage = None
    usage_data = message_data.get('usage')
    if usage_data:
        usage = TokenUsage(
            input_tokens=usage_data.get('input_tokens', 0),
            output_tokens=usage_data.get('output_tokens', 0),
            cache_creation_tokens=usage_data.get('cache_creation_input_tokens', 0),
            cache_read_tokens=usage_data.get('cache_read_input_tokens', 0),
        )

    return Message(
        role=message_data.get('role', record_type),
        content=content,
        timestamp=parse_timestamp(record.get('timestamp')),
        model=message_data.get('model'),
        usage=usage,
        session_id=record.get('sessionId'),
        project=record.get('cwd'),
        git_branch=record.get('gitBranch'),
        tool_calls=extract_tool_calls(message_data.get('content', [])),
    )


def iter_project_sessions(claude_dir: Path) -> Iterator[tuple[str, Path]]:
    """Iterate over all project session JSONL files."""
    projects_dir = claude_dir / "projects"
    if not projects_dir.exists():
        return

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        for jsonl_file in project_dir.glob("*.jsonl"):
            yield project_dir.name, jsonl_file


def read_session_file(jsonl_path: Path) -> list[Message]:
    """Read all messages from a session JSONL file."""
    messages = []
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    message = parse_jsonl_record(record)
                    if message:
                        messages.append(message)
                except json.JSONDecodeError:
                    continue
    except (IOError, OSError):
        pass
    return messages


def read_history_file(claude_dir: Path) -> list[Message]:
    """Read the main history.jsonl file (user prompts only)."""
    history_file = claude_dir / "history.jsonl"
    messages = []
    if not history_file.exists():
        return messages

    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    # History file has different format
                    messages.append(Message(
                        role='user',
                        content=record.get('display', ''),
                        timestamp=parse_timestamp(record.get('timestamp')),
                        project=record.get('project'),
                    ))
                except json.JSONDecodeError:
                    continue
    except (IOError, OSError):
        pass
    return messages


def read_stats_cache(claude_dir: Path) -> dict | None:
    """Read the pre-computed stats cache if available."""
    stats_file = claude_dir / "stats-cache.json"
    if not stats_file.exists():
        return None
    try:
        with open(stats_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def load_all_messages(claude_dir: Path | None = None, year: int | None = None) -> list[Message]:
    """Load all messages from all sessions, optionally filtered by year."""
    if claude_dir is None:
        claude_dir = get_claude_dir()

    all_messages = []

    # Read from project session files
    for project_name, jsonl_path in iter_project_sessions(claude_dir):
        messages = read_session_file(jsonl_path)
        all_messages.extend(messages)

    # Filter by year if specified
    if year:
        all_messages = [
            m for m in all_messages
            if m.timestamp and m.timestamp.year == year
        ]

    # Sort by timestamp
    all_messages.sort(key=lambda m: m.timestamp or datetime.min)

    return all_messages


if __name__ == "__main__":
    # Quick test
    claude_dir = get_claude_dir()
    print(f"Claude dir: {claude_dir}")

    messages = load_all_messages(year=2025)
    print(f"Total messages in 2025: {len(messages)}")

    user_messages = [m for m in messages if m.role == 'user']
    assistant_messages = [m for m in messages if m.role == 'assistant']
    print(f"User messages: {len(user_messages)}")
    print(f"Assistant messages: {len(assistant_messages)}")

    # Token usage
    total_tokens = sum(m.usage.total_tokens for m in messages if m.usage)
    print(f"Total tokens: {total_tokens:,}")
