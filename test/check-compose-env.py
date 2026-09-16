#!/usr/bin/env python3
"""Check that a Compose override retains the base service environment keys.

The base and override files are rendered separately on purpose.  The override
uses Compose's ``!override`` tag, so checking the two rendered services avoids
silently treating a replaced environment list as an inherited one.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Callable


DEFAULT_BASE_FILE = "docker-compose.yml"
DEFAULT_OVERRIDE_FILE = "docker-compose.override.yml"
DEFAULT_SERVICE = "nginx"
_ENVIRONMENT_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ComposeEnvironmentError(Exception):
    """A safe, user-facing validation error.

    Error messages intentionally contain paths, service names, and counts only;
    rendered environment values are never included in an error.
    """


def _duplicate_free_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object while rejecting duplicate keys."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ComposeEnvironmentError("rendered Compose JSON contains duplicate object keys")
        result[key] = value
    return result


def _parse_rendered_json(output: str, compose_file: str) -> Mapping[str, Any]:
    try:
        document = json.loads(output, object_pairs_hook=_duplicate_free_object)
    except (json.JSONDecodeError, ComposeEnvironmentError) as exc:
        if isinstance(exc, ComposeEnvironmentError):
            raise ComposeEnvironmentError(
                f"rendered Compose config for {compose_file!r} contains duplicate keys"
            ) from exc
        raise ComposeEnvironmentError(
            f"docker Compose returned invalid JSON for {compose_file!r}"
        ) from exc
    if not isinstance(document, Mapping):
        raise ComposeEnvironmentError(
            f"rendered Compose config for {compose_file!r} must be a JSON object"
        )
    return document


def render_compose_file(
    compose_file: str | Path,
    *,
    runner: Callable[..., Any] = subprocess.run,
    override: bool = False,
) -> Mapping[str, Any]:
    """Render one Compose file as JSON without interpolating environment vars."""

    file_name = str(compose_file)
    command = [
        "docker",
        "compose",
        "-f",
        file_name,
        "config",
        "--format",
        "json",
        "--no-interpolate",
    ]
    try:
        result = runner(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise ComposeEnvironmentError(
            f"could not run docker Compose for {file_name!r}; is Docker Compose installed?"
        ) from exc
    if result.returncode != 0:
        detail = ""
        if override or file_name.endswith("docker-compose.override.yml"):
            detail = "; Compose >=2.24 is required because this override uses !override"
        raise ComposeEnvironmentError(
            f"docker Compose could not render {file_name!r} (exit {result.returncode}){detail}"
        )
    return _parse_rendered_json(result.stdout, file_name)


def _validate_environment_key(key: Any, location: str) -> str:
    if not isinstance(key, str) or not _ENVIRONMENT_KEY.fullmatch(key):
        raise ComposeEnvironmentError(f"malformed environment key at {location}")
    return key


def _environment_keys(environment: Any) -> set[str]:
    """Extract keys from Compose's mapping or list environment representation."""

    if isinstance(environment, Mapping):
        keys: set[str] = set()
        for index, key in enumerate(environment):
            validated = _validate_environment_key(key, f"mapping entry {index}")
            if validated in keys:
                raise ComposeEnvironmentError("duplicate environment key")
            keys.add(validated)
        return keys

    if isinstance(environment, list):
        keys = set()
        for index, entry in enumerate(environment):
            if not isinstance(entry, str) or not entry:
                raise ComposeEnvironmentError(f"malformed environment entry at list index {index}")
            key = entry.split("=", 1)[0]
            validated = _validate_environment_key(key, f"list index {index}")
            if validated in keys:
                raise ComposeEnvironmentError("duplicate environment key")
            keys.add(validated)
        return keys

    raise ComposeEnvironmentError("service environment must be a mapping or list")


def extract_environment_keys(config: Mapping[str, Any], service: str) -> set[str]:
    """Return one service's environment keys, validating its structure."""

    if not isinstance(config, Mapping):
        raise ComposeEnvironmentError("rendered Compose config must be a JSON object")
    services = config.get("services")
    if not isinstance(services, Mapping):
        raise ComposeEnvironmentError("rendered Compose config is missing a services mapping")
    if service not in services:
        raise ComposeEnvironmentError(f"rendered Compose config is missing service {service!r}")
    service_config = services[service]
    if not isinstance(service_config, Mapping):
        raise ComposeEnvironmentError(f"service {service!r} must be a mapping")
    if "environment" not in service_config:
        raise ComposeEnvironmentError(f"service {service!r} is missing environment")
    return _environment_keys(service_config["environment"])


def check_environment_keys(
    base_config: Mapping[str, Any],
    override_config: Mapping[str, Any],
    service: str = DEFAULT_SERVICE,
) -> tuple[set[str], set[str]]:
    """Validate that every base environment key exists in the override.

    Extra override keys are allowed because security/runtime configuration may
    add variables to the base service.
    """

    base_keys = extract_environment_keys(base_config, service)
    override_keys = extract_environment_keys(override_config, service)
    missing = base_keys - override_keys
    if missing:
        raise ComposeEnvironmentError(
            f"override service {service!r} is missing {len(missing)} upstream environment key(s)"
        )
    return base_keys, override_keys


def check_compose_environment(
    base_file: str | Path = DEFAULT_BASE_FILE,
    override_file: str | Path = DEFAULT_OVERRIDE_FILE,
    service: str = DEFAULT_SERVICE,
    *,
    runner: Callable[..., Any] = subprocess.run,
) -> tuple[set[str], set[str]]:
    """Render both files and check environment-key parity."""

    base_config = render_compose_file(base_file, runner=runner)
    override_config = render_compose_file(override_file, runner=runner, override=True)
    return check_environment_keys(base_config, override_config, service)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check that a Compose override retains base environment keys."
    )
    parser.add_argument("--base", default=DEFAULT_BASE_FILE, help="base Compose file")
    parser.add_argument("--override", default=DEFAULT_OVERRIDE_FILE, help="override Compose file")
    parser.add_argument("--service", default=DEFAULT_SERVICE, help="service to compare")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        base_keys, override_keys = check_compose_environment(
            args.base, args.override, args.service
        )
    except ComposeEnvironmentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        f"Compose environment check passed for {args.service!r}: "
        f"{len(base_keys)} upstream key(s), {len(override_keys)} override key(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
