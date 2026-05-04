"""Tests for pattern engine components."""

import pytest
from by_nly.models.enums import Platform
from by_nly.generator.pattern_engine import (
    expand_pattern,
    pattern_size,
    get_charset,
    get_patterns,
    list_pattern_types,
    custom_pattern_to_template,
    parse_custom_pattern,
)


class TestCharsets:
    def test_get_charset(self):
        for p in Platform:
            cs = get_charset(p)
            assert "l" in cs
            assert "d" in cs


class TestPatternExpansion:
    def test_expand_ll(self):
        charset = get_charset(Platform.TELEGRAM)
        result = expand_pattern("ll", charset)
        assert len(result) == 26 * 26  # 676

    def test_expand_ld(self):
        charset = get_charset(Platform.TELEGRAM)
        result = expand_pattern("ld", charset)
        assert len(result) == 26 * 10  # 260

    def test_expand_l_l(self):
        charset = get_charset(Platform.TELEGRAM)
        result = expand_pattern("l_l", charset)
        assert len(result) == 26 * 26  # 676

    def test_expand_ll_dot_l(self):
        charset = get_charset(Platform.TELLONYM)
        result = expand_pattern("l.l", charset)
        assert len(result) == 26 * 26

    def test_pattern_size(self):
        charset = get_charset(Platform.TELEGRAM)
        assert pattern_size("lll", charset) == 26**3
        assert pattern_size("lld", charset) == 26 * 26 * 10

    def test_snapchat_hyphen(self):
        charset = get_charset(Platform.SNAPCHAT)
        result = expand_pattern("l-l", charset)
        assert len(result) == 26 * 26
        assert "a-b" in result


class TestTemplates:
    def test_semi2(self):
        patterns = get_patterns("semi2")
        assert len(patterns) > 0
        assert "ll" in patterns

    def test_semi3(self):
        patterns = get_patterns("semi3")
        assert len(patterns) > 0
        assert "lll" in patterns

    def test_quad(self):
        patterns = get_patterns("quad")
        assert len(patterns) > 0
        assert "llll" in patterns

    def test_full(self):
        patterns = get_patterns("full")
        assert len(patterns) > len(get_patterns("semi2"))

    def test_list_types(self):
        types = list_pattern_types()
        assert "semi2" in types
        assert "semi3" in types
        assert "quad" in types
        assert "full" in types

    def test_invalid_type(self):
        with pytest.raises(ValueError):
            get_patterns("nonexistent")


class TestCustomPatterns:
    def test_parse_simple(self):
        tokens = parse_custom_pattern("custom:ll.l")
        assert tokens == ["l", "l", ".", "l"]

    def test_parse_with_numbers(self):
        tokens = parse_custom_pattern("custom:l1l2")
        assert tokens == ["l", "d", "l", "d"]

    def test_parse_underscore(self):
        tokens = parse_custom_pattern("custom:l_ld")
        assert tokens == ["l", "_", "l", "d"]

    def test_convert_template(self):
        tmpl = custom_pattern_to_template("custom:ll.l")
        assert tmpl == "ll.l"

    def test_invalid_char(self):
        with pytest.raises(ValueError):
            parse_custom_pattern("custom:l@l")

    def test_empty_pattern(self):
        with pytest.raises(ValueError):
            parse_custom_pattern("custom:")
