"""Rich-based terminal UI for Claude Code Wrapped."""

import sys
import time
from datetime import datetime, timedelta

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.style import Style
from rich.table import Table
from rich.text import Text

from .stats import WrappedStats, format_tokens

# Minimal color palette
COLORS = {
    "orange": "#C96442",
    "purple": "#9B59B6",
    "blue": "#3498DB",
    "green": "#27AE60",
    "yellow": "#F1C40F",
    "white": "#ECF0F1",
    "gray": "#7F8C8D",
    "dark": "#2C3E50",
}

# GitHub-style contribution colors (no activity = visible gray, then greens)
CONTRIB_COLORS = ["#3a3a3a", "#0E4429", "#006D32", "#26A641", "#39D353"]


def wait_for_keypress():
    """Wait for user to press Enter."""
    input()
    return '\n'


# === ANIMATION UTILITIES ===

def animate_count_up(console: Console, target: int, duration: float = 1.2, suffix: str = "",
                     color: str = COLORS["orange"], bold: bool = True, centered: bool = True):
    """Animate a number counting up from 0 to target value."""
    steps = min(30, target) if target > 0 else 1
    step_duration = duration / steps

    with Live(console=console, refresh_per_second=60, transient=True) as live:
        for i in range(steps + 1):
            current = int((i / steps) * target)
            text = Text()
            text.append(f"{current:,}{suffix}", style=Style(color=color, bold=bold))

            if centered:
                live.update(Align.center(text))
            else:
                live.update(text)
            time.sleep(step_duration)

    # Final value (permanent)
    final = Text()
    final.append(f"{target:,}{suffix}", style=Style(color=color, bold=bold))
    if centered:
        console.print(Align.center(final))
    else:
        console.print(final)


def animate_typing(console: Console, text: str, color: str = COLORS["white"],
                   delay: float = 0.03, bold: bool = False, centered: bool = True):
    """Display text with a brief pause (simpler, no character-by-character for regular text)."""
    # Just display the text with a small dramatic pause
    dramatic_pause(delay * len(text) * 0.3)  # Shorter total time
    styled = Text(text, style=Style(color=color, bold=bold))
    if centered:
        console.print(Align.center(styled))
    else:
        console.print(styled)


def animate_lines(console: Console, lines: list[tuple[str, str]], delay: float = 0.08):
    """Reveal lines one at a time with a fade-in effect.

    Args:
        lines: List of (text, style) tuples
        delay: Delay between lines
    """
    for line_text, style in lines:
        console.print(line_text, style=style)
        time.sleep(delay)


def animate_ascii_art(console: Console, art_lines: list[str], color: str = COLORS["orange"],
                      delay: float = 0.05, centered: bool = True):
    """Animate ASCII art appearing line by line."""
    for line in art_lines:
        styled = Text(line, style=Style(color=color))
        if centered:
            console.print(Align.center(styled))
        else:
            console.print(styled)
        time.sleep(delay)


def dramatic_pause(duration: float = 0.5):
    """Add a dramatic pause before a reveal."""
    time.sleep(duration)


def animate_stat_reveal(console: Console, value: int | float, label: str, subtitle: str = "",
                        color: str = COLORS["orange"], count_duration: float = 1.0):
    """Animate a dramatic stat reveal with count-up effect."""
    console.print()
    console.print()
    console.print()

    # Animate the number counting up
    if isinstance(value, float):
        # For floats (like cost), format with 2 decimal places
        steps = 30
        step_duration = count_duration / steps
        for i in range(steps + 1):
            current = (i / steps) * value
            text = Text()
            text.append(f"${current:.2f}" if value < 1000 else f"${current:,.0f}",
                       style=Style(color=color, bold=True))
            console.print("\r" + " " * 50, end="\r")
            console.print(Align.center(text), end="\r")
            time.sleep(step_duration)
        final_text = Text()
        final_text.append(f"${value:.2f}" if value < 1000 else f"${value:,.0f}",
                         style=Style(color=color, bold=True))
        console.print("\r" + " " * 50, end="\r")
        console.print(Align.center(final_text))
    else:
        animate_count_up(console, value, duration=count_duration, color=color)

    # Label appears after number
    dramatic_pause(0.2)
    label_text = Text(label, style=Style(color=COLORS["white"], bold=True))
    console.print(Align.center(label_text))

    # Subtitle types out
    if subtitle:
        console.print()
        animate_typing(console, subtitle, color=COLORS["gray"], delay=0.02)


def format_year_display(year: int | None) -> str:
    """Format year for display - returns 'All time' if year is None."""
    return "All time" if year is None else str(year)


def create_dashboard_header(year: int | None, width: int = 80) -> Text:
    """Create the dashboard header bar using specified width."""
    # Build the title text
    title = f"CLAUDE CODE WRAPPED {format_year_display(year)}"
    # Center the title within the width
    padding = (width - len(title)) // 2

    header = Text()
    header.append("═" * width + "\n", style=Style(color=COLORS["orange"]))
    header.append(" " * padding, style=Style(color=COLORS["white"]))
    header.append("CLAUDE CODE WRAPPED ", style=Style(color=COLORS["white"], bold=True))
    header.append(format_year_display(year), style=Style(color=COLORS["orange"], bold=True))
    header.append("\n" + "═" * width, style=Style(color=COLORS["orange"]))
    return header


def create_dramatic_stat(value: str, label: str, subtitle: str = "", color: str = COLORS["orange"], extra_lines: list[tuple[str, str]] = None) -> Text:
    """Create a dramatic full-screen stat reveal."""
    text = Text()
    text.append("\n\n\n\n\n")
    text.append(f"{value}\n", style=Style(color=color, bold=True))
    text.append(f"{label}\n\n", style=Style(color=COLORS["white"], bold=True))
    if subtitle:
        text.append(subtitle, style=Style(color=COLORS["gray"]))
    if extra_lines:
        text.append("\n\n")
        for line, line_color in extra_lines:
            text.append(f"{line}\n", style=Style(color=line_color))
    text.append("\n\n\n\n")
    text.append("press [ENTER] to continue", style=Style(color=COLORS["dark"]))
    return text


def create_title_slide(year: int | None) -> Text:
    """Create the opening title (static version for non-animated mode)."""
    title = Text()
    title.append("\n\n\n")
    title.append("  ░█████╗░██╗░░░░░░█████╗░██╗░░░██╗██████╗░███████╗\n", style="#C96442")
    title.append("  ██╔══██╗██║░░░░░██╔══██╗██║░░░██║██╔══██╗██╔════╝\n", style="#C96442")
    title.append("  ██║░░╚═╝██║░░░░░███████║██║░░░██║██║░░██║█████╗░░\n", style="#C96442")
    title.append("  ██║░░██╗██║░░░░░██╔══██║██║░░░██║██║░░██║██╔══╝░░\n", style="#C96442")
    title.append("  ╚█████╔╝███████╗██║░░██║╚██████╔╝██████╔╝███████╗\n", style="#C96442")
    title.append("  ░╚════╝░╚══════╝╚═╝░░╚═╝░╚═════╝░╚═════╝░╚══════╝\n", style="#C96442")
    title.append("\n")
    title.append("              C O D E   W R A P P E D\n", style=Style(color=COLORS["white"], bold=True))
    year_display = format_year_display(year)
    title.append(f"                    {year_display}\n\n", style=Style(color=COLORS["purple"], bold=True))
    title.append("                   by ", style=Style(color=COLORS["gray"]))
    title.append("Trollefsen", style=Style(color=COLORS["blue"], bold=True, link="https://github.com/da-troll"))
    title.append("\n\n\n")
    title.append("               press [ENTER] to begin", style=Style(color=COLORS["dark"]))
    title.append("\n\n")
    return title


