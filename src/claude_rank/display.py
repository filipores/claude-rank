"""Rich terminal display for claude-rank."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Map tier colors from levels.py to valid Rich color names
_COLOR_MAP: dict[str, str] = {
    "bronze": "dark_orange3",
    "silver": "grey70",
    "gold": "gold1",
    "teal": "deep_sky_blue1",
    "diamond": "cyan",
    "purple": "purple",
    "deep_purple": "dark_violet",
    "crimson": "red1",
    "amber": "gold1",
    "legendary": "orange_red1",
}


def _safe_color(color: str) -> str:
    """Map a tier color to a valid Rich color name."""
    return _COLOR_MAP.get(color, color)


def format_number(n: int) -> str:
    """Format large numbers: 421543 -> '421.5K', 1200 -> '1,200', 1234567 -> '1.2M'."""
    if n >= 1_000_000:
        value = n / 1_000_000
        if value >= 100:
            return f"{value:.0f}M"
        if value >= 10:
            return f"{value:.1f}M"
        return f"{value:.1f}M"
    if n >= 10_000:
        value = n / 1_000
        if value >= 1000:
            return f"{value:.0f}K"
        return f"{value:.1f}K"
    return f"{n:,}"


def _xp_bar(current: int, total: int, width: int = 20) -> str:
    """Render an XP progress bar as text: [████████░░░░░░░░░░░░]."""
    if total <= 0:
        return "[" + "\u2588" * width + "]"
    ratio = min(current / total, 1.0)
    filled = int(ratio * width)
    empty = width - filled
    return "[" + "\u2588" * filled + "\u2591" * empty + "]"


def print_dashboard(data: dict) -> None:
    """Print the main dashboard with level, XP, streak, and achievements."""
    level = data.get("level", 1)
    total_xp = data.get("total_xp", 0)
    xp_in_level = data.get("xp_in_level", 0)
    xp_for_next = data.get("xp_for_next", 0)
    tier_name = data.get("tier_name", "Bronze")
    tier_color = _safe_color(data.get("tier_color", "bronze"))
    current_streak = data.get("current_streak", 0)
    freeze_count = data.get("freeze_count", 0)
    total_sessions = data.get("total_sessions", 0)
    total_messages = data.get("total_messages", 0)
    recent_achievements = data.get("recent_achievements", [])
    closest_achievements = data.get("closest_achievements", [])
    member_since = data.get("member_since", "unknown")

    prestige_count = data.get("prestige_count", 0)
    from claude_rank.levels import prestige_stars
    stars = prestige_stars(prestige_count)
    stars_suffix = f"  {stars}" if stars else ""

    lines: list[str] = []

    # Title
    lines.append("")
    lines.append(f"  [bold {tier_color}]Level {level} - {tier_name}{stars_suffix}[/]")

    # XP bar
    bar = _xp_bar(xp_in_level, xp_for_next)
    if xp_for_next > 0:
        lines.append(f"  {bar} {format_number(xp_in_level)}/{format_number(xp_for_next)} XP")
    else:
        lines.append(f"  {bar} MAX LEVEL")
    lines.append(f"  Total: [bold]{format_number(total_xp)}[/] XP")

    # Stats row
    lines.append("")
    lines.append(
        f"  \U0001f525 Streak: {current_streak} days  |  "
        f"\u2744\ufe0f  Freezes: {freeze_count}/3"
    )
    lines.append(
        f"  \U0001f4ca Sessions: {format_number(total_sessions)}  |  "
        f"\U0001f4ac Messages: {format_number(total_messages)}"
    )

    # Recent achievements
    if recent_achievements:
        lines.append("")
        lines.append("  [bold]Recent Achievements:[/]")
        for ach in recent_achievements[:3]:
            lines.append(f"  \u2705 {ach['name']} ({ach.get('description', '')})")

    # Closest achievements
    if closest_achievements:
        lines.append("")
        lines.append("  [bold]Almost There:[/]")
        for ach in closest_achievements[:3]:
            progress = ach.get("progress", 0.0)
            current_val = ach.get("current", 0)
            target_val = ach.get("target", 0)
            pct = int(progress * 100)
            lines.append(
                f"  \u23f3 {ach['name']}: "
                f"{format_number(current_val)}/{format_number(target_val)} ({pct}%)"
            )

    lines.append("")
    lines.append(f"  Member since: {member_since}")
    lines.append("")

    content = "\n".join(lines)
    panel = Panel(
        content,
        title="[bold]CLAUDE RANK[/]",
        box=box.ROUNDED,
        border_style=tier_color,
        width=50,
    )
    console.print(panel)


def print_stats(data: dict) -> None:
    """Print detailed stats as a table."""
    tier_color = _safe_color(data.get("tier_color", "bronze"))

    table = Table(
        title="Detailed Stats",
        box=box.ROUNDED,
        border_style=tier_color,
        show_header=True,
        header_style="bold",
    )
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    # Basic stats
    table.add_row("Total Sessions", format_number(data.get("total_sessions", 0)))
    table.add_row("Total Messages", format_number(data.get("total_messages", 0)))
    table.add_row("Total Tool Calls", format_number(data.get("total_tool_calls", 0)))

    # Streak
    table.add_row("Current Streak", f"{data.get('current_streak', 0)} days")
    table.add_row("Longest Streak", f"{data.get('longest_streak', 0)} days")

    # XP
    table.add_row("Total XP", format_number(data.get("total_xp", 0)))
    table.add_row("Level", str(data.get("level", 1)))
    table.add_row("Tier", data.get("tier_name", "Bronze"))

    # Projects
    projects = data.get("projects", [])
    table.add_row("Unique Projects", str(len(projects)))

    # Longest session
    table.add_row("Longest Session", f"{data.get('longest_session_messages', 0)} messages")

    # Most active hour
    hour_counts = data.get("hour_counts", [0] * 24)
    if any(h > 0 for h in hour_counts):
        peak_hour = hour_counts.index(max(hour_counts))
        table.add_row("Most Active Hour", f"{peak_hour:02d}:00")

    # Model usage
    model_usage = data.get("model_usage", {})
    if model_usage:
        table.add_section()
        table.add_row("[bold]Model Usage[/]", "")
        for model, tokens in sorted(model_usage.items(), key=lambda x: x[1], reverse=True):
            table.add_row(f"  {model}", format_number(tokens))

    # Top tool calls
    tool_usage = data.get("tool_usage", {})
    if tool_usage:
        table.add_section()
        table.add_row("[bold]Top Tools (30d)[/]", "")
        for tool, count in sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:10]:
            table.add_row(f"  {tool}", format_number(count))

    console.print(table)


def print_achievements(achievements: list[dict]) -> None:
    """Print all achievements with progress bars.

    Each dict has: id, name, description, rarity, rarity_color, progress (0.0-1.0),
    unlocked (bool), unlocked_at (str|None), current (int), target (int).
    """
    rarity_colors = {
        "common": "white",
        "uncommon": "green",
        "rare": "blue",
        "epic": "magenta",
        "legendary": "yellow",
    }

    # Split into unlocked and locked
    unlocked = [a for a in achievements if a.get("unlocked")]
    locked = [a for a in achievements if not a.get("unlocked")]

    # Sort: unlocked by date desc, locked by progress desc
    unlocked.sort(key=lambda a: a.get("unlocked_at", ""), reverse=True)
    locked.sort(key=lambda a: a.get("progress", 0), reverse=True)

    table = Table(
        title="Achievements",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
    )
    table.add_column("", width=2)
    table.add_column("Achievement", min_width=20)
    table.add_column("Rarity", width=10)
    table.add_column("Progress", min_width=18)
    table.add_column("Date", width=12)

    for ach in unlocked + locked:
        icon = "\u2705" if ach.get("unlocked") else "\u23f3"
        rarity = ach.get("rarity", "common")
        color = rarity_colors.get(rarity, "white")

        name_text = f"[bold]{ach['name']}[/]\n{ach.get('description', '')}"
        rarity_text = f"[{color}]{rarity.upper()}[/{color}]"

        progress = ach.get("progress", 0.0)
        current_val = ach.get("current", 0)
        target_val = ach.get("target", 0)
        pct = int(progress * 100)
        bar = _xp_bar(current_val, target_val, width=10)
        progress_text = f"{bar} {pct}%"

        date_text = ach.get("unlocked_at", "") or ""

        table.add_row(icon, name_text, rarity_text, progress_text, date_text)

    console.print(table)


def print_sync_result(stats: dict) -> None:
    """Print sync results summary."""
    lines: list[str] = []
    lines.append("")
    lines.append(f"  Days synced:     {stats.get('days_synced', 0)}")
    lines.append(f"  Total XP:        {format_number(stats.get('total_xp', 0))}")
    lines.append(f"  Level:           {stats.get('level', 1)}")
    lines.append(f"  Tier:            {stats.get('tier_name', 'Bronze')}")

    new_achievements = stats.get("new_achievements", [])
    lines.append(f"  Achievements:    {stats.get('total_achievements_unlocked', 0)} unlocked")
    if new_achievements:
        lines.append("")
        lines.append("  [bold]New Achievements:[/]")
        for name in new_achievements:
            lines.append(f"  \U0001f3c6 {name}")

    lines.append("")

    content = "\n".join(lines)
    panel = Panel(
        content,
        title="[bold]Sync Complete[/]",
        box=box.ROUNDED,
        border_style="green",
        width=50,
    )
    console.print(panel)


def print_no_data_message() -> None:
    """Print message when no data is available."""
    panel = Panel(
        "\n  No data found. Run [bold]claude-rank sync[/] first to parse your Claude Code data.\n",
        title="[bold]CLAUDE RANK[/]",
        box=box.ROUNDED,
        border_style="grey50",
        width=50,
    )
    console.print(panel)


def print_prestige_result(result: dict) -> None:
    """Print prestige success message."""
    lines: list[str] = []
    lines.append("")
    lines.append(f"  [bold yellow]PRESTIGE {result.get('prestige_count', 1)} ACHIEVED![/]")
    lines.append("")
    lines.append(f"  Stars: {result.get('stars', '')}")
    lines.append(f"  New Level: {result.get('new_level', 1)}")
    lines.append(f"  Tier: {result.get('tier_name', 'Bronze')}")
    lines.append(f"  Historical XP: {format_number(result.get('historical_total_xp', 0))}")
    lines.append("")

    content = "\n".join(lines)
    panel = Panel(
        content,
        title="[bold]PRESTIGE[/]",
        box=box.ROUNDED,
        border_style="yellow",
        width=50,
    )
    console.print(panel)


def print_prestige_not_ready(result: dict) -> None:
    """Print message when prestige requirements are not met."""
    lines: list[str] = []
    lines.append("")
    lines.append(f"  Current Level: {result.get('current_level', 1)}")
    lines.append(f"  Max Level: {result.get('max_level', 50)}")
    lines.append(f"  XP Needed: {format_number(result.get('xp_needed', 0))}")
    lines.append("")
    lines.append("  Reach max level to prestige and earn a star badge.")
    lines.append("")

    content = "\n".join(lines)
    panel = Panel(
        content,
        title="[bold]Not Ready to Prestige[/]",
        box=box.ROUNDED,
        border_style="grey50",
        width=50,
    )
    console.print(panel)


def print_badge_result(result: dict) -> None:
    """Print badge generation result."""
    lines: list[str] = []
    lines.append("")
    lines.append(f"  Badge saved to: [bold]{result.get('output', '')}[/]")
    lines.append(f"  Level {result.get('level', 1)} - {result.get('tier_name', 'Bronze')}")
    lines.append("")
    lines.append("  Add to your README:")
    lines.append("  ![Claude Rank](claude-rank-badge.svg)")
    lines.append("")

    content = "\n".join(lines)
    panel = Panel(
        content,
        title="[bold]Badge Generated[/]",
        box=box.ROUNDED,
        border_style="green",
        width=50,
    )
    console.print(panel)


def print_wrapped(data: dict) -> None:
    """Print wrapped summary with multiple panels."""
    period = data.get("period", "month")
    period_start = data.get("period_start", "")
    period_end = data.get("period_end", "")

    # Core Numbers panel
    core_lines: list[str] = []
    core_lines.append("")
    core_lines.append(f"  XP Earned:    {format_number(data.get('total_xp_earned', 0))}")
    core_lines.append(f"  Sessions:     {format_number(data.get('total_sessions', 0))}")
    core_lines.append(f"  Messages:     {format_number(data.get('total_messages', 0))}")
    core_lines.append(f"  Tool Calls:   {format_number(data.get('total_tool_calls', 0))}")
    core_lines.append(f"  Active Days:  {data.get('active_days', 0)}/{data.get('total_days', 0)}")
    core_lines.append(f"  Avg XP/Day:   {format_number(data.get('avg_xp_per_day', 0))}")
    core_lines.append("")

    core_panel = Panel(
        "\n".join(core_lines),
        title=f"[bold]Core Numbers ({period}: {period_start} to {period_end})[/]",
        box=box.ROUNDED,
        border_style="yellow",
        width=50,
    )
    console.print(core_panel)

    # Highlights panel
    hl_lines: list[str] = []
    hl_lines.append("")
    busiest_day = data.get("busiest_day")
    if busiest_day:
        hl_lines.append(f"  Busiest Day:  {busiest_day} ({format_number(data.get('busiest_day_xp', 0))} XP)")
    busiest_hour = data.get("busiest_hour")
    if busiest_hour is not None:
        hl_lines.append(f"  Peak Hour:    {busiest_hour:02d}:00")
    hl_lines.append(f"  Best Streak:  {data.get('period_streak', 0)} days")
    hl_lines.append(f"  Projects:     {data.get('projects_count', 0)}")
    hl_lines.append("")

    hl_panel = Panel(
        "\n".join(hl_lines),
        title="[bold]Highlights[/]",
        box=box.ROUNDED,
        border_style="cyan",
        width=50,
    )
    console.print(hl_panel)

    # Top Tools panel
    top_tools = data.get("top_tools", [])
    if top_tools:
        tool_lines: list[str] = []
        tool_lines.append("")
        max_count = top_tools[0][1] if top_tools else 1
        for name, count in top_tools:
            bar = _xp_bar(count, max_count, width=15)
            tool_lines.append(f"  {name:<12s} {bar} {format_number(count)}")
        tool_lines.append("")

        tool_panel = Panel(
            "\n".join(tool_lines),
            title="[bold]Top Tools[/]",
            box=box.ROUNDED,
            border_style="blue",
            width=50,
        )
        console.print(tool_panel)

    # All-Time panel
    at_lines: list[str] = []
    at_lines.append("")
    at_lines.append(f"  Level:          {data.get('current_level', 1)}")
    at_lines.append(f"  Lifetime XP:    {format_number(data.get('lifetime_xp', 0))}")
    at_lines.append(f"  Longest Streak: {data.get('longest_streak', 0)} days")
    at_lines.append(f"  Member Since:   {data.get('member_since', 'unknown')}")
    at_lines.append("")

    at_panel = Panel(
        "\n".join(at_lines),
        title="[bold]All-Time[/]",
        box=box.ROUNDED,
        border_style="grey50",
        width=50,
    )
    console.print(at_panel)
