"""SVG badge generation for claude-rank.

Generates a shields.io-style flat badge showing level, tier, and prestige stars.
Pure functions, no side effects, no external dependencies.
"""

from __future__ import annotations

# Tier color name -> hex color for SVG
_TIER_HEX: dict[str, str] = {
    "grey": "6b7280",
    "green": "16a34a",
    "blue": "2563eb",
    "purple": "7c3aed",
    "deep_purple": "5b21b6",
    "gold1": "d97706",
    "grey89": "9ca3af",
    "cyan": "0891b2",
    "magenta": "a21caf",
    "yellow": "ca8a04",
}

_LABEL = "claude-rank"
_LABEL_BG = "555555"
_FONT_SIZE = 11
_FONT_FAMILY = "DejaVu Sans,Verdana,Geneva,sans-serif"


def _text_width(text: str) -> int:
    """Estimate pixel width of text at 11px DejaVu Sans."""
    widths = {
        "f": 4, "i": 4, "j": 4, "l": 4, "r": 4, "t": 5,
        "m": 10, "w": 9, "W": 10, "M": 10,
        " ": 4, ".": 4, ",": 4, ":": 4, "/": 5,
    }
    return sum(widths.get(ch, 7) for ch in text)


def generate_badge_svg(
    level: int,
    tier_name: str,
    tier_color: str,
    prestige_count: int = 0,
    total_xp: int = 0,
) -> str:
    """Generate a shields.io flat-style SVG badge string.

    Layout: [claude-rank | Lv.12 Bug Slayer ★]
    """
    stars = "★" * prestige_count if prestige_count > 0 else ""
    value_text = f"Lv.{level} {tier_name}"
    if stars:
        value_text = f"{value_text} {stars}"

    right_hex = _TIER_HEX.get(tier_color, "6b7280")

    label_text_w = _text_width(_LABEL)
    value_text_w = _text_width(value_text)

    pad = 10
    label_w = label_text_w + pad * 2
    value_w = value_text_w + pad * 2
    total_w = label_w + value_w
    height = 20

    label_cx = label_w // 2
    value_cx = label_w + value_w // 2

    tooltip = f"claude-rank: Level {level} {tier_name}"
    if prestige_count > 0:
        tooltip += f" (Prestige {prestige_count})"
    if total_xp > 0:
        tooltip += f" - {total_xp:,} XP"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{total_w}" height="{height}" role="img" aria-label="{tooltip}">
  <title>{tooltip}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_w}" height="{height}" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_w}" height="{height}" fill="#{_LABEL_BG}"/>
    <rect x="{label_w}" width="{value_w}" height="{height}" fill="#{right_hex}"/>
    <rect width="{total_w}" height="{height}" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="{_FONT_FAMILY}" text-rendering="geometricPrecision" font-size="{_FONT_SIZE}">
    <text aria-hidden="true" x="{label_cx}.5" y="15" fill="#010101" fill-opacity=".3">{_LABEL}</text>
    <text x="{label_cx}.5" y="14">{_LABEL}</text>
    <text aria-hidden="true" x="{value_cx}.5" y="15" fill="#010101" fill-opacity=".3">{value_text}</text>
    <text x="{value_cx}.5" y="14">{value_text}</text>
  </g>
</svg>
'''
    return svg
