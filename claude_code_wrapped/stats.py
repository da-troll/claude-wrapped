"""Aggregate statistics from Claude Code conversation history for Wrapped."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .reader import Message, TokenUsage


@dataclass
class DailyStats:
    """Statistics for a single day."""
    date: datetime
    message_count: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    tokens: TokenUsage = field(default_factory=TokenUsage)
    tool_calls: Counter = field(default_factory=Counter)
    models_used: Counter = field(default_factory=Counter)
    projects: set = field(default_factory=set)
    session_count: int = 0


@dataclass
class WrappedStats:
    """Complete wrapped statistics for a year."""
    year: int

    # Overall counts
    total_messages: int = 0
    total_user_messages: int = 0
    total_assistant_messages: int = 0
    total_sessions: int = 0
    total_projects: int = 0

    # Token usage
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_creation_tokens: int = 0
    total_cache_read_tokens: int = 0

    # Time patterns
    first_message_date: datetime | None = None
    last_message_date: datetime | None = None
    most_active_day: tuple[datetime, int] | None = None
    most_active_hour: int | None = None
    streak_longest: int = 0
    streak_current: int = 0
    active_days: int = 0

    # Tool usage
    tool_calls: Counter = field(default_factory=Counter)
    top_tools: list[tuple[str, int]] = field(default_factory=list)

    # Model usage
    models_used: Counter = field(default_factory=Counter)
    primary_model: str | None = None

    # Projects
    projects: Counter = field(default_factory=Counter)
    top_projects: list[tuple[str, int]] = field(default_factory=list)

    # Daily breakdown
    daily_stats: dict[str, DailyStats] = field(default_factory=dict)

    # Hour distribution (0-23 -> count)
    hourly_distribution: list[int] = field(default_factory=lambda: [0] * 24)

    # Day of week distribution (0=Monday, 6=Sunday)
    weekday_distribution: list[int] = field(default_factory=lambda: [0] * 7)

    # Fun stats
    longest_conversation_tokens: int = 0
    avg_messages_per_day: float = 0.0
    avg_tokens_per_message: float = 0.0

    @property
    def total_tokens(self) -> int:
        return (
            self.total_input_tokens +
            self.total_output_tokens +
            self.total_cache_creation_tokens +
            self.total_cache_read_tokens
        )


def extract_project_name(project_path: str | None) -> str:
    """Extract a readable project name from a path."""
    if not project_path:
        return "Unknown"
    # Get the last part of the path
    parts = project_path.rstrip('/').split('/')
    return parts[-1] if parts else "Unknown"


def calculate_streaks(daily_stats: dict[str, DailyStats], year: int) -> tuple[int, int]:
    """Calculate longest and current coding streaks."""
    # Get all active dates in the year
    active_dates = set()
    for date_str, stats in daily_stats.items():
        if stats.message_count > 0:
            active_dates.add(datetime.strptime(date_str, "%Y-%m-%d").date())

    if not active_dates:
        return 0, 0

    # Sort dates
    sorted_dates = sorted(active_dates)

    # Calculate longest streak
    longest_streak = 1
    current_streak = 1

    for i in range(1, len(sorted_dates)):
        if sorted_dates[i] - sorted_dates[i-1] == timedelta(days=1):
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 1

    # Calculate current streak (counting back from today or last active day)
    today = datetime.now().date()
    current = 0

    # Start from today or the last day of the year
    check_date = min(today, datetime(year, 12, 31).date())

    while check_date >= datetime(year, 1, 1).date():
        if check_date in active_dates:
            current += 1
            check_date -= timedelta(days=1)
        elif check_date == today:
            # Today doesn't count against streak if we haven't coded yet
            check_date -= timedelta(days=1)
        else:
            break

    return longest_streak, current


def aggregate_stats(messages: list[Message], year: int) -> WrappedStats:
    """Aggregate all messages into wrapped statistics."""
    stats = WrappedStats(year=year)

    if not messages:
        return stats

    # Track unique sessions and projects
    sessions = set()
    projects = Counter()
    daily = defaultdict(lambda: DailyStats(date=datetime.now()))

    # Process each message
    for msg in messages:
        stats.total_messages += 1

        if msg.role == 'user':
            stats.total_user_messages += 1
        else:
            stats.total_assistant_messages += 1

        # Session tracking
        if msg.session_id:
            sessions.add(msg.session_id)

        # Project tracking
        project_name = extract_project_name(msg.project)
        if project_name != "Unknown":
            projects[project_name] += 1

        # Token usage
        if msg.usage:
            stats.total_input_tokens += msg.usage.input_tokens
            stats.total_output_tokens += msg.usage.output_tokens
            stats.total_cache_creation_tokens += msg.usage.cache_creation_tokens
            stats.total_cache_read_tokens += msg.usage.cache_read_tokens

        # Tool usage
        for tool in msg.tool_calls:
            stats.tool_calls[tool] += 1

        # Model usage
        if msg.model:
            # Simplify model name
            model_name = msg.model
            if 'opus' in model_name.lower():
                model_name = 'Opus'
            elif 'sonnet' in model_name.lower():
                model_name = 'Sonnet'
            elif 'haiku' in model_name.lower():
                model_name = 'Haiku'
            stats.models_used[model_name] += 1

        # Time-based stats
        if msg.timestamp:
            # Track first and last
            if stats.first_message_date is None or msg.timestamp < stats.first_message_date:
                stats.first_message_date = msg.timestamp
            if stats.last_message_date is None or msg.timestamp > stats.last_message_date:
                stats.last_message_date = msg.timestamp

            # Hourly distribution
            stats.hourly_distribution[msg.timestamp.hour] += 1

            # Weekday distribution
            stats.weekday_distribution[msg.timestamp.weekday()] += 1

            # Daily stats
            date_str = msg.timestamp.strftime("%Y-%m-%d")
            if date_str not in daily:
                daily[date_str] = DailyStats(date=msg.timestamp)

            daily_stat = daily[date_str]
            daily_stat.message_count += 1
            if msg.role == 'user':
                daily_stat.user_messages += 1
            else:
                daily_stat.assistant_messages += 1

    # Finalize stats
    stats.total_sessions = len(sessions)
    stats.projects = projects
    stats.total_projects = len(projects)
    stats.daily_stats = dict(daily)
    stats.active_days = len([d for d in daily.values() if d.message_count > 0])

    # Most active day
    if daily:
        most_active = max(daily.items(), key=lambda x: x[1].message_count)
        stats.most_active_day = (
            datetime.strptime(most_active[0], "%Y-%m-%d"),
            most_active[1].message_count
        )

    # Most active hour
    if any(stats.hourly_distribution):
        stats.most_active_hour = stats.hourly_distribution.index(max(stats.hourly_distribution))

    # Top tools
    stats.top_tools = stats.tool_calls.most_common(10)

    # Top projects
    stats.top_projects = projects.most_common(5)

    # Primary model
    if stats.models_used:
        stats.primary_model = stats.models_used.most_common(1)[0][0]

    # Streaks
    stats.streak_longest, stats.streak_current = calculate_streaks(daily, year)

    # Averages
    if stats.active_days > 0:
        stats.avg_messages_per_day = stats.total_messages / stats.active_days

    if stats.total_assistant_messages > 0:
        stats.avg_tokens_per_message = stats.total_tokens / stats.total_assistant_messages

    return stats


def format_tokens(tokens: int) -> str:
    """Format token count for display."""
    if tokens >= 1_000_000_000:
        return f"{tokens / 1_000_000_000:.1f}B"
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    if tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)


if __name__ == "__main__":
    from .reader import load_all_messages, get_claude_dir

    print("Loading messages...")
    messages = load_all_messages(year=2025)
    print(f"Loaded {len(messages)} messages")

    print("\nCalculating stats...")
    stats = aggregate_stats(messages, 2025)

    print(f"\n=== Claude Code Wrapped 2025 ===")
    print(f"Total messages: {stats.total_messages:,}")
    print(f"  User: {stats.total_user_messages:,}")
    print(f"  Assistant: {stats.total_assistant_messages:,}")
    print(f"Total sessions: {stats.total_sessions}")
    print(f"Total projects: {stats.total_projects}")
    print(f"Active days: {stats.active_days}")
    print(f"\nTokens: {format_tokens(stats.total_tokens)}")
    print(f"  Input: {format_tokens(stats.total_input_tokens)}")
    print(f"  Output: {format_tokens(stats.total_output_tokens)}")
    print(f"  Cache created: {format_tokens(stats.total_cache_creation_tokens)}")
    print(f"  Cache read: {format_tokens(stats.total_cache_read_tokens)}")
    print(f"\nPrimary model: {stats.primary_model}")
    print(f"Longest streak: {stats.streak_longest} days")
    print(f"Most active hour: {stats.most_active_hour}:00")
    if stats.most_active_day:
        print(f"Most active day: {stats.most_active_day[0].strftime('%B %d')} ({stats.most_active_day[1]} messages)")
    print(f"\nTop tools: {stats.top_tools[:5]}")
    print(f"Top projects: {stats.top_projects}")
