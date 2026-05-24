"""Tests for config loading."""

from hermes.config import _load_yaml_defaults


def test_config_yaml_loads():
    cfg = _load_yaml_defaults()
    assert cfg.get("name") == "garmin-brief"
    assert cfg.get("timezone") == "Europe/Lisbon"
    assert cfg.get("brief", {}).get("port") == 8765
