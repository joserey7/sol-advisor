"""Dependency-free fixtures; never read or modify the real user's Codex home."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "plugins/sol-advisor/scripts/native-support.py"
TEMPLATES = HELPER.parent.parent / "agents"
spec = importlib.util.spec_from_file_location("native_support", HELPER)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
THREAD = "00000000-0000-0000-0000-000000000001"
SECRET = "PRIVATE_PROMPT_TOKEN_SENTINEL"


class NativeSupportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sol advisor tests ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.target = self.root / "Jos\u00e9 [profile]" / "agents"
        self.sessions = self.root / "sessions"

    def install(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            core.install(self.target, TEMPLATES, **kwargs)

    def snapshot(self):
        return {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.target.iterdir()}

    def cli(self, *args, env=None):
        return subprocess.run([sys.executable, str(HELPER), *args], capture_output=True,
                              encoding="utf-8", env=dict(os.environ if env is None else env, PYTHONIOENCODING="utf-8"), check=False)

    def records(self):
        return [
            {"type": "session_meta", "payload": {
                "id": THREAD, "agent_role": "sol_advisor_luna_implementer",
                "parent_thread_id": "parent", "agent_path": "lane", "model_provider": "openai",
                "prompt": SECRET, "token": SECRET}},
            {"type": "response_item", "payload": {"message": SECRET}},
            {"type": "turn_context", "payload": {
                "model": "gpt-5.6-luna", "effort": "max", "cwd": "C:/Jos\u00e9/project",
                "sandbox_policy": {"type": "workspace-write", "secret": SECRET},
                "permission_profile": {"type": "default"}, "environment": SECRET}},
        ]

    def rollout(self, records=None, *, name=None):
        self.sessions.mkdir(parents=True, exist_ok=True)
        path = self.sessions / (name or f"rollout-2026-09-19-{THREAD}.jsonl")
        records = self.records() if records is None else records
        path.write_text("\n".join(json.dumps(row) for row in records) + "\n", encoding="utf-8")
        return path

    def symlink(self, link, destination, directory=False):
        try:
            link.symlink_to(destination, target_is_directory=directory)
        except OSError as error:
            self.skipTest(f"Symbolic-link creation unavailable: {error}")

    def test_clean_install_and_idempotence(self):
        self.install()
        self.assertEqual(set(core.FILES.values()), {p.name for p in self.target.iterdir()})
        for name in core.FILES.values():
            self.assertEqual((self.target / name).read_bytes(), (TEMPLATES / name).read_bytes())
        before = self.snapshot()
        self.install()
        self.install(check=True)
        self.assertEqual(before, self.snapshot())

    def test_missing_check_never_creates_directory(self):
        with self.assertRaises(core.SupportError):
            self.install(check=True)
        self.assertFalse(self.target.exists())

    def test_conflict_preflights_all_roles_and_preserves_config(self):
        self.target.mkdir(parents=True)
        destination = self.target / core.FILES["terra"]
        destination.write_bytes(b"user customization\r\n")
        config = self.target.parent / "config.toml"
        config.write_bytes(b"# private user config\n")
        before = self.snapshot()
        with self.assertRaises(core.SupportError):
            self.install()
        self.assertEqual(before, self.snapshot())
        self.assertEqual(config.read_bytes(), b"# private user config\n")

    def test_role_scoped_check_ignores_unselected_destinations(self):
        self.target.mkdir(parents=True)
        name = core.FILES["luna"]
        shutil.copyfile(TEMPLATES / name, self.target / name)
        self.install(roles=["luna", "luna"])
        self.assertEqual([name], [p.name for p in self.target.iterdir()])
        with self.assertRaises(core.SupportError):
            self.install(check=True)

    def test_bad_arguments_do_not_mutate(self):
        for suffix in [("--check-role", "unknown"), ("--check-role",), ("--target-dir", "")]:
            result = self.cli("install", "--target-dir", str(self.target), *suffix)
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(self.target.exists())

    def test_root_and_file_targets_rejected(self):
        for target in [Path(self.root.anchor), self.root / "not-a-directory"]:
            if target.parent != target:
                target.write_bytes(b"unchanged")
            with self.assertRaises(core.SupportError):
                core.install(target, TEMPLATES)
        self.assertEqual((self.root / "not-a-directory").read_bytes(), b"unchanged")

    def test_directory_instead_of_role_is_unsafe(self):
        (self.target / core.FILES["luna"]).mkdir(parents=True)
        with self.assertRaises(core.SupportError):
            self.install()
        self.assertFalse((self.target / core.FILES["terra"]).exists())

    def test_symlinked_role_rejected(self):
        self.target.mkdir(parents=True)
        self.symlink(self.target / core.FILES["luna"], TEMPLATES / core.FILES["luna"])
        with self.assertRaises(core.SupportError):
            self.install()
        self.assertFalse((self.target / core.FILES["terra"]).exists())

    def test_broken_symlink_rejected(self):
        self.target.mkdir(parents=True)
        self.symlink(self.target / core.FILES["luna"], self.root / "missing")
        with self.assertRaises(core.SupportError):
            self.install()

    def test_linked_target_ancestor_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.symlink(self.target.parent, outside, directory=True)
        with self.assertRaises(core.SupportError):
            self.install()
        self.assertEqual([], list(outside.iterdir()))

    def test_windows_reparse_point_detection(self):
        self.assertTrue(core.is_link(SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)))

    @unittest.skipUnless(os.name == "nt", "Windows junction fixture")
    def test_windows_junction_target_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(self.target.parent), str(outside)], capture_output=True)
        self.assertEqual(0, result.returncode)
        try:
            with self.assertRaises(core.SupportError):
                self.install()
            self.assertEqual([], list(outside.iterdir()))
        finally:
            os.rmdir(self.target.parent)

    def test_defaults_precedence_and_native_windows_profile(self):
        env = {"HOME": "/unix-home", "USERPROFILE": "C:/native-profile", "CODEX_HOME": "/explicit"}
        self.assertEqual(Path("/explicit"), core.codex_home(env, windows=True))
        del env["CODEX_HOME"]
        self.assertEqual(Path("C:/native-profile/.codex"), core.codex_home(env, windows=True))
        self.assertEqual(Path("/unix-home/.codex"), core.codex_home(env, windows=False))
        with self.assertRaises(core.SupportError):
            core.codex_home({}, windows=True)

    def test_codex_home_install_and_explicit_override(self):
        env = dict(os.environ, CODEX_HOME=str(self.root / "native home"))
        result = self.cli("install", env=env)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue((Path(env["CODEX_HOME"]) / "agents" / core.FILES["sol"]).is_file())
        result = self.cli("install", "--target-dir", str(self.target), env=env)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(self.target.is_dir())

    def test_line_ending_changes_are_conflicts_not_silent_normalization(self):
        self.install()
        path = self.target / core.FILES["luna"]
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        before = self.snapshot()
        with self.assertRaises(core.SupportError):
            self.install()
        self.assertEqual(before, self.snapshot())

    def test_historical_fingerprints_match_posix_installer(self):
        shell = HELPER.with_name("install-agents.sh")
        if not shell.exists():
            self.skipTest("POSIX source not available in this checkout")
        text = shell.read_text(encoding="utf-8")
        for fingerprints in core.LEGACY.values():
            for fingerprint in fingerprints:
                self.assertIn(fingerprint, text)

    def test_exact_historical_migration_fixtures(self):
        # Reuse upstream's literal, digest-checked fixture bytes; no remote fetches.
        source = HELPER.with_name("verify.sh")
        if not source.exists():
            self.skipTest("Upstream fixture source not available")
        text = source.read_text(encoding="utf-8")
        for prefix in ["LEGACY", "V050"]:
            self.target.mkdir(parents=True, exist_ok=True)
            for role in ["luna", "terra"]:
                marker = prefix + "_" + role.upper()
                data = text.split("<<'" + marker + "'\n", 1)[1].split("\n" + marker, 1)[0].encode() + b"\n"
                self.assertIn(hashlib.sha256(data).hexdigest(), core.LEGACY[role])
                (self.target / core.FILES[role]).write_bytes(data)
            self.install()
            self.install(check=True)

    def test_historical_crlf_windows_profiles_migrate(self):
        source = HELPER.with_name("verify.sh")
        if not source.exists():
            self.skipTest("Upstream fixture source not available")
        text = source.read_text(encoding="utf-8")
        markers = {"luna": "V060_LUNA", "terra": "V060_TERRA", "sol": "LEGACY_SOL"}
        self.target.mkdir(parents=True, exist_ok=True)
        for role, marker in markers.items():
            data = text.split("<<'" + marker + "'\n", 1)[1].split("\n" + marker, 1)[0].encode() + b"\n"
            crlf = data.replace(b"\n", b"\r\n")
            self.assertIn(hashlib.sha256(crlf).hexdigest(), core.LEGACY[role])
            (self.target / core.FILES[role]).write_bytes(crlf)
        self.install()
        self.install(check=True)

    def test_runtime_allowlist_and_no_payload_leakage(self):
        self.rollout()
        result = self.cli("inspect", "--sessions-dir", str(self.sessions), THREAD)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn(SECRET, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(set(data), {"thread_id", "parent_thread_id", "agent_role", "agent_path", "model_provider", "model", "effort", "sandbox_policy_type", "permission_profile_type", "cwd"})
        self.assertEqual(data["effort"], "max")

    def test_runtime_zero_multiple_or_wrong_thread_fails(self):
        self.sessions.mkdir()
        with self.assertRaises(core.SupportError):
            core.inspect_runtime(self.sessions, THREAD)
        self.rollout()
        self.rollout(name=f"rollout-other-{THREAD}.jsonl")
        with self.assertRaises(core.SupportError):
            core.inspect_runtime(self.sessions, THREAD)

    def test_invalid_runtime_json_does_not_leak(self):
        path = self.rollout()
        path.write_text(SECRET + "{invalid", encoding="utf-8")
        result = self.cli("inspect", "--sessions-dir", str(self.sessions), THREAD)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertNotIn(SECRET, result.stderr)

    def test_runtime_rejects_invalid_id_without_reading(self):
        for thread in ["../escape", THREAD.upper().replace("00000000", "AAAAAAAA"), "", THREAD + "\n"]:
            with self.assertRaises(core.SupportError):
                core.inspect_runtime(self.sessions, thread)

    def test_runtime_conflicting_turns_fail(self):
        for field, value in [("model", "other"), ("effort", "low"), ("sandbox_policy", {"type": "other"}),
                             ("permission_profile", {"type": "other"}), ("cwd", "other")]:
            rows = self.records()
            extra = copy.deepcopy(rows[-1])
            extra["payload"][field] = value
            self.rollout(rows + [extra])
            with self.assertRaises(core.SupportError):
                core.inspect_runtime(self.sessions, THREAD)

    def test_runtime_missing_required_and_ambiguous_session_fail(self):
        for section, field in [(0, "id"), (0, "agent_role"), (-1, "model"), (-1, "effort")]:
            rows = self.records()
            del rows[section]["payload"][field]
            self.rollout(rows)
            with self.assertRaises(core.SupportError):
                core.inspect_runtime(self.sessions, THREAD)
        rows = self.records()
        self.rollout(rows + [rows[0]])
        with self.assertRaises(core.SupportError):
            core.inspect_runtime(self.sessions, THREAD)

    def test_unrelated_rollouts_are_not_parsed(self):
        self.rollout()
        (self.sessions / "rollout-unrelated.jsonl").write_text(SECRET + "invalid JSON", encoding="utf-8")
        self.assertEqual(THREAD, core.inspect_runtime(self.sessions, THREAD)["thread_id"])

    def test_identical_turns_and_missing_optional_fields_are_supported(self):
        rows = self.records()
        for field in ["sandbox_policy", "permission_profile", "cwd"]:
            del rows[-1]["payload"][field]
        self.rollout(rows + [copy.deepcopy(rows[-1])])
        self.assertIsNone(core.inspect_runtime(self.sessions, THREAD)["cwd"])


if __name__ == "__main__":
    unittest.main()
