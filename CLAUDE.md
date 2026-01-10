# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Code Wrapped is a terminal-based analytics tool that generates a "Spotify Wrapped" style year-in-review for Claude Code users. It reads local conversation history from `~/.claude/projects/` and presents statistics with dramatic reveals, contribution graphs, personality insights, and movie-style credits.

The project is dual-published:
- **Python package** (primary): Installable via `pip`, `uvx`, or `pipx`
- **npm package** (wrapper): A Node.js CLI wrapper (`bin/cli.js`) that automatically detects and runs the Python version

## Core Architecture

### Time Scope

**IMPORTANT**: Data is filtered by **calendar year**, not rolling period. Running `claude-code-wrapped 2025` loads all messages where `timestamp.year == 2025` (January 1 - December 31, or today if current year). It's NOT "last 365 days from today".

### Data Flow

1. **Reader** (`reader.py`): Parses JSONL conversation logs from `~/.claude/`

   **JSONL Record Format** (from `~/.claude/projects/*/*.jsonl`):
   ```python
   {
       "type": "user" | "assistant",
       "message": {
           "role": "user" | "assistant",
           "content": [...],  # List of content blocks or string
           "model": "claude-3-5-sonnet-20241022",  # Full model ID
           "usage": {
               "input_tokens": 1234,
               "output_tokens": 567,
               "cache_creation_input_tokens": 890,
               "cache_read_input_tokens": 123
           },
           "id": "msg_abc123"  # For deduplication
       },
       "timestamp": 1704067200000,  # milliseconds since epoch (UTC)
       "sessionId": "session_xyz",
       "cwd": "/path/to/project",
       "gitBranch": "main"
   }
   ```

   **Content Block Structure** (for tool extraction):
   ```python
   "content": [
       {"type": "text", "text": "Here's the code..."},
       {"type": "tool_use", "name": "Edit", "input": {...}},
       {"type": "tool_use", "name": "mcp__playwright__browser_click", "input": {...}}
   ]
   ```

   **Key parsing logic**:
   - Deduplicates by `message.id` when present (keeps last occurrence for final token counts)
   - For messages without ID (old history), deduplicates by `(timestamp, content_prefix)`
   - Converts UTC timestamps → local time via `datetime.fromtimestamp(ms / 1000)` for accurate hour-of-day
   - Extracts tool names from `tool_use` content blocks
   - Maps `cwd` → project name (takes last path component)

2. **Stats** (`stats.py`): Aggregates messages into comprehensive statistics

   **Critical calculations**:
   - **Active days**: Count of unique dates with `message_count > 0`
   - **Averages**: All calculated using active days, not total days
     ```python
     avg_messages_per_day = total_messages / active_days
     avg_cost_per_day = estimated_cost / active_days
     ```
   - **Streaks**: Consecutive days with activity. Current streak only meaningful for current year.
   - **Late night days**: Unique dates with activity between 0:00-5:00 (local time)
   - **MCP extraction**: `mcp__servername__toolname` → extract middle component as server name
   - **Model tracking**:
     - Display names simplified: `claude-3-5-sonnet-*` → `"Sonnet"`
     - Cost calculations use full model ID for accuracy

   **Per-session tracking** (for longest conversation):
   ```python
   session_messages[session_id] += 1
   session_tokens[session_id] += msg.usage.total_tokens
   session_first_time[session_id] = msg.timestamp  # First occurrence
   ```

3. **Pricing** (`pricing.py`): Cost calculations using official Anthropic pricing

   **Lookup priority**:
   1. Exact match in `MODEL_PRICING` dict (e.g., `"claude-3-5-sonnet-20241022"`)
   2. Family match in `MODEL_FAMILY_PRICING` (e.g., `"sonnet"` → conservative pricing)
   3. Partial match (e.g., `"sonnet"` in model name → use family pricing)

   **Cost formula**:
   ```python
   cost = (input / 1M) * input_price +
          (output / 1M) * output_price +
          (cache_create / 1M) * cache_write_price +  # 1.25x input
          (cache_read / 1M) * cache_read_price       # 0.1x input
   ```