# ASCII art lines for animated display
CLAUDE_ASCII_LINES = [
    "  ░█████╗░██╗░░░░░░█████╗░██╗░░░██╗██████╗░███████╗",
    "  ██╔══██╗██║░░░░░██╔══██╗██║░░░██║██╔══██╗██╔════╝",
    "  ██║░░╚═╝██║░░░░░███████║██║░░░██║██║░░██║█████╗░░",
    "  ██║░░██╗██║░░░░░██╔══██║██║░░░██║██║░░██║██╔══╝░░",
    "  ╚█████╔╝███████╗██║░░██║╚██████╔╝██████╔╝███████╗",
    "  ░╚════╝░╚══════╝╚═╝░░╚═╝░╚═════╝░╚═════╝░╚══════╝",
]


def render_animated_title(console: Console, year: int | None):
    """Render the title slide with animations."""
    console.print("\n\n\n")

    # Fade in ASCII art line by line (CLAUDE logo)
    animate_ascii_art(console, CLAUDE_ASCII_LINES, color="#C96442", delay=0.08)

    console.print()
    dramatic_pause(0.3)

    # Build tree by typing out "CODE WRAPPED" - grows like a Christmas tree
    # First C = yellow (star), D in CODE & A,E in WRAPPED = white (tinsel), rest = green
    # Note: Empty print first to work around Rich centering bug on first line
    console.print(Align.center(Text("")))
    tree_text = "C O D E   W R A P P E D"
    final_width = len(tree_text)  # 23 characters
    # Character indices: C=0, O=2, D=4, E=6, W=10, R=12, A=14, P=16, P=18, E=20, D=22
    tinsel_indices = {4, 14, 20}  # D in CODE, A in WRAPPED, E in WRAPPED

    is_first_line = True
    for end_idx in range(1, len(tree_text) + 1):
        # Get the visible portion
        visible = tree_text[:end_idx]
        # Pad to full width so centering is consistent
        padded = visible.center(final_width)

        # Build styled text
        styled = Text()
        # Python's center() uses ceiling division for left padding
        left_pad = (final_width - len(visible) + 1) // 2
        for j, c in enumerate(padded):
            # Map padded index back to original index
            orig_idx = j - left_pad
            if orig_idx < 0 or orig_idx >= len(visible):
                styled.append(c)  # Padding space
            elif orig_idx == 0 and is_first_line:  # First C = yellow star
                styled.append(c, style=Style(color=COLORS["yellow"], bold=True))
            elif orig_idx in tinsel_indices and c != " ":  # Tinsel = white
                styled.append(c, style=Style(color=COLORS["white"], bold=True))
            elif c == " ":
                styled.append(c)
            else:  # Rest = green
                styled.append(c, style=Style(color=COLORS["green"], bold=True))

        console.print(Align.center(styled))

        if tree_text[end_idx - 1] not in " ":
            time.sleep(0.04)
            is_first_line = False

    dramatic_pause(0.2)

    # Tree stump - 3 years stacked
    year_display = format_year_display(year)
    for _ in range(3):
        year_text = Text(year_display, style=Style(color=COLORS["purple"], bold=True))
        console.print(Align.center(year_text))
        time.sleep(0.15)

    console.print()
    dramatic_pause(0.3)

    # Credits
    credits = Text()
    credits.append("by ", style=Style(color=COLORS["gray"]))
    credits.append("Trollefsen", style=Style(color=COLORS["blue"], bold=True, link="https://github.com/da-troll"))
    console.print(Align.center(credits))

    console.print("\n\n")
    prompt = Text("press [ENTER] to begin", style=Style(color=COLORS["dark"]))
    console.print(Align.center(prompt))


def create_big_stat(value: str, label: str, color: str = COLORS["orange"]) -> Text:
    """Create a big statistic display."""
    text = Text()
    text.append(f"{value}\n", style=Style(color=color, bold=True))
    text.append(label, style=Style(color=COLORS["gray"]))
    return text


def get_contribution_data(daily_stats: dict, year: int | None) -> tuple:
    """Calculate contribution graph data. Returns (weeks_data, max_count, active_count, date_range, start_date, end_date)."""
    if not daily_stats:
        return [], 0, 0, "", None, None

    # Calculate date range
    if year is None:
        dates = [datetime.strptime(d, "%Y-%m-%d") for d in daily_stats.keys()]
        start_date = min(dates) if dates else datetime.now()
        end_date = max(dates) if dates else datetime.now()
    else:
        start_date = datetime(year, 1, 1)
        today = datetime.now()
        end_date = today if year == today.year else datetime(year, 12, 31)

    max_count = max(s.message_count for s in daily_stats.values()) if daily_stats else 1

    # Build weeks with their start dates
    weeks_data = []
    current = start_date - timedelta(days=start_date.weekday())

    while current <= end_date:
        week = []
        for day in range(7):
            date = current + timedelta(days=day)
            date_str = date.strftime("%Y-%m-%d")
            if year is not None and date.year != year:
                level = 0
            elif date_str in daily_stats:
                count = daily_stats[date_str].message_count
                level = min(4, 1 + int((count / max_count) * 3)) if count > 0 else 0
            else:
                level = 0
            week.append(level)
        weeks_data.append((current, week))
        current += timedelta(days=7)

    # Trim leading empty weeks
    first_active_idx = 0
    for i, (_, week) in enumerate(weeks_data):
        if any(level > 0 for level in week):
            first_active_date = weeks_data[i][0]
            month_start = first_active_date.replace(day=1)
            for j, (week_start, _) in enumerate(weeks_data):
                if week_start <= month_start < week_start + timedelta(days=7):
                    first_active_idx = j
                    break
            else:
                first_active_idx = max(0, i - 1)
            break

    weeks_data = weeks_data[first_active_idx:]

    # Calculate date range for title
    if weeks_data:
        display_start = weeks_data[0][0]
        display_end = min(weeks_data[-1][0] + timedelta(days=6), end_date)
        date_range = f"{display_start.strftime('%b')} - {display_end.strftime('%b %Y')}"
    else:
        date_range = ""

    active_count = len([d for d in daily_stats.values() if d.message_count > 0])

    return weeks_data, max_count, active_count, date_range, start_date, end_date


