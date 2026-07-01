"""Tests for Reticulum config sanitization."""

from __future__ import annotations

from rnsvg.interfaces_manager import sanitize_rns_config_text, _normalize_config_value


def test_sanitize_removes_none_assignments():
    text = """[interfaces]
  [[UDP]]
    type = UDPInterface
    enabled = yes
    listen_ip = 10.0.0.1
    bitrate = None
    target_host = None
"""
    cleaned, changed = sanitize_rns_config_text(text)
    assert changed is True
    assert "bitrate" not in cleaned
    assert "target_host" not in cleaned
    assert "listen_ip = 10.0.0.1" in cleaned


def test_normalize_config_value_drops_nulls():
    assert _normalize_config_value(None) is None
    assert _normalize_config_value("None") is None
    assert _normalize_config_value(" 4242 ") == "4242"