4. **UI** (`ui.py`): Rich-based terminal presentation

   **Personality detection logic** (`determine_personality()` in ui.py:241):
   Evaluated in order, first match wins:
   ```python
   1. Night Owl: night_hours (22:00-6:00) > day_hours * 0.4
   2. Streak Master: longest_streak >= 14 days
   3. The Refactorer: top_tool == "Edit"
   4. Terminal Warrior: top_tool == "Bash"
   5. Empire Builder: total_projects >= 5
   6. Weekend Warrior: weekend_msgs > weekday_msgs * 0.5
   7. Perfectionist: Opus messages > Sonnet messages
   8. Default: "Dedicated Dev"
   ```

   **Fun facts generation** (`get_fun_facts()` in ui.py:267):
   Returns exactly 3 facts (all always shown if data exists):
   - Late night days count (midnight-5am activity)
   - Most active day (day of week + message count)
   - Longest streak

   **Credits structure** (`create_credits_frames()` in ui.py:400+):
   Multiple frames shown sequentially:
   1. **The Numbers**: Cost breakdown, token totals
   2. **Timeline**: Year, journey start, active days, peak hour
   3. **Averages**: Messages & cost per day/week/month
   4. **Longest Conversation**: Message count, tokens, date
   5. **Starring**: Top 3 models with message counts
   6. **Projects**: Top 5 projects with message counts
   7. **Tools**: Top 5 tools (if >500 tool calls)
   8. **MCP Servers**: Top 3 MCPs (if any)

   **Contribution graph** (`create_contribution_graph()` in ui.py:85):
   - Always shows full calendar year: Jan 1 → Dec 31 (or today if current year)
   - Color intensity based on message count quartiles (5 levels)
   - Organized by weeks, 7 rows (days of week)

5. **Main** (`main.py`): CLI entry point with argparse
   - Supports year filtering, animation toggling, JSON export
   - Default year: `datetime.now().year`

