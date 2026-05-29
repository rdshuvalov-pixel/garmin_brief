"""Tests for BRIEF_PUBLIC_BASE_URL validation."""

from hermes.config import brief_public_base_url_warnings


def test_vercel_ap_typo_warns():
    warnings = brief_public_base_url_warnings("https://garmin-brief.vercel.ap")
    assert any(".vercel.ap" in w for w in warnings)


def test_vercel_app_ok():
    warnings = brief_public_base_url_warnings("https://garmin-brief.vercel.app")
    assert not any(".vercel.ap" in w for w in warnings)


def test_localhost_warns():
    warnings = brief_public_base_url_warnings("http://127.0.0.1:8765")
    assert len(warnings) == 1
