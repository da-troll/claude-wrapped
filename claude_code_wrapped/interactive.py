"""Interactive mode for Claude Code Wrapped using questionary prompts."""

import sys
from datetime import datetime
from pathlib import Path

import questionary
from questionary import Style
from rich.console import Console

# Custom styling to match the wrapped aesthetic
custom_style = Style([
    ('qmark', 'fg:#E67E22 bold'),       # Orange question mark
    ('question', 'bold'),                # Question text
    ('answer', 'fg:#9B59B6 bold'),      # Purple answer
    ('pointer', 'fg:#E67E22 bold'),     # Orange pointer
    ('highlighted', 'fg:#E67E22 bold'), # Orange highlighted choice
    ('selected', 'fg:#9B59B6'),         # Purple selected
    ('separator', 'fg:#7F8C8D'),        # Gray separator
    ('instruction', 'fg:#7F8C8D'),      # Gray instructions
])


def get_available_years() -> list[str]:
    """Get list of available years from the data."""
    # For now, generate last 3 years + current year
    current_year = datetime.now().year
    years = [str(year) for year in range(current_year - 2, current_year + 1)]
    years.reverse()  # Most recent first
    years.append("All time")
    return years


def interactive_mode() -> dict:
    """Run interactive mode to collect user preferences.

    Returns:
        Dictionary with user selections: {
            'year': str,
            'html': bool,
            'markdown': bool,
            'json': bool,
            'no_animate': bool,
            'output': str | None
        }
    """
    console = Console()

    # Welcome message
    console.print()
    console.print("  [bold #E67E22]Claude Code Wrapped[/bold #E67E22] [dim]- Interactive Mode[/dim]")
    console.print()

    try:
        # 1. Select time period
        year_choices = get_available_years()
        year_answer = questionary.select(
            "Select time period:",
            choices=year_choices,
            style=custom_style,
            use_shortcuts=True,
            use_arrow_keys=True,
        ).ask()

        if year_answer is None:  # User pressed Ctrl+C
            console.print("\n[yellow]Cancelled.[/yellow]")
            sys.exit(0)

        # Convert "All time" to "all" for internal use
        year = "all" if year_answer == "All time" else year_answer

        # 2. Select export format
        export_answer = questionary.select(
            "Export format:",
            choices=[
                "View in terminal only",
                "Export to HTML",
                "Export to Markdown",
                "Export to both HTML & Markdown",
                "Export to JSON",
            ],
            style=custom_style,
            default="View in terminal only",
        ).ask()

        if export_answer is None:
            console.print("\n[yellow]Cancelled.[/yellow]")
            sys.exit(0)

        # Parse export selections
        html = "HTML" in export_answer
        markdown = "Markdown" in export_answer
        json_export = "JSON" in export_answer

        # 3. Ask about animations (only if viewing in terminal)
        if export_answer == "View in terminal only" or html or markdown:
            animate_answer = questionary.confirm(
                "Show animations?",
                default=True,
                style=custom_style,
            ).ask()

            if animate_answer is None:
                console.print("\n[yellow]Cancelled.[/yellow]")
                sys.exit(0)

            no_animate = not animate_answer
        else:
            no_animate = True  # Skip animations for JSON-only export

        # 4. Custom filename (only if exporting)
        output_filename = None
        if html or markdown or json_export:
            use_custom = questionary.confirm(
                "Use custom filename?",
                default=False,
                style=custom_style,
            ).ask()

            if use_custom is None:
                console.print("\n[yellow]Cancelled.[/yellow]")
                sys.exit(0)

            if use_custom:
                output_filename = questionary.text(
                    "Enter filename (without extension):",
                    style=custom_style,
                    validate=lambda text: len(text) > 0 or "Filename cannot be empty",
                ).ask()

                if output_filename is None:
                    console.print("\n[yellow]Cancelled.[/yellow]")
                    sys.exit(0)

        console.print()  # Add spacing before execution

        return {
            'year': year,
            'html': html,
            'markdown': markdown,
            'json': json_export,
            'no_animate': no_animate,
            'output': output_filename,
        }

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Cancelled.[/yellow]")
        sys.exit(0)


def should_use_interactive_mode() -> bool:
    """Determine if we should use interactive mode.

    Interactive mode is used when:
    - No arguments provided at all (just `claude-wrapped`)
    - Only the --interactive flag is provided
    """
    # Check if only the script name is in argv (no arguments)
    if len(sys.argv) == 1:
        return True

    # Check if only --interactive flag is provided
    if len(sys.argv) == 2 and sys.argv[1] in ['--interactive', '-i']:
        return True

    return False