def build_month_row(weeks_data: list) -> Text:
    """Build the month labels row for contribution graph."""
    month_row = Text()
    month_row.append("    ", style=Style(color=COLORS["gray"]))
    last_month = None
    skip_count = 0
    for i, (week_start, _) in enumerate(weeks_data):
        if skip_count > 0:
            skip_count -= 1
            continue
        month_changed = week_start.month != last_month
        if month_changed:
            month_abbr = week_start.strftime("%b")
            month_row.append(f"{month_abbr} ", style=Style(color=COLORS["gray"]))
            last_month = week_start.month
            skip_count = 1
        else:
            month_row.append("  ", style=Style(color=COLORS["gray"]))
    month_row.append("\n")
    return month_row


def create_contribution_graph(daily_stats: dict, year: int | None) -> Panel:
    """Create a GitHub-style contribution graph for the full year or all-time."""
    weeks_data, _, active_count, date_range, _, _ = get_contribution_data(daily_stats, year)

    if not weeks_data:
        return Panel("No activity data", title="Activity", border_style=COLORS["gray"])

    month_row = build_month_row(weeks_data)

    # Build the graph
    graph = Text()
    graph.append("\n")
    graph.append(month_row)

    days_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for row in range(7):
        graph.append(f"{days_labels[row]} ", style=Style(color=COLORS["gray"]))
        for _, week in weeks_data:
            color = CONTRIB_COLORS[week[row]]
            graph.append("■ ", style=Style(color=color))
        graph.append("\n")

    legend = Text()
    legend.append("Less ", style=Style(color=COLORS["gray"]))
    for color in CONTRIB_COLORS:
        legend.append("■ ", style=Style(color=color))
    legend.append("More", style=Style(color=COLORS["gray"]))

    content = Group(Align.center(graph), Align.center(legend))

    return Panel(
        Align.center(content),
        title=f"Activity · {active_count} days · {date_range}",
        border_style=Style(color=COLORS["green"]),
        padding=(0, 2),
    )


def animate_contribution_graph(console: Console, daily_stats: dict, year: int | None, delay: float = 0.015):
    """Animate the contribution graph squares appearing row by row."""
    weeks_data, _, active_count, date_range, _, _ = get_contribution_data(daily_stats, year)

    if not weeks_data:
        console.print(Panel("No activity data", title="Activity", border_style=COLORS["gray"]))
        return

    month_row = build_month_row(weeks_data)
    days_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    num_weeks = len(weeks_data)

    def build_graph_frame(revealed_squares: int) -> Panel:
        """Build graph with only revealed_squares visible."""
        graph = Text()
        graph.append("\n")
        graph.append(month_row)

        squares_shown = 0
        for row in range(7):
            graph.append(f"{days_labels[row]} ", style=Style(color=COLORS["gray"]))
            for _, week in weeks_data:
                if squares_shown < revealed_squares:
                    color = CONTRIB_COLORS[week[row]]
                    graph.append("■ ", style=Style(color=color))
                else:
                    # Empty placeholder (dark gray)
                    graph.append("■ ", style=Style(color=COLORS["dark"]))
                squares_shown += 1
            graph.append("\n")

        legend = Text()
        legend.append("Less ", style=Style(color=COLORS["gray"]))
        for color in CONTRIB_COLORS:
            legend.append("■ ", style=Style(color=color))
        legend.append("More", style=Style(color=COLORS["gray"]))

        content = Group(Align.center(graph), Align.center(legend))
        return Panel(
            Align.center(content),
            title=f"Activity · {active_count} days · {date_range}",
            border_style=Style(color=COLORS["green"]),
            padding=(0, 2),
        )

    total_squares = 7 * num_weeks

    with Live(build_graph_frame(0), console=console, refresh_per_second=60, transient=True) as live:
        for i in range(total_squares + 1):
            live.update(build_graph_frame(i))
            time.sleep(delay)

    # Print final state
    console.print(build_graph_frame(total_squares))


def create_hour_chart(distribution: list[int]) -> Panel:
    """Create a clean hourly distribution chart."""
    max_val = max(distribution) if any(distribution) else 1
    chars = "▁▂▃▄▅▆▇█"

    content = Text()
    for i, val in enumerate(distribution):
        idx = int((val / max_val) * (len(chars) - 1)) if max_val > 0 else 0
        if 6 <= i < 12:
            color = COLORS["orange"]
        elif 12 <= i < 18:
            color = COLORS["blue"]
        elif 18 <= i < 24:
            color = COLORS["yellow"]
        else:
            color = COLORS["gray"]
        content.append(chars[idx], style=Style(color=color))

    # Build aligned label (24 chars to match 24 bars)
    # Labels at positions: 0, 6, 12, 18, with end marker
    content.append("\n")
    content.append("0     6     12    18    24", style=Style(color=COLORS["gray"]))

    return Panel(
        Align.center(content),
        title="Hours",
        border_style=Style(color=COLORS["yellow"]),
        padding=(0, 1),
        expand=True,
    )


