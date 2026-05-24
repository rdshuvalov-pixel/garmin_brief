"""Tests for Vercel deploy helper."""

from pathlib import Path
from unittest.mock import patch

from hermes.brief.vercel_deploy import deploy_vercel_if_configured


def test_skips_without_token(tmp_path: Path):
    with patch.dict("os.environ", {}, clear=True):
        assert deploy_vercel_if_configured(tmp_path) is False


def test_skips_without_project_ids(tmp_path: Path):
    env = {"VERCEL_TOKEN": "tok"}
    with patch.dict("os.environ", env, clear=True):
        assert deploy_vercel_if_configured(tmp_path) is False
