#!/usr/bin/env python3
"""Portable companion installation, plan validation, and allowlisted runtime inspection.

Python 3.11+, standard library only. Never edits Codex configuration or calls models.
A validated plan is not a runtime permission boundary or a hard spending limit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import tomllib


class SupportError(Exception):
    """Safe operator-facing failure; never attach rollout or authorization payloads."""


def read_registry(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("roles"), dict):
        raise SupportError("Invalid shipped role registry.")
    names, files = set(), set()
    for key, role in data["roles"].items():
        if not re.fullmatch(r"[a-z][a-z-]*", key):
            raise SupportError("Invalid role key.")
        if not re.fullmatch(r"sol-advisor-[a-z-]+\.toml", role.get("file", "")):
            raise SupportError("Invalid role filename.")
        for field in ("name", "model", "effort"):
            if not isinstance(role.get(field), str) or not role[field].strip():
                raise SupportError("Missing role pin.")
        if any(type(role.get(field)) is not bool for field in ("optional", "read_only")):
            raise SupportError("Invalid role capabilities.")
        if role["name"] in names or role["file"] in files:
            raise SupportError("Duplicate role identity.")
        names.add(role["name"])
        files.add(role["file"])
    return data


REGISTRY = read_registry(Path(__file__).with_name("role-registry.json"))
ROLES = REGISTRY["roles"]
FILES = {key: role["file"] for key, role in ROLES.items()}
PINS = {key: (role["name"], role["model"], role["effort"]) for key, role in ROLES.items()}
CORE_ROLES = tuple(key for key, role in ROLES.items() if not role["optional"])
LEGACY = {key: frozenset(values) for key, values in REGISTRY["legacy_sha256"].items()}
TERRA_FILE = "sol-advisor-terra-implementer.toml"
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")


def codex_home(environ=None, *, windows=None) -> Path:
    env = os.environ if environ is None else environ
    if env.get("CODEX_HOME"):
        return Path(env["CODEX_HOME"])
    windows = os.name == "nt" if windows is None else windows
    key = "USERPROFILE" if windows else "HOME"
    if not env.get(key):
        raise SupportError(f"{key} is unset; set CODEX_HOME or supply an explicit directory.")
    return Path(env[key]) / ".codex"


def lstat_or_none(path: Path):
    try:
        return path.lstat()
    except FileNotFoundError:
        return None


def is_link(info) -> bool:
    # Reparse points include Windows junctions on Python 3.11.
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def assert_directory_chain(path: Path) -> None:
    for item in (path, *path.parents):
        info = lstat_or_none(item)
        if info is not None and (is_link(info) or not stat.S_ISDIR(info.st_mode)):
            raise SupportError(f"Unsafe directory (link, reparse point, or non-directory): {item}")


def absolute_path(value: str | Path) -> Path:
    if not str(value).strip():
        raise SupportError("Directory must not be empty.")
    return Path(os.path.abspath(os.path.expanduser(value)))


def read_regular(path: Path) -> bytes:
    info = lstat_or_none(path)
    if info is None or is_link(info) or not stat.S_ISREG(info.st_mode):
        raise SupportError(f"Missing or unsafe regular file: {path}")
    return path.read_bytes()


def read_templates(directory: Path, roles=None) -> dict[str, bytes]:
    assert_directory_chain(directory)
    templates = {}
    for role in CORE_ROLES if roles is None else roles:
        path = directory / FILES[role]
        data = read_regular(path)
        parsed = tomllib.loads(data.decode("utf-8"))
        actual = tuple(parsed.get(key) for key in ("name", "model", "model_reasoning_effort"))
        if actual != PINS[role]:
            raise SupportError(f"Shipped template has unexpected role/model/effort pins: {path}")
        if ROLES[role]["read_only"] and parsed.get("sandbox_mode") != "read-only":
            raise SupportError(f"Read-only role lost its sandbox request: {path}")
        if any(not isinstance(parsed.get(key), str) or not parsed[key].strip()
               for key in ("description", "developer_instructions")):
            raise SupportError(f"Shipped template lacks its role contract: {path}")
        templates[role] = data
    return templates


def classify(path: Path, data: bytes, role: str) -> str:
    info = lstat_or_none(path)
    if info is None:
        return "missing"
    if is_link(info) or not stat.S_ISREG(info.st_mode):
        return "unsafe"
    try:
        installed = path.read_bytes()
    except OSError:
        return "unreadable"
    if installed == data:
        return "current"
    return "legacy" if hashlib.sha256(installed).hexdigest() in LEGACY.get(role, ()) else "conflict"


def publish_new(destination: Path, data: bytes) -> None:
    """Publish a complete file without replacing any existing destination."""
    assert_directory_chain(destination.parent)
    fd, name = tempfile.mkstemp(prefix=".sol-advisor-", dir=destination.parent)
    staged = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        assert_directory_chain(destination.parent)
        if os.name == "nt":
            os.rename(staged, destination)  # Windows refuses an existing destination.
        else:
            os.link(staged, destination)  # Exclusive publication, unlike POSIX rename.
    finally:
        if staged.exists():
            staged.unlink()


def plan_terra_retirement(target: Path):
    """Preflight exact released Terra bytes; unknown user files are never changed."""
    source = target / TERRA_FILE
    info = lstat_or_none(source)
    if info is None:
        return None
    if is_link(info) or not stat.S_ISREG(info.st_mode):
        print(f"WARNING: unsafe retired Terra profile retained; never selected by this workflow: {source}", file=sys.stderr)
        return None
    try:
        data = source.read_bytes()
    except OSError:
        print("WARNING: unreadable retired Terra profile retained; remove it manually from agent discovery.", file=sys.stderr)
        return None
    digest = hashlib.sha256(data).hexdigest()
    if digest not in LEGACY["terra"]:
        print(f"WARNING: customized retired Terra profile retained; move it outside agent discovery manually: {source}", file=sys.stderr)
        return None
    archive = target.parent / "sol-advisor-retired" / f"{TERRA_FILE}.{digest}.bak"
    assert_directory_chain(archive.parent)
    if lstat_or_none(archive) is not None and read_regular(archive) != data:
        raise SupportError("Retired Terra archive conflicts; no files changed.")
    return source, archive, data


def retire_terra(retirement) -> None:
    if retirement is None:
        return
    source, archive, data = retirement
    assert_directory_chain(source.parent)
    if read_regular(source) != data:
        raise SupportError("Terra changed after preflight; retained without removal.")
    assert_directory_chain(archive.parent)
    archive.parent.mkdir(parents=True, exist_ok=True)
    assert_directory_chain(archive.parent)
    if lstat_or_none(archive) is None:
        publish_new(archive, data)
    if read_regular(archive) != data or read_regular(source) != data:
        raise SupportError("Terra or its archive changed; source not removed.")
    source.unlink()
    print(f"RETIRED: exact Terra profile archived outside agent discovery: {archive}")


def install(target: Path, template_dir: Path, *, check=False, roles=(), with_astra=False) -> None:
    if roles and with_astra:
        raise SupportError("Use --with-astra for a bundle or --check-role for selected checks, not both.")
    selected = tuple(dict.fromkeys(roles)) or (CORE_ROLES + (("astra",) if with_astra else ()))
    if any(role not in FILES for role in selected):
        raise SupportError("Unknown role; expected luna, sol-implementer, sol, or astra.")
    check = check or bool(roles)
    target = absolute_path(target)
    if target.parent == target:
        raise SupportError("Refusing to use a filesystem root as an agent directory.")
    assert_directory_chain(target)
    templates = read_templates(template_dir, selected)
    states = {role: classify(target / FILES[role], templates[role], role) for role in selected}
    allowed = {"current"} if check else {"missing", "current", "legacy"}
    failures = [f"{role}: {state}" for role, state in states.items() if state not in allowed]
    if failures:
        raise SupportError("Preflight failed; no files changed: " + "; ".join(failures))
    if check:
        print("CHECK PASSED: selected role templates match exactly.")
        return
    # Preflight ALL selected destinations and the archive before any mutations.
    before = {role: None if state == "missing" else read_regular(target / FILES[role])
              for role, state in states.items()}
    retirement = plan_terra_retirement(target)
    target.mkdir(parents=True, exist_ok=True)
    assert_directory_chain(target)
    for role, state in states.items():
        destination = target / FILES[role]
        if classify(destination, templates[role], role) != state:
            raise SupportError("Destination changed after preflight; no further files changed.")
        if before[role] is not None and read_regular(destination) != before[role]:
            raise SupportError("Destination bytes changed after preflight; no further files changed.")
    for role, state in states.items():
        destination = target / FILES[role]
        if state == "current":
            continue
        assert_directory_chain(target)
        if state == "missing":
            publish_new(destination, templates[role])
        else:
            fd, name = tempfile.mkstemp(prefix=".sol-advisor-", dir=target)
            staged = Path(name)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(templates[role])
                    stream.flush()
                    os.fsync(stream.fileno())
                assert_directory_chain(target)
                if read_regular(destination) != before[role]:
                    raise SupportError("Destination changed; no further files changed.")
                os.replace(staged, destination)
            finally:
                if staged.exists():
                    staged.unlink()
        print(f"{'INSTALLED' if state == 'missing' else 'MIGRATED'}: {destination}")
    retire_terra(retirement)
    if any(classify(target / FILES[role], data, role) != "current" for role, data in templates.items()):
        raise SupportError("Post-install exactness check failed.")
    print("INSTALL PASSED: " + ", ".join(selected) + ". Start a fresh Codex task.")
    if with_astra:
        print("Astra installed, NOT authorized for use. Each consultation needs explicit user authorization.")


def nonempty(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def check_plan(plan: dict) -> dict:
    """Validate a DECLARED plan, not the truth of evidence or user authorization."""
    allowed = {"mode", "difficulty", "risk", "worker", "delegation_benefit", "full_justification", "astra"}
    if not isinstance(plan, dict) or set(plan) - allowed:
        raise SupportError("Invalid plan fields.")
    mode, difficulty, risk = (plan.get(key) for key in ("mode", "difficulty", "risk"))
    if mode not in ("solo", "delegate", "audit", "full"):
        raise SupportError("Unknown delivery mode.")
    if difficulty not in ("bounded", "judgment-heavy") or risk not in ("contained", "material"):
        raise SupportError("Declare difficulty and consequence risk separately.")
    if risk == "material" and mode not in ("audit", "full"):
        raise SupportError("Material consequence risk requires audit or full.")
    worker = plan.get("worker")
    selected = []
    if mode in ("delegate", "full"):
        if worker not in ("luna", "sol-implementer"):
            raise SupportError("Delegation requires a Luna or Sol implementation role.")
        if difficulty == "judgment-heavy" and worker == "luna":
            raise SupportError("Judgment-heavy implementation requires Sol, not forced Luna retries.")
        if not nonempty(plan.get("delegation_benefit")):
            raise SupportError("Delegation must explain work or context it replaces.")
        selected.append(worker)
    elif worker is not None:
        raise SupportError("Solo and audit do not select an implementer.")
    if mode == "full" and not nonempty(plan.get("full_justification")):
        raise SupportError("Full requires an explicit exception justification.")
    if mode in ("audit", "full"):
        selected.append("sol")  # Reviewer alias retained for CLI compatibility.
    consultation = plan.get("astra")
    if consultation is not None:
        if not isinstance(consultation, dict):
            raise SupportError("Invalid Astra consultation packet.")
        if consultation.get("trigger") not in ("irreversible-decision", "structural-disagreement", "diagnostic-blocker"):
            raise SupportError("Astra needs a qualifying consequential uncertainty.")
        for field in ("decision", "user_authorization", "evidence", "counterevidence", "alternatives", "required_checks"):
            if not nonempty(consultation.get(field)):
                raise SupportError(f"Astra packet is missing {field}.")
        number = consultation.get("consultation_number")
        if type(number) is not int or number < 1:
            raise SupportError("Declare the Astra consultation number for this decision.")
        if number > 1 and consultation.get("renewed_authorization") is not True:
            raise SupportError("A repeat consultation requires renewed explicit authorization.")
        selected.append("astra")
    return {"mode": mode, "companion_checks": selected,
            "astra_selected": consultation is not None, "enforcement": "declarative-only"}


def string_or_null(value):
    return value if isinstance(value, str) else None


def policy_type(payload: dict, key: str):
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SupportError("Invalid routing metadata.")
    return string_or_null(value.get("type"))


def inspect_runtime(sessions: Path, thread_id: str) -> dict:
    if not UUID.fullmatch(thread_id):
        raise SupportError("THREAD_ID must be a lowercase UUID.")
    sessions = absolute_path(sessions)
    assert_directory_chain(sessions)
    if not sessions.is_dir():
        raise SupportError("Sessions directory is unavailable.")
    matches = []

    def walk_error(error):
        raise SupportError("Could not enumerate rollout filenames.") from None

    # Enumerate filenames only; never read unrelated sessions or follow links/junctions.
    for root, dirs, files in os.walk(sessions, followlinks=False, onerror=walk_error):
        folder = Path(root)
        dirs[:] = [name for name in dirs if not is_link((folder / name).lstat())]
        for name in files:
            if name.startswith("rollout-") and name.endswith(f"-{thread_id}.jsonl"):
                path = folder / name
                info = path.lstat()
                if not is_link(info) and stat.S_ISREG(info.st_mode):
                    matches.append(path)
    if len(matches) != 1:
        raise SupportError("Expected exactly one rollout filename for the requested thread.")
    session = routing = None
    try:
        with matches[0].open(encoding="utf-8-sig") as stream:
            for line in stream:
                if not line.strip():
                    continue
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise SupportError("Invalid routing metadata.")
                kind = record.get("type")
                if kind not in ("session_meta", "turn_context"):
                    continue
                payload = record.get("payload")
                if not isinstance(payload, dict):
                    raise SupportError("Invalid routing metadata.")
                if kind == "session_meta":
                    if session is not None:
                        raise SupportError("Ambiguous session metadata.")
                    session = {key: string_or_null(payload.get(key)) for key in (
                        "id", "parent_thread_id", "agent_role", "agent_path", "model_provider"
                    )}
                else:
                    current = {
                        "model": string_or_null(payload.get("model")),
                        "effort": string_or_null(payload.get("effort")),
                        "sandbox_policy_type": policy_type(payload, "sandbox_policy"),
                        "permission_profile_type": policy_type(payload, "permission_profile"),
                        "cwd": string_or_null(payload.get("cwd")),
                    }
                    if not current["model"] or not current["effort"]:
                        raise SupportError("Missing model or effort.")
                    if routing is not None and current != routing:
                        raise SupportError("Conflicting routing metadata.")
                    routing = current
    except (OSError, ValueError, UnicodeError):
        raise SupportError("Rollout is unreadable or contains invalid JSON.") from None
    if not session or session["id"] != thread_id or not session["agent_role"] or routing is None:
        raise SupportError("Missing or inconsistent required routing metadata.")
    return {"thread_id": session["id"], "parent_thread_id": session["parent_thread_id"],
            "agent_role": session["agent_role"], "agent_path": session["agent_path"],
            "model_provider": session["model_provider"], **routing}


def verify_runtime(data: dict, role: str, *, require_read_only=False) -> None:
    if role not in ROLES:
        raise SupportError("Unknown runtime role.")
    actual = tuple(data.get(key) for key in ("agent_role", "model", "effort"))
    if actual != PINS[role]:
        raise SupportError("Runtime role/model/effort differs from the selected registry pin.")
    if require_read_only and data.get("sandbox_policy_type") != "read-only":
        raise SupportError("Required read-only sandbox was not observed.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("install", help="Install core roles; Astra is opt-in")
    setup.add_argument("--target-dir")
    setup.add_argument("--check", action="store_true")
    setup.add_argument("--check-role", action="append", choices=tuple(FILES), default=[])
    setup.add_argument("--with-astra", action="store_true", help="Include the optional profile, not spending authorization")
    runtime = commands.add_parser("inspect", help="Print allowlisted routing metadata only")
    runtime.add_argument("--sessions-dir")
    runtime.add_argument("--expect-role", choices=tuple(FILES))
    runtime.add_argument("--require-read-only", action="store_true")
    runtime.add_argument("thread_id")
    commands.add_parser("check-plan", help="Validate a confirmed plan from stdin JSON; no models or mutations")
    args = parser.parse_args(argv)
    try:
        if args.command == "install":
            target = absolute_path(args.target_dir) if args.target_dir is not None else codex_home() / "agents"
            install(target, Path(__file__).resolve().parent.parent / "agents", check=args.check,
                    roles=args.check_role, with_astra=args.with_astra)
        elif args.command == "check-plan":
            print(json.dumps(check_plan(json.load(sys.stdin)), separators=(",", ":")))
        else:
            if args.require_read_only and not args.expect_role:
                raise SupportError("--require-read-only requires --expect-role.")
            sessions = absolute_path(args.sessions_dir) if args.sessions_dir is not None else codex_home() / "sessions"
            data = inspect_runtime(sessions, args.thread_id)
            if args.expect_role:
                verify_runtime(data, args.expect_role, require_read_only=args.require_read_only)
            print(json.dumps(data, ensure_ascii=True, separators=(",", ":")))
        return 0
    except SupportError as error:
        print(f"ERROR: {error}", file=sys.stderr)
    except (OSError, ValueError, TypeError):
        print("ERROR: File, template, or input validation failed; no unsafe fallback attempted.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