def create_weekday_chart(distribution: list[int], width: int = 80) -> Panel:
    """Create a clean weekday distribution chart that fills available width."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    max_val = max(distribution) if any(distribution) else 1

    # Calculate bar width: width - day label (4) - count (~8) - padding/borders (~6)
    bar_width = max(10, width - 18)

    content = Text()
    content.append("\n")  # Add spacing above Monday
    for i, (day, count) in enumerate(zip(days, distribution)):
        bar_len = int((count / max_val) * bar_width) if max_val > 0 else 0
        bar = "█" * bar_len + "░" * (bar_width - bar_len)
        content.append(f"{day} ", style=Style(color=COLORS["gray"]))
        content.append(bar, style=Style(color=COLORS["blue"]))
        content.append(f" {count:,}\n", style=Style(color=COLORS["gray"]))

    return Panel(
        content,
        title="Days",
        border_style=Style(color=COLORS["blue"]),
        padding=(0, 1),
        expand=True,
    )


def create_top_list(items: list[tuple[str, int]], title: str, color: str, width: int = 30) -> Panel:
    """Create a clean top items list with dynamic bar width."""
    content = Text()
    content.append("\n")  # Add spacing above first item
    max_val = max(v for _, v in items) if items else 1

    # Calculate bar width for the bar line
    # Overhead: panel border (2), padding (2), count " XX,XXX" (~8) = 12 chars
    bar_width = max(8, width - 12)

    for i, (name, count) in enumerate(items[:5], 1):
        # Line 1: rank + name
        content.append(f"{i}. ", style=Style(color=COLORS["gray"]))
        content.append(f"{name[:12]}\n", style=Style(color=COLORS["white"]))
        # Line 2: bar + count
        bar_len = int((count / max_val) * bar_width)
        content.append("▓" * bar_len, style=Style(color=color))
        content.append("░" * (bar_width - bar_len), style=Style(color=COLORS["dark"]))
        content.append(f" {count:,}\n", style=Style(color=COLORS["gray"]))

    return Panel(
        content,
        title=title,
        border_style=Style(color=color),
        padding=(0, 1),
    )


def create_personality_card(stats: WrappedStats) -> Panel:
    """Create the personality card."""
    personality = determine_personality(stats)

    content = Text()
    content.append(f"\n  {personality['emoji']}  ", style=Style(bold=True))
    content.append(f"{personality['title']}\n\n", style=Style(color=COLORS["purple"], bold=True))
    content.append(f"  {personality['description']}\n", style=Style(color=COLORS["gray"]))

    return Panel(
        content,
        title="Your Type",
        border_style=Style(color=COLORS["purple"]),
        padding=(0, 1),
    )


def determine_personality(stats: WrappedStats) -> dict:
    """Determine user's coding personality based on stats."""
    night_hours = sum(stats.hourly_distribution[22:]) + sum(stats.hourly_distribution[:6])
    day_hours = sum(stats.hourly_distribution[6:22])
    top_tool = stats.top_tools[0][0] if stats.top_tools else None
    weekend_msgs = stats.weekday_distribution[5] + stats.weekday_distribution[6]
    weekday_msgs = sum(stats.weekday_distribution[:5])

    if night_hours > day_hours * 0.4:
        return {"emoji": "🦉", "title": "Night Owl", "description": "The quiet hours are your sanctuary."}
    elif stats.streak_longest >= 14:
        return {"emoji": "🔥", "title": "Streak Master", "description": f"{stats.streak_longest} days. Unstoppable."}
    elif top_tool == "Edit":
        return {"emoji": "🎨", "title": "The Refactorer", "description": "You see beauty in clean code."}
    elif top_tool == "Bash":
        return {"emoji": "⚡", "title": "Terminal Warrior", "description": "Command line is your domain."}
    elif stats.total_projects >= 5:
        return {"emoji": "🚀", "title": "Empire Builder", "description": f"{stats.total_projects} projects. Legend."}
    elif weekend_msgs > weekday_msgs * 0.5:
        return {"emoji": "🌙", "title": "Weekend Warrior", "description": "Passion fuels your weekends."}
    elif stats.models_used.get("Opus", 0) > stats.models_used.get("Sonnet", 0):
        return {"emoji": "🎯", "title": "Perfectionist", "description": "Only the best will do."}
    else:
        return {"emoji": "💻", "title": "Dedicated Dev", "description": "Steady and reliable."}


def get_fun_facts(stats: WrappedStats) -> list[tuple[str, str]]:
    """Generate fun facts / bloopers based on stats - only 3 key facts."""
    facts = []

    # Late night coding days (midnight to 5am)
    if stats.late_night_days > 0:
        facts.append(("🌙", f"You coded after midnight on {stats.late_night_days} days. Sleep is overrated."))

    # Most active day insight
    if stats.most_active_day:
        day_name = stats.most_active_day[0].strftime("%A")
        facts.append(("📅", f"Your biggest day was a {day_name}. {stats.most_active_day[1]:,} messages. Epic."))

    # Streak fact
    if stats.streak_longest >= 1:
        facts.append(("🔥", f"Your {stats.streak_longest}-day streak was legendary. Consistency wins."))

    return facts


