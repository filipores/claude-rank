from claude_rank.badge import generate_badge_svg, _text_width, _TIER_HEX


class TestTextWidth:
    def test_empty_string(self):
        assert _text_width("") == 0

    def test_single_narrow_char(self):
        assert _text_width("i") == 4

    def test_single_wide_char(self):
        assert _text_width("m") == 10

    def test_default_width_char(self):
        assert _text_width("a") == 7

    def test_mixed_string(self):
        result = _text_width("Lv.1")
        assert result > 0


class TestGenerateBadgeSvg:
    def test_contains_svg_tag(self):
        svg = generate_badge_svg(1, "Bronze", "bronze")
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_contains_label(self):
        svg = generate_badge_svg(1, "Bronze", "bronze")
        assert "claude-rank" in svg

    def test_contains_level_and_tier(self):
        svg = generate_badge_svg(12, "Gold", "gold")
        assert "Lv.12" in svg
        assert "Gold" in svg

    def test_tier_color_applied(self):
        svg = generate_badge_svg(1, "Test", "gold")
        assert "d4a017" in svg

    def test_unknown_color_falls_back_to_grey(self):
        svg = generate_badge_svg(1, "Test", "unknown_color")
        assert "6b7280" in svg

    def test_prestige_stars_in_svg(self):
        svg = generate_badge_svg(1, "Bronze", "bronze", prestige_count=2)
        assert "★★" in svg

    def test_no_prestige_no_stars(self):
        svg = generate_badge_svg(1, "Bronze", "bronze", prestige_count=0)
        assert "★" not in svg

    def test_tooltip_includes_xp(self):
        svg = generate_badge_svg(10, "Silver", "silver", total_xp=5000)
        assert "5,000 XP" in svg

    def test_tooltip_includes_prestige(self):
        svg = generate_badge_svg(1, "Bronze", "bronze", prestige_count=1)
        assert "Prestige 1" in svg

    def test_positive_dimensions(self):
        svg = generate_badge_svg(50, "Legendary Grandmaster", "legendary", prestige_count=5)
        assert 'width="' in svg
        assert 'height="20"' in svg

    def test_all_tier_colors_have_hex(self):
        for color_name, hex_val in _TIER_HEX.items():
            assert len(hex_val) == 6
            int(hex_val, 16)  # validates hex

    def test_valid_xml_structure(self):
        svg = generate_badge_svg(25, "Refactor Sage", "deep_purple", prestige_count=1, total_xp=100000)
        assert svg.startswith("<svg")
        assert svg.strip().endswith("</svg>")
