#!/usr/bin/env python3
"""Unit tests for the dependency-free Compose environment guard."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("check-compose-env.py")
SPEC = importlib.util.spec_from_file_location("check_compose_env", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


def compose_config(environment, *, service="nginx"):
    return {"services": {service: {"environment": environment}}}


class EnvironmentKeyTests(unittest.TestCase):
    def test_mapping_environment_is_supported(self):
        keys = CHECKER.extract_environment_keys(
            compose_config({"DOMAIN": "${DOMAIN}", "PORT": "${PORT:-443}"}), "nginx"
        )
        self.assertEqual(keys, {"DOMAIN", "PORT"})

    def test_list_environment_and_bare_keys_are_supported(self):
        keys = CHECKER.extract_environment_keys(
            compose_config(["DOMAIN=${DOMAIN}", "PORT", "URL=value=with=equals"]), "nginx"
        )
        self.assertEqual(keys, {"DOMAIN", "PORT", "URL"})

    def test_interpolation_and_default_syntax_are_compared_as_keys_only(self):
        base = compose_config(["DOMAIN=${DOMAIN}", "PORT=${HTTPS_PORT:-443}"])
        override = compose_config({"DOMAIN": "${DOMAIN:-central.local}", "PORT": "${HTTPS_PORT}"})
        base_keys, override_keys = CHECKER.check_environment_keys(base, override)
        self.assertEqual(base_keys, {"DOMAIN", "PORT"})
        self.assertEqual(override_keys, base_keys)

    def test_extra_override_keys_are_allowed(self):
        base = compose_config(["DOMAIN=${DOMAIN}"])
        override = compose_config(["DOMAIN=${DOMAIN}", "MODSEC_ENGINE_MODE=${MODSEC_ENGINE_MODE:-On}"])
        CHECKER.check_environment_keys(base, override)

    def test_missing_upstream_key_fails(self):
        base = compose_config(["DOMAIN=${DOMAIN}", "CERTBOT_EMAIL=${SYSADMIN_EMAIL}"])
        override = compose_config(["DOMAIN=${DOMAIN}"])
        with self.assertRaisesRegex(CHECKER.ComposeEnvironmentError, "missing 1 upstream"):
            CHECKER.check_environment_keys(base, override)

    def test_malformed_environment_entries_fail(self):
        malformed = [None, 17, {}, "", "=value", "bad key=value"]
        for entry in malformed:
            with self.subTest(entry_type=type(entry).__name__):
                with self.assertRaises(CHECKER.ComposeEnvironmentError):
                    CHECKER.extract_environment_keys(compose_config([entry]), "nginx")

    def test_malformed_environment_container_fails(self):
        with self.assertRaisesRegex(CHECKER.ComposeEnvironmentError, "mapping or list"):
            CHECKER.extract_environment_keys(compose_config("DOMAIN=value"), "nginx")

    def test_duplicate_environment_entries_fail(self):
        with self.assertRaisesRegex(CHECKER.ComposeEnvironmentError, "duplicate"):
            CHECKER.extract_environment_keys(compose_config(["DOMAIN=one", "DOMAIN=two"]), "nginx")

    def test_missing_service_and_environment_fail_closed(self):
        with self.assertRaisesRegex(CHECKER.ComposeEnvironmentError, "services mapping"):
            CHECKER.extract_environment_keys({}, "nginx")
        with self.assertRaisesRegex(CHECKER.ComposeEnvironmentError, "missing service"):
            CHECKER.extract_environment_keys({"services": {}}, "nginx")
        with self.assertRaisesRegex(CHECKER.ComposeEnvironmentError, "missing environment"):
            CHECKER.extract_environment_keys({"services": {"nginx": {}}}, "nginx")


class RenderTests(unittest.TestCase):
    def test_render_command_uses_json_and_no_interpolate(self):
        completed = subprocess.CompletedProcess([], 0, '{"services": {}}', "")
        runner = mock.Mock(return_value=completed)
        CHECKER.render_compose_file("base.yml", runner=runner)
        runner.assert_called_once_with(
            [
                "docker",
                "compose",
                "-f",
                "base.yml",
                "config",
                "--format",
                "json",
                "--no-interpolate",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_render_failure_is_safe_and_does_not_print_stderr_values(self):
        completed = subprocess.CompletedProcess([], 2, "", "secret-value should stay private")
        with self.assertRaisesRegex(CHECKER.ComposeEnvironmentError, "could not render") as raised:
            CHECKER.render_compose_file("base.yml", runner=mock.Mock(return_value=completed))
        self.assertNotIn("secret-value", str(raised.exception))

    def test_override_render_failure_mentions_compose_version(self):
        completed = subprocess.CompletedProcess([], 1, "", "parse failure")
        with self.assertRaisesRegex(CHECKER.ComposeEnvironmentError, "Compose >=2.24"):
            CHECKER.render_compose_file(
                "docker-compose.override.yml", runner=mock.Mock(return_value=completed)
            )

    def test_override_role_mentions_compose_version_for_custom_file_name(self):
        completed = subprocess.CompletedProcess([], 1, "", "parse failure")
        with self.assertRaisesRegex(CHECKER.ComposeEnvironmentError, "Compose >=2.24"):
            CHECKER.render_compose_file(
                "temporary-override.yml", override=True, runner=mock.Mock(return_value=completed)
            )

    def test_invalid_rendered_json_fails_without_echoing_output(self):
        output = '{"services": {"nginx": {"environment": ["SECRET=private"]}'
        with self.assertRaisesRegex(CHECKER.ComposeEnvironmentError, "invalid JSON") as raised:
            CHECKER.render_compose_file("base.yml", runner=mock.Mock(
                return_value=subprocess.CompletedProcess([], 0, output, "")
            ))
        self.assertNotIn("private", str(raised.exception))

    def test_duplicate_rendered_json_keys_fail(self):
        output = '{"services": {"nginx": {"environment": {"A": "1", "A": "2"}}}}'
        with self.assertRaisesRegex(CHECKER.ComposeEnvironmentError, "duplicate"):
            CHECKER.render_compose_file("base.yml", runner=mock.Mock(
                return_value=subprocess.CompletedProcess([], 0, output, "")
            ))

    def test_checker_renders_base_and_override_separately(self):
        outputs = [
            json.dumps(compose_config(["A=1"])),
            json.dumps(compose_config({"A": "${A}", "B": "extra"})),
        ]
        runner = mock.Mock(
            side_effect=[
                subprocess.CompletedProcess([], 0, outputs[0], ""),
                subprocess.CompletedProcess([], 0, outputs[1], ""),
            ]
        )
        CHECKER.check_compose_environment("base.yml", "override.yml", runner=runner)
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(runner.call_args_list[0].args[0][3], "base.yml")
        self.assertEqual(runner.call_args_list[1].args[0][3], "override.yml")

    def test_cli_accepts_file_and_service_parameters_with_temp_fixtures(self):
        # The CLI still invokes Compose; this test verifies its argument surface
        # without requiring a Docker daemon by replacing the render helper.
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "base.yml"
            override = Path(directory) / "override.yml"
            base.write_text("services: {}", encoding="utf-8")
            override.write_text("services: {}", encoding="utf-8")
            with mock.patch.object(
                CHECKER,
                "check_compose_environment",
                return_value=({"A"}, {"A", "B"}),
            ) as check:
                self.assertEqual(
                    CHECKER.main(["--base", str(base), "--override", str(override), "--service", "worker"]),
                    0,
                )
            check.assert_called_once_with(str(base), str(override), "worker")


if __name__ == "__main__":
    unittest.main()