6. **Interactive** (`interactive.py`): User-friendly interactive mode

   **When activated**:
   - No CLI arguments provided (just `claude-code-wrapped`)
   - Explicit `--interactive` or `-i` flag used

   **Implementation details**:
   ```python
   # Detection
   def should_use_interactive_mode() -> bool:
       if len(sys.argv) == 1:  # No arguments
           return True
       if len(sys.argv) == 2 and sys.argv[1] in ['--interactive', '-i']:
           return True
       return False

   # Prompts
   def interactive_mode() -> dict:
       # Uses questionary for beautiful prompts
       # Returns: {'year': str, 'html': bool, 'markdown': bool,
       #          'json': bool, 'no_animate': bool, 'output': str | None}
   ```

   **Prompt flow**:
   1. **Time period selection** - Arrow keys to choose year or "All time"
   2. **Export format** - Terminal only, HTML, Markdown, both, or JSON
   3. **Animation preference** - Show dramatic reveals or skip (only if viewing in terminal)
   4. **Custom filename** - Optional custom output name (only if exporting)

   **Integration with main.py**:
   ```python
   if should_use_interactive_mode():
       selections = interactive_mode()
       args = argparse.Namespace(**selections)  # Convert to args object
   else:
       args = parser.parse_args()  # Traditional CLI parsing
   # Rest of code uses args object regardless of mode
   ```

   **Styling**:
   - Custom questionary theme matching wrapped aesthetic
   - Orange (#E67E22) for pointers and highlights
   - Purple (#9B59B6) for answers and selections
   - Gray (#7F8C8D) for instructions

### Key Design Decisions

**Deduplication Strategy**: Messages are deduplicated by `message_id` when available. For messages without IDs (like older history entries), deduplicate by `(timestamp, content_prefix)`. This handles streaming duplicates where the same message appears multiple times as tokens are generated.

**Timestamp Handling**: All timestamps are converted from UTC to local time during parsing. This ensures hour-of-day stats (like "most active hour" and "late night coding") reflect the user's actual local time, not UTC.

**Active Days Calculation**: All averages (messages/day, cost/day, etc.) are calculated using the count of days with activity, not total days in the year. This matches the behavior of tools like `ccusage` and provides more meaningful averages.

**MCP Server Extraction**: Tool names follow the pattern `mcp__servername__toolname`. The stats module extracts the server name (second component) to track which MCP servers are most used.

**Model Name Normalization**: For display purposes, full model IDs are simplified to `Opus`, `Sonnet`, or `Haiku`. However, cost calculations retain the full model ID to ensure accurate pricing for specific model versions.

## Common Development Commands

### Running locally
```bash
# Install dependencies with uv
uv sync

# Run from source with arguments
uv run python -m claude_code_wrapped
uv run python -m claude_code_wrapped 2024
uv run python -m claude_code_wrapped --no-animate
uv run python -m claude_code_wrapped --json

# Run individual modules for testing
uv run python -m claude_code_wrapped.reader
uv run python -m claude_code_wrapped.stats
uv run python -m claude_code_wrapped.pricing
```

### Using custom backup directories

If you have Claude Code backups in other locations, you can include them:

```bash
# Create .env file (copy from .env.example)
cp .env.example .env

# Edit .env and add your backup directories
# CLAUDE_BACKUP_DIRS=~/Dropbox/claude-backups/.claude,/mnt/external/old-data/.claude

# Run as normal - will automatically load from all directories
uv run python -m claude_code_wrapped
```

The tool will:
1. Load from `~/.claude/` (main directory)
2. Load from all directories listed in `CLAUDE_BACKUP_DIRS`
3. Deduplicate messages across all sources
4. Aggregate stats from all locations

### Testing the npm wrapper
```bash
# Test the Node.js wrapper locally
node bin/cli.js
npm start
```

### Building and publishing
```bash
# Build Python package
uv build

# Publish to PyPI (version in pyproject.toml)
uv publish

# Publish to npm (version in package.json)
npm publish

# IMPORTANT: Keep versions in sync between pyproject.toml and package.json
```

## Git Workflow

### Automated Code Review (Codex)

This repository uses OpenAI Codex for automated code reviews via GitHub Actions (`.github/workflows/codex-api-review.yml`).

**Automatic triggers:**
- PR opened
- PR reopened
- PR marked ready for review

**Manual trigger:**
- Comment `@codex review` on any PR

**Review focus:**
- Bugs & logic errors (P0/P1 severity only)
- Security vulnerabilities
- Performance concerns
- Best practices

### Branching Strategy

**Always create a feature branch for changes:**
```bash
# Create and switch to a new branch
git checkout -b feat/your-feature-name

# Or for fixes
git checkout -b fix/issue-description
```

**Branch naming conventions:**
- `feat/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring

### Pull Request Workflow

**1. Create a PR after pushing your branch:**
```bash
git push -u origin feat/your-feature-name

# Create PR using GitHub CLI
gh pr create --title "feat: description" --body "$(cat <<'EOF'
## Summary
- Bullet points describing changes

## Test plan
- [ ] How to verify the changes

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**2. Wait for Codex review:**
- The Codex bot will automatically review the PR
- Check the PR comments for the review

**3. Check PR comments before merging:**
```bash
# View PR with comments
gh pr view <PR_NUMBER> --comments

# Or view in browser
gh pr view <PR_NUMBER> --web
```

**4. Merge only if Codex review passes:**
```bash
# If no issues found, merge
gh pr merge <PR_NUMBER> --merge

# Then switch back to master and pull
git checkout master && git pull
```

### Version Management

**CRITICAL**: Versions must be sequential with no gaps (v1.0.0, v1.0.1, v1.0.2, etc.)

**Version files to update (BOTH must match):**
- `pyproject.toml` - line 3: `version = "X.Y.Z"`
- `package.json` - line 3: `"version": "X.Y.Z"`

**Bumping version:**
```bash
# 1. Update version in both files
# 2. Commit the change
git add pyproject.toml package.json
git commit -m "Bump version to X.Y.Z"
git push
```

### Tags and Releases

**After merging version bumps, create tag and release:**
```bash
# Create tag at the version bump commit
git tag vX.Y.Z <commit-sha>

# Or tag current HEAD
git tag vX.Y.Z

# Push tag to remote
git push origin vX.Y.Z

# Create GitHub release
gh release create vX.Y.Z --title "vX.Y.Z" --notes "Version X.Y.Z"
```

**Verify releases:**
```bash
gh release list
```

**If you need to fix tag/release issues:**
```bash
# Delete release first
gh release delete vX.Y.Z --yes

# Delete remote tag
git push origin --delete vX.Y.Z

# Delete local tag
git tag -d vX.Y.Z

# Recreate correctly
git tag vX.Y.Z <correct-commit-sha>
git push origin vX.Y.Z
gh release create vX.Y.Z --title "vX.Y.Z" --notes "Version X.Y.Z"
```

### Complete Release Workflow Example

```bash
# 1. Create feature branch
git checkout -b feat/new-feature

# 2. Make changes and commit
git add .
git commit -m "feat: add new feature"

# 3. Push and create PR
git push -u origin feat/new-feature
gh pr create --title "feat: add new feature" --body "Description here"

# 4. Wait for Codex review, then check comments
gh pr view 1 --comments

# 5. If review passes, merge
gh pr merge 1 --merge

# 6. Switch to master and pull
git checkout master && git pull

# 7. Bump version (edit pyproject.toml and package.json)
git add pyproject.toml package.json
git commit -m "Bump version to 1.0.5"
git push

# 8. Create tag and release
git tag v1.0.5
git push origin v1.0.5
gh release create v1.0.5 --title "v1.0.5" --notes "- Add new feature"

# 9. Publish to package registries
uv build && uv publish
npm publish
```

## File Structure

- `claude_code_wrapped/main.py` - CLI entry point, argument parsing, orchestration
- `claude_code_wrapped/interactive.py` - Interactive mode with questionary prompts
- `claude_code_wrapped/reader.py` - JSONL parsing, message extraction, deduplication
- `claude_code_wrapped/stats.py` - Statistical aggregation, streak calculation, model tracking
- `claude_code_wrapped/pricing.py` - Model pricing data, cost calculation
- `claude_code_wrapped/ui.py` - Rich-based terminal UI, contribution graphs, credits
- `claude_code_wrapped/exporters/` - Export modules for HTML and Markdown
- `bin/cli.js` - Node.js wrapper that detects and runs Python version
- `pyproject.toml` - Python package metadata, uses hatchling build backend
- `package.json` - npm package metadata, points to `bin/cli.js`

## Important Implementation Notes

### Adding New Statistics

When adding new stats to `WrappedStats`:
1. Add field to `WrappedStats` dataclass in `stats.py` (with default value via `field()` if needed)
2. Calculate in `aggregate_stats()` function, typically in the message loop or finalization section
3. For monthly/model-specific breakdowns, use the existing tracking dicts:
   - `monthly_tokens` for per-month data
   - `stats.model_token_usage` for per-model tracking
4. Export in JSON output in `main.py` line 70+ (if relevant for `--json` flag)
5. Add UI presentation:
   - Dramatic reveal: Use `create_dramatic_stat()` in `render_wrapped()`
   - Dashboard panel: Add to stats panels around ui.py:320
   - Credits frame: Add new frame in `create_credits_frames()`

**Example - Adding "weekend warrior" stat**:
```python
# 1. stats.py - Add field
@dataclass
class WrappedStats:
    weekend_messages: int = 0

# 2. stats.py - Calculate in aggregate_stats()
if msg.timestamp:
    if msg.timestamp.weekday() in [5, 6]:  # Sat, Sun
        stats.weekend_messages += 1

# 3. main.py - Export in JSON
output = {
    ...
    "weekend_messages": stats.weekend_messages,
}

# 4. ui.py - Add dramatic reveal
console.print(create_dramatic_stat(
    f"{stats.weekend_messages:,}",
    "WEEKEND MESSAGES",
    color=COLORS["purple"]
))
wait_for_keypress()
```

### Updating Model Pricing

Model prices are in `pricing.py`:

**Adding a new model**:
```python
MODEL_PRICING: dict[str, ModelPricing] = {
    "claude-opus-5-20260101": ModelPricing(
        input_cost=20.0,        # USD per 1M tokens
        output_cost=100.0,
        cache_write_cost=25.0,  # Always 1.25x input
        cache_read_cost=2.0     # Always 0.1x input
    ),
}
```

**IMPORTANT**: Cache multipliers are fixed by Anthropic:
- Cache write = 1.25x base input cost
- Cache read = 0.1x base input cost

**Testing pricing**:
```bash
uv run python -m claude_code_wrapped.pricing
```

### Adding a New Personality Type

Personalities are evaluated in order (first match wins) in `ui.py:241`.

**To add new personality**:
1. Choose threshold criteria using available stats
2. Insert in priority order (earlier = higher priority)
3. Provide emoji, title, description

**Example - Adding "API Master"**:
```python
def determine_personality(stats: WrappedStats) -> dict:
    night_hours = sum(stats.hourly_distribution[22:]) + sum(stats.hourly_distribution[:6])
    day_hours = sum(stats.hourly_distribution[6:22])
    top_tool = stats.top_tools[0][0] if stats.top_tools else None

    # Add this before "Terminal Warrior" to give it priority
    if stats.tool_calls.get("WebFetch", 0) > 50:
        return {"emoji": "🌐", "title": "API Master", "description": "You speak HTTP fluently."}

    # ... rest of existing logic
```

### Modifying Time Calculations

Time-based stats use **local time** converted during parsing in `reader.py:57-74`:

**Critical**: Timestamps are converted from UTC to local ONCE during parsing:
```python
# reader.py - ALREADY converts to local
utc_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
local_dt = utc_dt.astimezone().replace(tzinfo=None)  # Local time, no TZ info
```

**In stats.py - timestamps are ALREADY LOCAL**:
```python
# ✅ CORRECT - hour is already in local time
stats.hourly_distribution[msg.timestamp.hour] += 1

# ❌ WRONG - don't convert again
stats.hourly_distribution[msg.timestamp.astimezone().hour] += 1
```

**Time boundaries**:
- Late night: `0 <= hour < 5` (midnight to 5am local)
- Night hours for personality: `hour >= 22 or hour < 6`
- Weekday: `0=Monday, 6=Sunday` (use `datetime.weekday()`)

### Adding Custom Data Sources

To include backup directories or archived data:

**Via environment variable**:
1. Create `.env` file: `cp .env.example .env`
2. Set `CLAUDE_BACKUP_DIRS` to comma-separated paths:
   ```bash
   CLAUDE_BACKUP_DIRS=~/Dropbox/claude-backups/.claude,/mnt/old-data/.claude,~/flat-exports
   ```
3. Run normally - automatically loads from all directories

**Supported directory structures**:

The tool auto-detects THREE structures:

1. **Standard `~/.claude` structure** (has `projects/` subdirectory):
   ```
   backup-dir/
   ├── projects/
   │   └── -Users-you-code-project/
   │       └── session-uuid.jsonl
   └── history.jsonl (optional)
   ```
   Uses `iter_project_sessions()` to traverse `projects/` subdirectory.

2. **Projects folder itself** (subdirectories with `*.jsonl` files):
   ```
   projects-dir/
   ├── -Users-you-code-project1/
   │   └── session.jsonl
   └── -Users-you-code-project2/
       └── session.jsonl
   ```
   Uses `iter_projects_folder()` - same as #1 but without looking for `projects/` subdir.
   Useful for: `~/.claude/backups/projects`, exported project folders.

3. **Flat structure** (`*.jsonl` files directly in directory):
   ```
   backup-dir/
   ├── session1.jsonl
   ├── session2.jsonl
   └── session3.jsonl
   ```
   Uses `iter_flat_sessions()` to read files directly from directory.
   Uses directory name as project name.

**Detection logic** (reader.py:299-330):
```python
has_projects_subdir = (scan_dir / "projects").exists()
has_project_folders = any(d.is_dir() and any(d.glob("*.jsonl")) for d in scan_dir.iterdir() if d.is_dir())
has_jsonl_files = any(scan_dir.glob("*.jsonl"))

if has_projects_subdir:
    # Structure 1: Standard
elif has_project_folders:
    # Structure 2: Projects folder
elif has_jsonl_files:
    # Structure 3: Flat
```

**Programmatically**:
```python
from pathlib import Path
from claude_code_wrapped.reader import load_all_messages

# Load from main dir only
messages = load_all_messages(include_custom_dirs=False)

# Load from specific custom dir (auto-detects structure)
messages = load_all_messages(claude_dir=Path("/path/to/backup"))
```

**How it works**:
- `get_custom_claude_dirs()` reads `CLAUDE_BACKUP_DIRS` env var
- Splits on comma, expands `~`, validates each path exists
- `load_all_messages()` iterates over main + custom dirs **in order**
- For each dir, detects structure and uses appropriate iterator
- Deduplicates messages by `message_id` across all sources
- **CRITICAL**: If same message appears in multiple sources, **keeps LAST occurrence**

**Deduplication details** (reader.py:332-351):
```python
seen_ids: dict[str, Message] = {}
for msg in all_messages:  # Scanned in order: main, then custom dirs
    if msg.message_id:
        seen_ids[msg.message_id] = msg  # Overwrites previous!
unique_messages.extend(seen_ids.values())
```

**Order precedence**:
1. Main `~/.claude/` directory (scanned first, lowest priority)
2. Custom dirs in `CLAUDE_BACKUP_DIRS` order (later = higher priority)

**Example** - Pre-compaction backups should be LAST:
```bash
# WRONG: Pre-compaction backups get overwritten by main dir
CLAUDE_BACKUP_DIRS=~/.claude/backups/projects,~/flat-exports

# CORRECT: Pre-compaction backups override main dir
CLAUDE_BACKUP_DIRS=~/flat-exports,~/.claude/backups/projects
```

This ensures the most complete/authoritative versions are kept.

### Testing with Real Data

The tool reads from `~/.claude/` by default.

**Option 1: Use your own data** (recommended):
```bash
uv run python -m claude_code_wrapped 2025
```

**Option 2: Test with backups**:
```bash
# Create .env with backup directories
CLAUDE_BACKUP_DIRS=~/old-claude-backup/.claude uv run python -m claude_code_wrapped
```

**Option 3: Create test JSONL files**:
1. Create `test_claude/.claude/projects/test-project/session.jsonl`
2. Add records matching schema in reader.py:88-131
3. Modify `get_claude_dir()` to return test path OR:
   ```python
   messages = load_all_messages(claude_dir=Path("test_claude/.claude"))
   ```

**Option 4: Test individual modules**:
```bash
# Test reader
uv run python -m claude_code_wrapped.reader

# Test stats
uv run python -m claude_code_wrapped.stats

# Test pricing
uv run python -m claude_code_wrapped.pricing
```

## Common Gotchas & Edge Cases

### Version Synchronization
**CRITICAL**: `pyproject.toml` and `package.json` versions MUST match.

When bumping version:
```bash
# Update both files to same version
# pyproject.toml line 3: version = "0.1.12"
# package.json line 3: "version": "0.1.12"

# Build and publish
uv build
uv publish
npm publish
```

### Deduplication Edge Cases

**Streaming messages**: Same message appears multiple times with increasing content as tokens stream in. The last occurrence has final token counts, so we keep it:
```python
# Keep LAST occurrence (has final counts)
seen_ids[msg.message_id] = msg  # Overwrites previous
```

**History file duplicates**: Old messages from `history.jsonl` may duplicate session file messages but lack `message_id`. Deduplicate by timestamp + content prefix.

### Timezone Handling

**Common mistake**: Converting timestamps twice
```python
# ❌ WRONG
msg.timestamp.astimezone()  # Already converted in reader!

# ✅ CORRECT
msg.timestamp.hour  # Already local time
```

**Testing across timezones**: If test data uses different timezone than your machine, hour-of-day stats will reflect YOUR local time (by design).

### Active Days vs Total Days

**Important**: All averages use active days, not calendar days in year.

For a user with 50 active days in 2025:
```python
avg_per_day = total_messages / 50  # NOT total_messages / 365
```

This matches `ccusage` behavior and gives meaningful numbers.

### Model ID Matching

**Full vs simplified names**:
- Display: `"Sonnet"` (simplified for UI)
- Pricing: `"claude-3-5-sonnet-20241022"` (full ID for accurate cost)

If adding new model family (e.g., "Ultra"), update BOTH:
1. `stats.py` model name simplification logic (line 240)
2. `pricing.py` MODEL_FAMILY_PRICING dict

### Contribution Graph Color Calculation

Graph uses **quartiles** not linear scaling:
```python
# Based on max message count in daily_stats
quartile_1 = max_count * 0.25
quartile_2 = max_count * 0.50
# etc.
```

So days with similar message counts may have different colors based on the distribution.

### Tool Name Extraction

Tools are ONLY counted if they appear in `content` blocks of type `tool_use`:
```python
# Counted
{"type": "tool_use", "name": "Edit", "input": {...}}

# NOT counted (text reference, not actual tool use)
{"type": "text", "text": "I'll use the Edit tool"}
```

### NPM Wrapper Behavior

`bin/cli.js` tries executors in order:
1. `uvx` (recommended, no install needed)
2. `pipx run` (isolated environment)
3. `python3 -m` (if package installed globally)

If user has multiple Python versions or environments, the wrapper might find a different installation than expected.

## Privacy Guarantees

This tool is **completely local**:
- No network requests (no API keys, no analytics, no telemetry)
- Only reads from `~/.claude/` directory
- Shows aggregated stats, not conversation content
- Safe to run on sensitive codebases