def create_fun_facts_slide(facts: list[tuple[str, str]], console_width: int = 80, console_height: int = 24) -> Text:
    """Create a fun facts slide (without prompt text)."""
    # Left quarter position
    pad = " " * (console_width // 4)

    # Calculate content height: title (1) + blank lines (2) + facts (2 lines each) + prompt (2)
    content_height = 1 + 2 + len(facts) * 2 + 2
    vertical_pad = max(0, (console_height - content_height) // 2)

    text = Text()
    text.append("\n" * vertical_pad)
    text.append(f"{pad}B L O O P E R S  &  F U N  F A C T S\n\n", style=Style(color=COLORS["purple"], bold=True))

    for emoji, fact in facts:
        text.append(f"{pad}{emoji} ", style=Style(bold=True))
        text.append(f"{fact}\n\n", style=Style(color=COLORS["white"]))

    return text


def simplify_model_name(model: str) -> str:
    """Simplify a full model ID to a display name."""
    model_lower = model.lower()
    if 'opus-4-5' in model_lower or 'opus-4.5' in model_lower:
        return 'Opus 4.5'
    elif 'opus-4-1' in model_lower or 'opus-4.1' in model_lower:
        return 'Opus 4.1'
    elif 'opus' in model_lower:
        return 'Opus'
    elif 'sonnet-4-5' in model_lower or 'sonnet-4.5' in model_lower:
        return 'Sonnet 4.5'
    elif 'sonnet' in model_lower:
        return 'Sonnet'
    elif 'haiku-4-5' in model_lower or 'haiku-4.5' in model_lower:
        return 'Haiku 4.5'
    elif 'haiku' in model_lower:
        return 'Haiku'
    return model


def create_monthly_cost_table(stats: WrappedStats) -> Panel:
    """Create a monthly cost breakdown table like ccusage."""
    from .pricing import format_cost

    table = Table(
        show_header=True,
        header_style=Style(color=COLORS["white"], bold=True),
        border_style=Style(color=COLORS["dark"]),
        box=None,
        padding=(0, 2),
        expand=True,
    )

    # Month column gets larger ratio to create gap before data columns
    table.add_column("Month", style=Style(color=COLORS["gray"]), ratio=3)
    table.add_column("Input", justify="right", style=Style(color=COLORS["blue"]), ratio=2)
    table.add_column("Output", justify="right", style=Style(color=COLORS["orange"]), ratio=2)
    table.add_column("Cache", justify="right", style=Style(color=COLORS["purple"]), ratio=2)
    table.add_column("Cost", justify="right", style=Style(color=COLORS["green"], bold=True), ratio=2)

    # Sort months chronologically
    sorted_months = sorted(stats.monthly_costs.keys())

    for month_key in sorted_months:
        cost = stats.monthly_costs.get(month_key, 0)
        tokens = stats.monthly_tokens.get(month_key, {})

        # Format month name
        try:
            month_date = datetime.strptime(month_key, "%Y-%m")
            month_name = month_date.strftime("%b %Y")
        except ValueError:
            month_name = month_key

        input_tokens = tokens.get("input", 0)
        output_tokens = tokens.get("output", 0)
        cache_tokens = tokens.get("cache_create", 0) + tokens.get("cache_read", 0)

        table.add_row(
            month_name,
            format_tokens(input_tokens),
            format_tokens(output_tokens),
            format_tokens(cache_tokens),
            format_cost(cost),
        )

    # Add total row
    if sorted_months:
        table.add_row("", "", "", "", "")  # Separator
        table.add_row(
            "Total",
            format_tokens(stats.total_input_tokens),
            format_tokens(stats.total_output_tokens),
            format_tokens(stats.total_cache_creation_tokens + stats.total_cache_read_tokens),
            format_cost(stats.estimated_cost) if stats.estimated_cost else "N/A",
            style=Style(bold=True),
        )

    return Panel(
        table,
        title="Monthly Cost Breakdown",
        border_style=Style(color=COLORS["green"]),
        padding=(0, 1),
    )


def create_credits_roll(stats: WrappedStats, console_width: int = 80, console_height: int = 24) -> list[Text]:
    """Create end credits content."""
    from .pricing import format_cost

    # Dynamic positioning based on console width - all sections at left quarter
    pad = " " * (console_width // 4)

    def vertical_center(content_lines: int) -> str:
        """Return newlines needed to vertically center content."""
        padding = max(0, (console_height - content_lines) // 2)
        return "\n" * padding

    # Build frames with labels for post-processing [ENTER] prompts
    labeled_frames: list[tuple[Text, str]] = []

    # Aggregate costs by simplified model name for display
    display_costs: dict[str, float] = {}
    for model, cost in stats.cost_by_model.items():
        display_name = simplify_model_name(model)
        display_costs[display_name] = display_costs.get(display_name, 0) + cost

    # Frame 1: The Numbers (cost + tokens) - ~15 content lines
    numbers = Text()
    numbers.append(vertical_center(15))
    numbers.append(f"{pad}T H E   N U M B E R S\n\n", style=Style(color=COLORS["green"], bold=True))
    if stats.estimated_cost is not None:
        numbers.append(f"{pad}Estimated Cost              ", style=Style(color=COLORS["white"], bold=True))
        numbers.append(f"{format_cost(stats.estimated_cost):>20}\n", style=Style(color=COLORS["green"], bold=True))
        for model, cost in sorted(display_costs.items(), key=lambda x: -x[1]):
            cost_str = format_cost(cost)
            numbers.append(f"{pad}{model}{'':>{27 - len(model)}}", style=Style(color=COLORS["gray"]))
            numbers.append(f"{cost_str:>20}\n", style=Style(color=COLORS["gray"]))
    numbers.append(f"\n{pad}Tokens                      ", style=Style(color=COLORS["white"], bold=True))
    tokens_str = format_tokens(stats.total_tokens)
    numbers.append(f"{tokens_str:>20}\n", style=Style(color=COLORS["orange"], bold=True))
    # Right-align token breakdown values
    input_str = format_tokens(stats.total_input_tokens)
    output_str = format_tokens(stats.total_output_tokens)
    cache_create_str = format_tokens(stats.total_cache_creation_tokens)
    cache_read_str = format_tokens(stats.total_cache_read_tokens)
    numbers.append(f"{pad}Input                       ", style=Style(color=COLORS["gray"]))
    numbers.append(f"{input_str:>20}\n", style=Style(color=COLORS["gray"]))
    numbers.append(f"{pad}Output                      ", style=Style(color=COLORS["gray"]))
    numbers.append(f"{output_str:>20}\n", style=Style(color=COLORS["gray"]))
    numbers.append(f"{pad}Cache write                 ", style=Style(color=COLORS["gray"]))
    numbers.append(f"{cache_create_str:>20}\n", style=Style(color=COLORS["gray"]))
    numbers.append(f"{pad}Cache read                  ", style=Style(color=COLORS["gray"]))
    numbers.append(f"{cache_read_str:>20}\n", style=Style(color=COLORS["gray"]))
    numbers.append("\n\n")
    labeled_frames.append((numbers, "numbers"))

    # Frame 2: Timeline (full year context) - ~12 content lines
    timeline = Text()
    timeline.append(vertical_center(12))
    timeline.append(f"{pad}T I M E L I N E\n\n", style=Style(color=COLORS["orange"], bold=True))
    timeline.append(f"{pad}Period                 ", style=Style(color=COLORS["white"], bold=True))
    # Use sentence case for "All time" in timeline
    period_text = "All time" if stats.year is None else str(stats.year)
    timeline.append(f"{period_text:>20}\n", style=Style(color=COLORS["orange"], bold=True))
    if stats.first_message_date:
        timeline.append(f"{pad}Journey started        ", style=Style(color=COLORS["white"], bold=True))
        timeline.append(f"{stats.first_message_date.strftime('%B %d, %Y'):>20}\n", style=Style(color=COLORS["gray"]))
    # Calculate total days in year
    today = datetime.now()
    if stats.year is None:
        # All-time: calculate days from first to last message
        if stats.first_message_date and stats.last_message_date:
            total_days_year = (stats.last_message_date - stats.first_message_date).days + 1
        else:
            total_days_year = stats.active_days
    elif stats.year == today.year:
        total_days_year = (today - datetime(stats.year, 1, 1)).days + 1
    else:
        total_days_year = 366 if stats.year % 4 == 0 else 365

    # Calculate days since journey start
    if stats.first_message_date:
        if stats.year is None:
            # All-time: days from first to last message
            if stats.last_message_date:
                days_since_journey = (stats.last_message_date - stats.first_message_date).days + 1
            else:
                days_since_journey = stats.active_days
        elif stats.year == today.year:
            # Current year: days from first message to today
            first_msg_date = stats.first_message_date.date() if hasattr(stats.first_message_date, 'date') else stats.first_message_date
            days_since_journey = (today.date() - first_msg_date).days + 1
        else:
            # Past year: days from first message to end of year
            year_end = datetime(stats.year, 12, 31).date()
            first_msg_date = stats.first_message_date.date() if hasattr(stats.first_message_date, 'date') else stats.first_message_date
            days_since_journey = (year_end - first_msg_date).days + 1
    else:
        days_since_journey = stats.active_days

    timeline.append(f"\n{pad}Active days            ", style=Style(color=COLORS["white"], bold=True))
    timeline.append(f"{stats.active_days:>20}\n", style=Style(color=COLORS["orange"], bold=True))
    year_pct = (stats.active_days / total_days_year * 100) if total_days_year > 0 else 0
    journey_pct = (stats.active_days / days_since_journey * 100) if days_since_journey > 0 else 0
    year_pct_str = f"{year_pct:.1f}%"
    journey_pct_str = f"{journey_pct:.1f}%"
    timeline.append(f"{pad}Active days of year    ", style=Style(color=COLORS["white"], bold=True))
    timeline.append(f"{year_pct_str:>20}\n", style=Style(color=COLORS["gray"]))
    timeline.append(f"{pad}Active days on journey ", style=Style(color=COLORS["white"], bold=True))
    timeline.append(f"{journey_pct_str:>20}\n", style=Style(color=COLORS["purple"], bold=True))
    if stats.most_active_hour is not None:
        hour_label = "AM" if stats.most_active_hour < 12 else "PM"
        hour_12 = stats.most_active_hour % 12 or 12
        hour_str = f"{hour_12}:00 {hour_label}"
        timeline.append(f"{pad}Peak hour              ", style=Style(color=COLORS["white"], bold=True))
        timeline.append(f"{hour_str:>20}\n", style=Style(color=COLORS["purple"], bold=True))
    timeline.append("\n\n")
    labeled_frames.append((timeline, "timeline"))

    # Frame 3: Averages - ~12 content lines
    from .pricing import format_cost
    averages = Text()
    averages.append(vertical_center(12))
    averages.append(f"{pad}A V E R A G E S\n\n", style=Style(color=COLORS["blue"], bold=True))
    averages.append(f"{pad}Messages                    ", style=Style(color=COLORS["white"], bold=True))
    averages.append("\n", style=Style(color=COLORS["white"]))
    averages.append(f"{pad}Per day                     ", style=Style(color=COLORS["gray"]))
    averages.append(f"{stats.avg_messages_per_day:>20.1f}\n", style=Style(color=COLORS["gray"]))
    averages.append(f"{pad}Per week                    ", style=Style(color=COLORS["gray"]))
    averages.append(f"{stats.avg_messages_per_week:>20.1f}\n", style=Style(color=COLORS["gray"]))
    averages.append(f"{pad}Per month                   ", style=Style(color=COLORS["gray"]))
    averages.append(f"{stats.avg_messages_per_month:>20.1f}\n", style=Style(color=COLORS["gray"]))
    if stats.estimated_cost is not None:
        averages.append(f"\n{pad}Cost                        ", style=Style(color=COLORS["white"], bold=True))
        averages.append("\n", style=Style(color=COLORS["white"]))
        averages.append(f"{pad}Per day                     ", style=Style(color=COLORS["gray"]))
        averages.append(f"{format_cost(stats.avg_cost_per_day):>20}\n", style=Style(color=COLORS["gray"]))
        averages.append(f"{pad}Per week                    ", style=Style(color=COLORS["gray"]))
        averages.append(f"{format_cost(stats.avg_cost_per_week):>20}\n", style=Style(color=COLORS["gray"]))
        averages.append(f"{pad}Per month                   ", style=Style(color=COLORS["gray"]))
        averages.append(f"{format_cost(stats.avg_cost_per_month):>20}\n", style=Style(color=COLORS["gray"]))
    averages.append("\n\n")
    labeled_frames.append((averages, "averages"))

    # Frame 4: Longest Streak (if significant) - ~10 content lines
    if stats.streak_longest >= 3 and stats.streak_longest_start and stats.streak_longest_end:
        streak = Text()
        streak.append(vertical_center(10))
        streak.append(f"{pad}L O N G E S T   S T R E A K\n\n", style=Style(color=COLORS["blue"], bold=True))
        streak.append(f"{pad}{stats.streak_longest}", style=Style(color=COLORS["blue"], bold=True))
        streak.append(" days of consistent coding\n\n", style=Style(color=COLORS["white"], bold=True))
        streak.append(f"{pad}From  ", style=Style(color=COLORS["white"], bold=True))
        streak.append(f"{stats.streak_longest_start.strftime('%B %d, %Y'):>29}\n", style=Style(color=COLORS["gray"]))
        streak.append(f"{pad}To    ", style=Style(color=COLORS["white"], bold=True))
        streak.append(f"{stats.streak_longest_end.strftime('%B %d, %Y'):>29}\n", style=Style(color=COLORS["gray"]))
        streak.append(f"\n{pad}Consistency is the key to mastery.\n", style=Style(color=COLORS["gray"]))
        if stats.streak_current > 0:
            streak.append(f"\n{pad}Current streak: {stats.streak_current} days\n", style=Style(color=COLORS["gray"]))
        streak.append("\n\n")
        labeled_frames.append((streak, "streak"))

    # Frame 5: Longest Conversation - ~10 content lines
    if stats.longest_conversation_messages > 0:
        longest = Text()
        longest.append(vertical_center(10))
        longest.append(f"{pad}L O N G E S T   C O N V E R S A T I O N\n\n", style=Style(color=COLORS["purple"], bold=True))
        longest.append(f"{pad}Messages    ", style=Style(color=COLORS["white"], bold=True))
        longest.append(f"{stats.longest_conversation_messages:,}\n", style=Style(color=COLORS["purple"], bold=True))
        if stats.longest_conversation_tokens > 0:
            longest.append(f"{pad}Tokens      ", style=Style(color=COLORS["white"], bold=True))
            longest.append(f"{format_tokens(stats.longest_conversation_tokens)}\n", style=Style(color=COLORS["orange"], bold=True))
        if stats.longest_conversation_date:
            longest.append(f"{pad}Date        ", style=Style(color=COLORS["white"], bold=True))
            longest.append(f"{stats.longest_conversation_date.strftime('%B %d, %Y')}\n", style=Style(color=COLORS["gray"]))
        longest.append(f"\n{pad}That's one epic coding session!\n", style=Style(color=COLORS["gray"]))
        longest.append("\n\n")
        labeled_frames.append((longest, "conversation"))

    # Frame 6: Cast (models) - ~8 content lines
    cast = Text()
    cast.append(vertical_center(8))
    cast.append(f"{pad}S T A R R I N G\n\n", style=Style(color=COLORS["purple"], bold=True))
    for model, count in stats.models_used.most_common(3):
        cast.append(f"{pad}Claude {model}", style=Style(color=COLORS["white"], bold=True))
        cast.append(f"  ({count:,} messages)\n", style=Style(color=COLORS["gray"]))
    cast.append("\n\n\n")
    labeled_frames.append((cast, "starring"))

    # Frame 7: Projects - ~10 content lines
    if stats.top_projects:
        projects = Text()
        projects.append(vertical_center(10))
        projects.append(f"{pad}P R O J E C T S\n\n", style=Style(color=COLORS["blue"], bold=True))
        for proj, count in stats.top_projects[:5]:
            projects.append(f"{pad}{proj}", style=Style(color=COLORS["white"], bold=True))
            projects.append(f"  ({count:,} messages)\n", style=Style(color=COLORS["gray"]))
        projects.append("\n\n\n")
        labeled_frames.append((projects, "projects"))

    # Frame 8: Final card - ~4 content lines, CENTER aligned
    final = Text()
    final.append(vertical_center(4))
    if stats.year is not None:
        see_you_text = f"See you in {stats.year + 1}"
        center_pad = " " * ((console_width - len(see_you_text)) // 2)
        final.append(f"{center_pad}See you in ", style=Style(color=COLORS["gray"]))
        final.append(f"{stats.year + 1}", style=Style(color=COLORS["orange"], bold=True))
    else:
        alt_text = "Nothing exploded. That's a win."
        center_pad = " " * ((console_width - len(alt_text)) // 2)
        final.append(f"{center_pad}{alt_text}", style=Style(color=COLORS["orange"], bold=True))
    final.append("\n\n\n\n\n\n", style=Style(color=COLORS["gray"]))
    exit_text = "[ENTER] to exit"
    exit_pad = " " * ((console_width - len(exit_text)) // 2)
    final.append(f"{exit_pad}{exit_text}", style=Style(color=COLORS["dark"]))
    labeled_frames.append((final, "final"))

    # Map labels to friendly names for [ENTER] prompts
    label_to_name = {
        "numbers": "the numbers",
        "timeline": "the timeline",
        "averages": "the averages",
        "streak": "the streak",
        "conversation": "the longest conversation",
        "starring": "the starring",
        "projects": "the projects",
        "final": None,  # Final frame has its own text
    }

    # Post-process: add [ENTER] prompts based on next frame
    frames = []
    for i, (frame, label) in enumerate(labeled_frames):
        if label != "final":  # Final frame already has its [ENTER] text
            if i + 1 < len(labeled_frames):
                next_label = labeled_frames[i + 1][1]
                next_name = label_to_name.get(next_label, "continue")
                if next_name:
                    frame.append(f"{pad}press [ENTER] for {next_name}", style=Style(color=COLORS["dark"]))
                else:
                    frame.append(f"{pad}press [ENTER] to continue", style=Style(color=COLORS["dark"]))
            else:
                frame.append(f"{pad}press [ENTER] to continue", style=Style(color=COLORS["dark"]))
        frames.append(frame)

    return frames


def render_wrapped(stats: WrappedStats, console: Console | None = None, animate: bool = True):
    """Render the complete wrapped experience."""
    if console is None:
        console = Console(style=Style(bgcolor="#2c2c2c"))

    # === CINEMATIC MODE ===
    if animate:
        # Loading - centered vertically and full width
        console.clear()

        # Calculate vertical centering
        terminal_height = console.height
        vertical_padding = (terminal_height // 2) - 1
        for _ in range(vertical_padding):
            console.print()

        # Calculate bar width (full width minus text and spinner)
        loading_text = "Unwrapping your history..." if stats.year is None else "Unwrapping your year..."
        text_width = len(loading_text) + 4  # spinner + spacing
        bar_width = max(20, console.width - text_width - 4)

        with Progress(
            SpinnerColumn(style=COLORS["orange"]),
            TextColumn(f"[bold]{loading_text}[/bold]"),
            BarColumn(complete_style=COLORS["orange"], finished_style=COLORS["green"], bar_width=bar_width),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("", total=100)
            for _ in range(100):
                time.sleep(0.012)
                progress.update(task, advance=1)

        console.clear()

        # Title slide - ANIMATED
        render_animated_title(console, stats.year)
        wait_for_keypress()
        console.clear()

        # Slide 1: Messages with count-up animation
        first_date = stats.first_message_date.strftime("%d %B") if stats.first_message_date else "the beginning"
        last_date = stats.last_message_date.strftime("%d %B %Y") if stats.last_message_date else "today"
        messages_subtitle = f"From {first_date} to {last_date}"

        # Center vertically (~8 content lines)
        vertical_pad = max(0, (console.height - 8) // 2)
        console.print("\n" * vertical_pad)
        animate_typing(console, "you exchanged", color=COLORS["gray"], delay=0.03)
        console.print()
        animate_count_up(console, stats.total_messages, duration=1.5, color=COLORS["orange"])
        dramatic_pause(0.2)
        label = Text("MESSAGES", style=Style(color=COLORS["white"], bold=True))
        console.print(Align.center(label))
        console.print()
        animate_typing(console, messages_subtitle, color=COLORS["gray"], delay=0.02)
        console.print("\n\n")
        prompt = Text("press [ENTER] to continue", style=Style(color=COLORS["dark"]))
        console.print(Align.center(prompt))
        wait_for_keypress()
        console.clear()

        # Slide 2: Averages with animated reveals (~10 content lines)
        from .pricing import format_cost
        vertical_pad = max(0, (console.height - 10) // 2)
        console.print("\n" * vertical_pad)
        animate_typing(console, "On average, you sent", color=COLORS["gray"], delay=0.03)
        console.print()

        # Animate each average
        dramatic_pause(0.3)
        avg_day = Text()
        avg_day.append(f"{stats.avg_messages_per_day:.0f}", style=Style(color=COLORS["orange"], bold=True))
        avg_day.append(" messages per day", style=Style(color=COLORS["white"]))
        console.print(Align.center(avg_day))
        time.sleep(0.4)

        avg_week = Text()
        avg_week.append(f"{stats.avg_messages_per_week:.0f}", style=Style(color=COLORS["blue"], bold=True))
        avg_week.append(" messages per week", style=Style(color=COLORS["white"]))
        console.print(Align.center(avg_week))
        time.sleep(0.4)

        avg_month = Text()
        avg_month.append(f"{stats.avg_messages_per_month:.0f}", style=Style(color=COLORS["purple"], bold=True))
        avg_month.append(" messages per month", style=Style(color=COLORS["white"]))
        console.print(Align.center(avg_month))

        if stats.estimated_cost is not None:
            console.print()
            dramatic_pause(0.5)
            cost_text = Text()
            cost_text.append("Costing about ", style=Style(color=COLORS["gray"]))
            cost_text.append(f"{format_cost(stats.avg_cost_per_day)}/day", style=Style(color=COLORS["green"], bold=True))
            cost_text.append(f" · {format_cost(stats.avg_cost_per_week)}/week", style=Style(color=COLORS["green"]))
            cost_text.append(f" · {format_cost(stats.avg_cost_per_month)}/month", style=Style(color=COLORS["green"]))
            console.print(Align.center(cost_text))

        console.print("\n\n")
        prompt = Text("press [ENTER] to continue", style=Style(color=COLORS["dark"]))
        console.print(Align.center(prompt))
        wait_for_keypress()
        console.clear()

        # Slide 3: Tokens with dramatic reveal
        def format_tokens_dramatic(tokens: int) -> str:
            if tokens >= 1_000_000_000:
                return f"{tokens / 1_000_000_000:.1f} Bn"
            if tokens >= 1_000_000:
                return f"{tokens / 1_000_000:.0f} M"
            if tokens >= 1_000:
                return f"{tokens / 1_000:.0f} K"
            return str(tokens)

        # Center vertically (~8 content lines)
        vertical_pad = max(0, (console.height - 8) // 2)
        console.print("\n" * vertical_pad)
        animate_typing(console, "Together, you processed", color=COLORS["gray"], delay=0.03)
        console.print()
        dramatic_pause(0.3)

        # Big token reveal
        tokens_display = format_tokens_dramatic(stats.total_tokens)
        tokens_text = Text(tokens_display, style=Style(color=COLORS["green"], bold=True))
        console.print(Align.center(tokens_text))
        dramatic_pause(0.2)

        tokens_label = Text("TOKENS", style=Style(color=COLORS["white"], bold=True))
        console.print(Align.center(tokens_label))
        console.print()
        animate_typing(console, "processed through the AI", color=COLORS["gray"], delay=0.02)
        console.print("\n\n")
        prompt = Text("press [ENTER] to continue", style=Style(color=COLORS["dark"]))
        console.print(Align.center(prompt))
        wait_for_keypress()
        console.clear()

        # Slide 4: Streak reveal (~6 content lines)
        vertical_pad = max(0, (console.height - 6) // 2)
        console.print("\n" * vertical_pad)
        animate_typing(console, "Your longest streak was", color=COLORS["gray"], delay=0.03)
        console.print()
        dramatic_pause(0.3)

        # Animate streak count
        animate_count_up(console, stats.streak_longest, duration=1.0, color=COLORS["blue"])
        dramatic_pause(0.2)
        streak_label = Text("DAYS IN A ROW", style=Style(color=COLORS["white"], bold=True))
        console.print(Align.center(streak_label))

        console.print("\n\n")
        prompt = Text("press [ENTER] to continue", style=Style(color=COLORS["dark"]))
        console.print(Align.center(prompt))
        wait_for_keypress()
        console.clear()

    # === DASHBOARD VIEW - Split into 4 panels ===

    # PANEL 1: Big Stats + Activity Graph
    if animate:
        console.clear()
    console.print()
    console.print(create_dashboard_header(stats.year, console.width))
    console.print()

    # Big stats row
    stats_table = Table(show_header=False, box=None, padding=(0, 3), expand=True)
    stats_table.add_column(justify="center")
    stats_table.add_column(justify="center")
    stats_table.add_column(justify="center")
    stats_table.add_column(justify="center")

    stats_table.add_row(
        create_big_stat(f"{stats.total_messages:,}", "messages", COLORS["orange"]),
        create_big_stat(str(stats.total_sessions), "sessions", COLORS["purple"]),
        create_big_stat(format_tokens(stats.total_tokens), "tokens", COLORS["green"]),
        create_big_stat(f"{stats.streak_longest}d", "best streak", COLORS["blue"]),
    )
    console.print(Align.center(stats_table))
    console.print()

    # Contribution graph
    if animate:
        animate_contribution_graph(console, stats.daily_stats, stats.year)
    else:
        console.print(create_contribution_graph(stats.daily_stats, stats.year))

    if animate:
        console.print()
        prompt_text = Text()
        prompt_text.append("press [ENTER] to continue", style=Style(color=COLORS["dark"]))
        console.print(Align.center(prompt_text))
        wait_for_keypress()

    # PANEL 2: Personality + Days + Hours
    if animate:
        console.clear()
    console.print()
    console.print(create_dashboard_header(stats.year, console.width))
    console.print()

    # Charts row - Days panel gets 2/3 of width
    charts = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    charts.add_column(ratio=1)
    charts.add_column(ratio=2)
    days_width = (console.width * 2) // 3  # 2/3 of terminal width for Days panel
    charts.add_row(
        create_personality_card(stats),
        create_weekday_chart(stats.weekday_distribution, days_width),
    )
    console.print(charts)

    # Hour chart
    console.print(create_hour_chart(stats.hourly_distribution))

    if animate:
        console.print()
        prompt_text = Text()
        prompt_text.append("press [ENTER] to continue", style=Style(color=COLORS["dark"]))
        console.print(Align.center(prompt_text))
        wait_for_keypress()

    # PANEL 3: Top Projects (full width)
    if animate:
        console.clear()
    console.print()
    console.print(create_dashboard_header(stats.year, console.width))
    console.print()

    console.print(create_top_list(stats.top_projects, "Top Projects", COLORS["green"], console.width))

    if animate:
        console.print()
        prompt_text = Text()
        prompt_text.append("press [ENTER] to continue", style=Style(color=COLORS["dark"]))
        console.print(Align.center(prompt_text))
        wait_for_keypress()

    # PANEL 4: Top Tools + MCPs
    if animate:
        console.clear()
    console.print()
    console.print(create_dashboard_header(stats.year, console.width))
    console.print()

    # Top lists - Tools and MCPs side by side
    lists = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    lists.add_column(ratio=1)
    lists.add_column(ratio=1)
    # Each column gets roughly 1/2 of terminal width
    col_width = console.width // 2
    lists.add_row(
        create_top_list(stats.top_tools[:5], "Top Tools", COLORS["orange"], col_width),
        create_top_list(stats.top_mcps, "Top MCP Servers", COLORS["purple"], col_width) if stats.top_mcps else Text(""),
    )
    console.print(lists)

    if animate:
        console.print()
        prompt_text = Text()
        prompt_text.append("press [ENTER] to continue", style=Style(color=COLORS["dark"]))
        console.print(Align.center(prompt_text))
        wait_for_keypress()

    # PANEL 5: Monthly Costs + Insights
    if animate:
        console.clear()
    console.print()
    console.print(create_dashboard_header(stats.year, console.width))
    console.print()

    # Monthly cost table
    if stats.monthly_costs:
        console.print(create_monthly_cost_table(stats))

    # Insights
    insights = Text()
    if stats.most_active_day:
        insights.append("  Peak day: ", style=Style(color=COLORS["gray"]))
        insights.append(f"{stats.most_active_day[0].strftime('%b %d')}", style=Style(color=COLORS["orange"], bold=True))
        insights.append(f" ({stats.most_active_day[1]:,} msgs)", style=Style(color=COLORS["gray"]))
    if stats.most_active_hour is not None:
        insights.append("  •  Peak hour: ", style=Style(color=COLORS["gray"]))
        insights.append(f"{stats.most_active_hour}:00", style=Style(color=COLORS["purple"], bold=True))
    if stats.primary_model:
        insights.append("  •  Favorite: ", style=Style(color=COLORS["gray"]))
        insights.append(f"Claude {stats.primary_model}", style=Style(color=COLORS["blue"], bold=True))

    console.print()
    console.print(Align.center(insights))

    # === CREDITS SEQUENCE ===
    if animate:
        console.print()
        continue_text = Text()
        continue_text.append("\n    press [ENTER] for fun facts & credits", style=Style(color=COLORS["dark"]))
        console.print(Align.center(continue_text))
        wait_for_keypress()
        console.clear()

        # Fun facts
        facts = get_fun_facts(stats)
        pad = " " * (console.width // 4)
        if facts:
            console.print(create_fun_facts_slide(facts, console.width, console.height))
            prompt_text = Text()
            prompt_text.append(f"{pad}press [ENTER] for the credits", style=Style(color=COLORS["dark"]))
            console.print(prompt_text)
            wait_for_keypress()
            console.clear()

        # Credits roll
        for frame in create_credits_roll(stats, console.width, console.height):
            console.print(frame)
            wait_for_keypress()
            console.clear()

    # Final footer
    console.print()
    footer = Text()
    footer.append("─" * 60 + "\n\n", style=Style(color=COLORS["dark"]))
    footer.append("Thanks for building with Claude ", style=Style(color=COLORS["gray"]))
    footer.append("✨\n\n", style=Style(color=COLORS["orange"]))
    footer.append("Created by ", style=Style(color=COLORS["gray"]))
    footer.append("Daniel Tollefsen", style=Style(color=COLORS["white"], bold=True, link="https://github.com/da-troll"))
    footer.append(" · ", style=Style(color=COLORS["dark"]))
    footer.append("github.com/da-troll/claude-wrapped", style=Style(color=COLORS["blue"], link="https://github.com/da-troll/claude-wrapped"))
    footer.append("\n")
    console.print(Align.center(footer))


if __name__ == "__main__":
    from .reader import load_all_messages
    from .stats import aggregate_stats

    print("Loading data...")
    messages = load_all_messages(year=2025)
    stats = aggregate_stats(messages, 2025)

    render_wrapped(stats)
