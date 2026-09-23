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
FIXTURES = json.loads((ROOT / "tests/fixtures/legacy-profiles.json").read_text(encoding="utf-8"))
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
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            core.install(self.target, TEMPLATES, **kwargs)

    def snapshot(self):
        if not self.target.exists():
            return {}
        return {str(p.relative_to(self.target.parent)): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.target.parent.rglob("*") if p.is_file() and not p.is_symlink()}

    def cli(self, *args, env=None, input=None):
        return subprocess.run([sys.executable, str(HELPER), *args], capture_output=True,
                              encoding="utf-8", input=input,
                              env=dict(os.environ if env is None else env, PYTHONIOENCODING="utf-8"), check=False)

    def legacy_path(self, fixture):
        role = fixture["role"]
        return self.target / (core.TERRA_FILE if role == "terra" else core.FILES[role])

    def write_fixture(self, label):
        self.target.mkdir(parents=True, exist_ok=True)
        fixture = FIXTURES[label]
        data = fixture["content"].encode()
        self.assertEqual(fixture["sha256"], hashlib.sha256(data).hexdigest())
        self.assertIn(fixture["sha256"], core.LEGACY[fixture["role"]])
        path = self.legacy_path(fixture)
        path.write_bytes(data)
        return path, data

    def records(self):
        return [
            {"type": "session_meta", "payload": {
                "id": THREAD, "agent_role": "sol_advisor_luna_implementer",
                "parent_thread_id": "parent", "agent_path": "lane", "model_provider": "openai",
                "prompt": SECRET, "token": SECRET}},
            {"type": "response_item", "payload": {"message": SECRET}},
            {"type": "turn_context", "payload": {
                "model": "gpt-6-luna", "effort": "max", "cwd": "C:/Jos\u00e9/project",
                "sandbox_policy": {"type": "workspace-write", "secret": SECRET},
                "permission_profile": {"type": "default"}, "environment": SECRET}},
        ]

    def rollout(self, records=None, *, name=None):
        self.sessions.mkdir(parents=True, exist_ok=True)
        path = self.sessions / (name or f"rollout-2026-09-22-{THREAD}.jsonl")
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
        expected = {core.FILES[key] for key in core.CORE_ROLES}
        self.assertEqual(expected, {p.name for p in self.target.iterdir()})
        self.assertFalse((self.target / core.FILES["astra"]).exists())
        for name in expected:
            self.assertEqual((self.target / name).read_bytes(), (TEMPLATES / name).read_bytes())
        before = self.snapshot()
        self.install()
        self.install(check=True)
        self.assertEqual(before, self.snapshot())

    def test_optional_astra_install_and_explicit_check(self):
        self.install()
        with self.assertRaises(core.SupportError):
            self.install(roles=["astra"])
        self.install(with_astra=True)
        self.install(roles=["astra"])
        before = self.snapshot()
        self.install(with_astra=True)
        self.assertEqual(before, self.snapshot())
        self.assertIn("NOT authorized", self.cli("install", "--target-dir", str(self.target), "--with-astra").stdout)

    def test_core_ignores_missing_optional_source_and_conflicting_destination(self):
        bundle = self.root / "bundle"
        shutil.copytree(TEMPLATES, bundle)
        (bundle / core.FILES["astra"]).unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            core.install(self.target, bundle)
        optional = self.target / core.FILES["astra"]
        optional.write_bytes(b"user customization")
        before = self.snapshot()
        self.install(check=True)
        self.install()
        self.assertEqual(before, self.snapshot())
        with self.assertRaises(core.SupportError):
            self.install(with_astra=True)
        self.assertEqual(before, self.snapshot())

    def test_missing_check_never_creates_directory(self):
        with self.assertRaises(core.SupportError):
            self.install(check=True)
        self.assertFalse(self.target.exists())

    def test_conflict_preflights_all_selected_roles_and_preserves_config(self):
        self.target.mkdir(parents=True)
        destination = self.target / core.FILES["sol-implementer"]
        destination.write_bytes(b"user customization\r\n")
        config = self.target.parent / "config.toml"
        config.write_bytes(b"# private user config\n")
        before = self.snapshot()
        with self.assertRaises(core.SupportError):
            self.install()
        self.assertEqual(before, self.snapshot())

    def test_role_scoped_checks_ignore_unselected_destinations(self):
        for selected in [("luna", "sol"), ("sol-implementer", "sol")]:
            self.install()
            unselected = "sol-implementer" if selected[0] == "luna" else "luna"
            path = self.target / core.FILES[unselected]
            original = path.read_bytes()
            path.write_bytes(b"custom")
            before = self.snapshot()
            self.install(roles=[*selected, selected[0]])
            with self.assertRaises(core.SupportError):
                self.install(check=True)
            with self.assertRaises(core.SupportError):
                self.install(roles=[unselected])
            self.assertEqual(before, self.snapshot())
            path.write_bytes(original)

    def test_bad_arguments_do_not_mutate(self):
        for suffix in [("--check-role", "unknown"), ("--check-role", "terra"), ("--check-role",),
                       ("--target-dir", ""), ("--with-astra", "--check-role", "luna")]:
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
        self.assertFalse((self.target / core.FILES["sol"]).exists())

    def test_symlinked_role_rejected(self):
        self.target.mkdir(parents=True)
        self.symlink(self.target / core.FILES["luna"], TEMPLATES / core.FILES["luna"])
        with self.assertRaises(core.SupportError):
            self.install()
        self.assertFalse((self.target / core.FILES["sol"]).exists())

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

    def test_current_line_ending_changes_are_conflicts(self):
        self.install()
        for role in core.CORE_ROLES:
            path = self.target / core.FILES[role]
            original = path.read_bytes()
            path.write_bytes(original.replace(b"\n", b"\r\n"))
            before = self.snapshot()
            with self.assertRaises(core.SupportError):
                self.install()
            self.assertEqual(before, self.snapshot())
            path.write_bytes(original)

    def test_every_historical_fixture_migrates_or_archives_exactly(self):
        for label, fixture in FIXTURES.items():
            with self.subTest(label=label):
                path, data = self.write_fixture(label)
                self.install()
                self.install(check=True)
                if fixture["role"] == "terra":
                    self.assertFalse(path.exists())
                    archive = self.target.parent / "sol-advisor-retired" / f'{core.TERRA_FILE}.{fixture["sha256"]}.bak'
                    self.assertEqual(data, archive.read_bytes())
                else:
                    self.assertEqual((TEMPLATES / path.name).read_bytes(), path.read_bytes())
                before = self.snapshot()
                self.install()
                self.assertEqual(before, self.snapshot())

    def test_full_v070_installation_migrates_without_astra(self):
        for role in ("luna", "terra", "sol"):
            self.write_fixture("v070_" + role)
        self.install()
        self.install(check=True)
        self.assertFalse((self.target / core.TERRA_FILE).exists())
        self.assertFalse((self.target / core.FILES["astra"]).exists())

    def test_modified_historical_active_roles_fail_before_any_mutation(self):
        for label, fixture in FIXTURES.items():
            if fixture["role"] == "terra":
                continue
            with self.subTest(label=label):
                path, data = self.write_fixture(label)
                path.write_bytes(data + b"X")
                before = self.snapshot()
                with self.assertRaises(core.SupportError):
                    self.install()
                self.assertEqual(before, self.snapshot())
                path.unlink()

    def test_custom_terra_is_preserved_and_warned_not_selected(self):
        path, data = self.write_fixture("v070_terra")
        path.write_bytes(data + b"# customization\n")
        expected = path.read_bytes()
        result = self.cli("install", "--target-dir", str(self.target))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("customized retired Terra", result.stderr)
        self.assertEqual(expected, path.read_bytes())
        self.assertNotIn("terra", core.ROLES)

    def test_check_does_not_retire_terra(self):
        self.install()
        self.write_fixture("v070_terra")
        before = self.snapshot()
        self.install(check=True)
        self.assertEqual(before, self.snapshot())

    def test_archive_conflict_stops_all_writes(self):
        _, data = self.write_fixture("v070_terra")
        digest = hashlib.sha256(data).hexdigest()
        archive = self.target.parent / "sol-advisor-retired" / f"{core.TERRA_FILE}.{digest}.bak"
        archive.parent.mkdir()
        archive.write_bytes(b"user archive")
        before = self.snapshot()
        with self.assertRaises(core.SupportError):
            self.install()
        self.assertEqual(before, self.snapshot())

    def test_linked_retirement_directory_stops_all_writes(self):
        self.write_fixture("v070_terra")
        outside = self.root / "outside"
        outside.mkdir()
        self.symlink(self.target.parent / "sol-advisor-retired", outside, directory=True)
        before = self.snapshot()
        with self.assertRaises(core.SupportError):
            self.install()
        self.assertEqual(before, self.snapshot())
        self.assertEqual([], list(outside.iterdir()))

    def test_existing_identical_archive_is_reusable(self):
        self.write_fixture("v070_terra")
        self.install()
        self.write_fixture("v070_terra")
        self.install()
        self.assertFalse((self.target / core.TERRA_FILE).exists())
        self.assertEqual(1, len(list((self.target.parent / "sol-advisor-retired").iterdir())))

    def test_runtime_allowlist_and_no_payload_leakage(self):
        self.rollout()
        result = self.cli("inspect", "--sessions-dir", str(self.sessions), "--expect-role", "luna", THREAD)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn(SECRET, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(set(data), {"thread_id", "parent_thread_id", "agent_role", "agent_path", "model_provider", "model", "effort", "sandbox_policy_type", "permission_profile_type", "cwd"})
        self.assertEqual(data["effort"], "max")

    def test_runtime_zero_multiple_or_wrong_thread_fails(self):
        self.sessions.mkdir()
        with self.assertRaises(core.SupportError):
            core.inspect_runtime(self.sessions, THREAD)
        rows = self.records()
        rows[0]["payload"]["id"] = "wrong"
        self.rollout(rows)
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
        for thread in ["../escape", "AAAAAAAA-0000-0000-0000-000000000001", "", THREAD + "\n"]:
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

    def test_runtime_pins_distinguish_sol_worker_from_reviewer(self):
        for key in core.ROLES:
            name, model, effort = core.PINS[key]
            data = {"agent_role": name, "model": model, "effort": effort, "sandbox_policy_type": "read-only"}
            core.verify_runtime(data, key, require_read_only=core.ROLES[key]["read_only"])
            for field in ("agent_role", "model", "effort"):
                bad = dict(data, **{field: "wrong"})
                with self.assertRaises(core.SupportError):
                    core.verify_runtime(bad, key)
        data = {"agent_role": core.PINS["sol-implementer"][0], "model": "gpt-6-sol", "effort": "xhigh"}
        with self.assertRaises(core.SupportError):
            core.verify_runtime(data, "sol")

    def test_required_isolation_rejects_broader_or_unobservable_policy(self):
        for observed in (None, "workspace-write", "danger-full-access"):
            data = {"agent_role": core.PINS["sol"][0], "model": "gpt-6-sol", "effort": "xhigh", "sandbox_policy_type": observed}
            with self.assertRaises(core.SupportError):
                core.verify_runtime(data, "sol", require_read_only=True)

    @unittest.skipIf(os.name == "nt", "POSIX wrapper; Windows has separate PS fixtures")
    def test_posix_wrapper_install_check_runtime_and_relative_paths(self):
        shell = HELPER.with_name("install-agents.sh")
        for args in [("--target-dir", "relative agents"), ("--target-dir", "relative agents", "--check")]:
            result = subprocess.run(["sh", str(shell), *args], cwd=self.root, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
        self.rollout()
        result = subprocess.run(["sh", str(HELPER.with_name("inspect-agent-runtime.sh")), "--sessions-dir", str(self.sessions), THREAD], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(THREAD, json.loads(result.stdout)["thread_id"])


class PlanTests(unittest.TestCase):
    def plan(self, **kwargs):
        return dict({"mode": "solo", "difficulty": "bounded", "risk": "contained"}, **kwargs)

    def astra(self, **kwargs):
        return dict({"trigger": "irreversible-decision", "decision": "Choose a migration strategy",
                     "user_authorization": "Explicit user approval, current task, decision D1",
                     "evidence": "Schema and lock-contention trace", "counterevidence": "Rollback limitations",
                     "alternatives": "Incremental migration versus replacement", "required_checks": "Replay and rollback test",
                     "consultation_number": 1}, **kwargs)

    def test_solo_needs_no_auxiliary_or_astra(self):
        result = core.check_plan(self.plan())
        self.assertEqual([], result["companion_checks"])
        self.assertFalse(result["astra_selected"])

    def test_routes_select_only_the_needed_roles(self):
        for mode, worker, expected in [("delegate", "luna", ["luna"]), ("audit", None, ["sol"]),
                                       ("full", "sol-implementer", ["sol-implementer", "sol"])]:
            plan = self.plan(mode=mode, worker=worker, delegation_benefit="Isolate repeated implementation",
                             full_justification="Independent implementation and scrutiny are justified")
            self.assertEqual(expected, core.check_plan(plan)["companion_checks"])

    def test_material_risk_requires_independent_review_even_for_small_changes(self):
        for mode in ("solo", "delegate"):
            with self.assertRaises(core.SupportError):
                core.check_plan(self.plan(mode=mode, risk="material", worker="luna", delegation_benefit="Work saved"))
        self.assertEqual(["sol"], core.check_plan(self.plan(mode="audit", risk="material"))["companion_checks"])

    def test_judgment_heavy_work_never_forces_luna_retry(self):
        with self.assertRaises(core.SupportError):
            core.check_plan(self.plan(mode="delegate", difficulty="judgment-heavy", worker="luna", delegation_benefit="Work saved"))
        result = core.check_plan(self.plan(mode="delegate", difficulty="judgment-heavy", worker="sol-implementer", delegation_benefit="Isolated block"))
        self.assertEqual(["sol-implementer"], result["companion_checks"])

    def test_duplicate_worker_and_unjustified_full_are_rejected(self):
        for plan in [self.plan(worker="luna"), self.plan(mode="audit", worker="sol-implementer"),
                     self.plan(mode="delegate", worker="luna"), self.plan(mode="full", worker="luna", delegation_benefit="Volume")]:
            with self.assertRaises(core.SupportError):
                core.check_plan(plan)

    def test_retired_terra_unknown_roles_and_fields_are_rejected(self):
        for worker in ("terra", "sol", "astra", "unknown"):
            with self.assertRaises(core.SupportError):
                core.check_plan(self.plan(mode="delegate", worker=worker, delegation_benefit="Not valid"))
        for plan in [{}, [], self.plan(unexpected=True), self.plan(mode="astra")]:
            with self.assertRaises(core.SupportError):
                core.check_plan(plan)

    def test_astra_requires_each_packet_field_and_qualifying_trigger(self):
        for field in self.astra():
            packet = self.astra()
            del packet[field]
            with self.assertRaises(core.SupportError, msg=field):
                core.check_plan(self.plan(astra=packet))
        for trigger in ("large-diff", "failed-test", "full", "expensive"):
            with self.assertRaises(core.SupportError):
                core.check_plan(self.plan(astra=self.astra(trigger=trigger)))
        result = core.check_plan(self.plan(astra=self.astra()))
        self.assertEqual(["astra"], result["companion_checks"])
        self.assertEqual("declarative-only", result["enforcement"])

    def test_second_consultation_requires_renewal(self):
        with self.assertRaises(core.SupportError):
            core.check_plan(self.plan(astra=self.astra(consultation_number=2)))
        result = core.check_plan(self.plan(astra=self.astra(consultation_number=2, renewed_authorization=True)))
        self.assertTrue(result["astra_selected"])
        for number in (True, "1", 0, -1):
            with self.assertRaises(core.SupportError):
                core.check_plan(self.plan(astra=self.astra(consultation_number=number)))

    def test_astra_never_replaces_required_review(self):
        plan = self.plan(mode="full", worker="luna", risk="material", delegation_benefit="Bounded repeated work",
                         full_justification="Material consequences", astra=self.astra())
        self.assertEqual(["luna", "sol", "astra"], core.check_plan(plan)["companion_checks"])

    def test_plan_cli_rejects_bad_json_without_echoing_authorization(self):
        result = subprocess.run([sys.executable, str(HELPER), "check-plan"], input=SECRET + "{invalid", capture_output=True, text=True)
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn(SECRET, result.stdout + result.stderr)
        result = subprocess.run([sys.executable, str(HELPER), "check-plan"], input=json.dumps(self.plan()), capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([], json.loads(result.stdout)["companion_checks"])


if __name__ == "__main__":
    unittest.main()
