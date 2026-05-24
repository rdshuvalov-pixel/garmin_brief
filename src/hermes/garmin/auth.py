"""Garmin Connect authentication with token reuse."""

from __future__ import annotations

import logging
from getpass import getpass
from pathlib import Path

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)
from garth.exc import GarthException, GarthHTTPError

from hermes.config import Config

logger = logging.getLogger(__name__)


def _prompt_mfa() -> str:
    return input("MFA code: ").strip()


def _tokens_exist(tokenstore_path: Path) -> bool:
    return (
        (tokenstore_path / "oauth1_token.json").exists()
        and (tokenstore_path / "oauth2_token.json").exists()
    )


def _complete_session(client: Garmin) -> None:
    client.display_name = client.garth.profile["displayName"]
    client.full_name = client.garth.profile["fullName"]
    settings = client.garth.connectapi("/userprofile-service/userprofile/user-settings")
    client.unit_system = settings["userData"]["measurementSystem"]


def init_garmin_client(config: Config, *, interactive: bool = False) -> Garmin | None:
    """Restore saved tokens or perform credential login with MFA support."""
    tokenstore_path = config.garmin_tokens_path
    tokenstore_path.mkdir(parents=True, exist_ok=True)
    tokenstore = str(tokenstore_path)

    client = Garmin(email=config.garmin_email, password=config.garmin_password)

    if _tokens_exist(tokenstore_path):
        try:
            client.login(tokenstore)
            logger.info("Logged in using saved tokens from %s", tokenstore_path)
            return client
        except (GarminConnectAuthenticationError, GarminConnectConnectionError, OSError) as err:
            logger.warning("Saved tokens invalid or expired: %s", err)

    if not interactive and (not config.garmin_email or not config.garmin_password):
        logger.error(
            "Garmin credentials missing. Set GARMIN_EMAIL/GARMIN_PASSWORD or run scripts/login.py"
        )
        return None

    while True:
        try:
            email = config.garmin_email or input("Garmin email: ").strip()
            password = config.garmin_password or getpass("Garmin password: ")

            client.garth.login(email, password, prompt_mfa=_prompt_mfa)
            client.garth.dump(tokenstore)
            _complete_session(client)
            logger.info("Login successful. Tokens saved to %s", tokenstore_path)
            return client
        except GarminConnectTooManyRequestsError as err:
            logger.error("Garmin rate limit: %s", err)
            raise
        except (GarminConnectAuthenticationError, GarthException, GarthHTTPError, AssertionError) as err:
            logger.warning("Garmin login failed: %s", err)
            if not interactive:
                return None
            continue
        except GarminConnectConnectionError as err:
            logger.error("Garmin connection error: %s", err)
            return None
        except KeyboardInterrupt:
            logger.info("Login cancelled")
            return None


def login_interactive(config: Config) -> int:
    """Run interactive login; returns process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    client = init_garmin_client(config, interactive=True)
    if client is None:
        return 1
    print(f"Tokens saved to: {config.garmin_tokens_path}")
    return 0
