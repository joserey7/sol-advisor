"""Static release contracts complement, but do not replace, live Codex checks."""
import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import tomllib
import unittest

from test_native_support import core, FIXTURES, HELPER, ROOT, TEMPLATES

PLUGIN = HELPER.parent.parent
REFS = PLUGIN / "skills/orchestration/references"


class ReleaseContracts(unittest.TestCase):
    def test_version_manifest_registry_and_changelog_agree(self):
        manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
        self.assertEqual("0.8.0", manifest["version"])
        self.assertEqual(manifest["version"], core.REGISTRY["release_version"])
        self.assertIn("0.8.0 - 2026-09-22", (ROOT / "CHANGELOG.md").read_text())
        self.assertEqual("Daniel McAteer", manifest["author"]["name"])
        self.assertEqual("https://github.com/joserey7/sol-advisor", manifest["repository"])

    def test_exact_active_inventory_and_independent_roles(self):
        self.assertEqual(set(core.FILES.values()), {p.name for p in TEMPLATES.glob("*.toml")})
        self.assertEqual({"luna", "sol-implementer", "sol"}, set(core.CORE_ROLES))
        self.assertEqual({"model": "gpt-6-sol", "effort": "xhigh"}, core.REGISTRY["primary"])
        expected = {"luna": ("gpt-6-luna", "max"), "sol-implementer": ("gpt-6-sol", "xhigh"),
                    "sol": ("gpt-6-sol", "xhigh"), "astra": ("gpt-6-astra", "high")}
        for key, (model, effort) in expected.items():
            data = tomllib.loads((TEMPLATES / core.FILES[key]).read_text())
            self.assertEqual(model, data["model"])
            self.assertEqual(effort, data["model_reasoning_effort"])
            self.assertTrue(data["developer_instructions"].strip())
            self.assertEqual(core.ROLES[key]["name"], data["name"])
            self.assertEqual(key == "astra", core.ROLES[key]["optional"])
            if key in ("sol", "astra"):
                self.assertEqual("read-only", data["sandbox_mode"])
        self.assertNotEqual(core.PINS["sol-implementer"][0], core.PINS["sol"][0])
        self.assertFalse((TEMPLATES / core.TERRA_FILE).exists())

    def test_registered_fingerprints_exactly_match_immutable_fixture_bytes(self):
        expected = {"luna": set(), "terra": set(), "sol": set()}
        for fixture in FIXTURES.values():
            digest = hashlib.sha256(fixture["content"].encode()).hexdigest()
            self.assertEqual(fixture["sha256"], digest)
            expected[fixture["role"]].add(digest)
        self.assertEqual(expected, core.LEGACY)
        # The newly added migration inputs are literally the released Git blobs.
        for role, sha in [("luna", "5d1941615a666bfb1408196c1d30132370384d76"),
                          ("terra", "347c2fdaf35d12341b160a1036af40d67728b567"),
                          ("sol", "603887c943297b0c5cbe6ce4f92f43dc9848003f")]:
            data = FIXTURES["v070_" + role]["content"].encode()
            self.assertEqual(sha, hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest())
        self.assertEqual("000ff8bed7f94f77a460fb81424d51233eb6146db5b21a346068aceb6a9abe27", FIXTURES["v060_luna_crlf"]["sha256"])
        self.assertEqual("7c9497c46207007565f72ac9bac6ce4954a1491914e4d64b44e27e4c27e8cd43", FIXTURES["v060_terra_crlf"]["sha256"])
        self.assertEqual("6ac63677bcc8677a9a743522cf06696c8edb1b005a61430e0fc8fa62e18dc355", FIXTURES["v060_sol_crlf"]["sha256"])

    def test_registry_rejects_duplicate_identities_and_traversal(self):
        for field, value in [("name", core.ROLES["sol"]["name"]), ("file", "../../outside.toml"),
                             ("optional", "false"), ("model", "")]:
            registry = copy.deepcopy(core.REGISTRY)
            registry["roles"]["astra"][field] = value
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "registry.json"
                path.write_text(json.dumps(registry))
                with self.assertRaises(core.SupportError):
                    core.read_registry(path)

    def test_all_shipped_json_is_valid(self):
        for path in ROOT.rglob("*.json"):
            if ".git" not in path.parts:
                json.loads(path.read_text(encoding="utf-8"))

    def test_documentation_local_links_resolve(self):
        for path in [ROOT / "README.md", *PLUGIN.rglob("*.md")]:
            text = path.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                if "://" in target or target.startswith("#"):
                    continue
                self.assertTrue((path.parent / target.split("#")[0]).exists(), f"{path}: {target}")

    def test_review_invalidation_and_advisor_limits_are_in_active_profiles(self):
        reviewer = (TEMPLATES / core.FILES["sol"]).read_text()
        advisor = (TEMPLATES / core.FILES["astra"]).read_text()
        self.assertIn("invalidates this verdict", reviewer)
        self.assertIn("new fresh review", reviewer)
        self.assertIn("not permission to spend", advisor)
        self.assertIn("renewed explicit authorization", advisor)
        self.assertIn("not a hard", advisor)
        self.assertIn("never continue autonomously or spawn agents", advisor)
        skill = (PLUGIN / "skills/orchestration/SKILL.md").read_text()
        self.assertIn("provisional", skill)
        self.assertIn("confirmed", skill)
        self.assertIn("Material consequence risk requires", skill)
        self.assertIn("check-plan", skill)
        self.assertLessEqual(len(skill.splitlines()), 150)

    def test_windows_entrypoints_expose_explicit_optional_install(self):
        for path in [ROOT / "scripts/install-plugin.ps1", HELPER.with_name("install-agents.ps1")]:
            text = path.read_text()
            self.assertIn("[switch] $WithAstra", text)
            self.assertIn("--with-astra", text)
        text = (ROOT / "tests/verify-windows.ps1").read_text()
        self.assertIn("-WithAstra", text)
        self.assertIn("sol-advisor-sol-implementer.toml", text)
        self.assertNotIn("gpt-5.6-luna", text)


if __name__ == "__main__":
    unittest.main()
