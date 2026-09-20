#!/usr/bin/env python3
"""Shell-free companion installation and allowlisted runtime inspection (Python 3.11+).

No third-party packages, Codex configuration edits, or model/effort overrides.
The POSIX helpers remain supported; Windows entry points call this implementation.
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

FILES = {
    "luna": "sol-advisor-luna-implementer.toml",
    "terra": "sol-advisor-terra-implementer.toml",
    "sol": "sol-advisor-sol-reviewer.toml",
}
# Same immutable v0.2.0, v0.5.0, and v0.6.0 fingerprints as install-agents.sh.
LEGACY = {
    "luna": {
        "fba1b42849d93737e83b094a2ab0b1611f87ac37db7438c8bbdf581f0813f8eb",
        "5cfaf77f14757074ca5d3cfecd0b8204c91dc14eff8d6119985c64416ddf4853",
        "12fa9180a292876e6731bc325779123bcd931c3caa902fbf90d676a31833be84",
    },
    "terra": {
        "4425a8c1f21ce8c6af93f96adc253bbc33ea301f1389b3fa8ce350be08584eca",
        "dc329fe87f6f6610c13157ec16432f91c79cf5a541ee3e7448f6afb165dd18ce",
        "77ed2f36bb149da5d9032230c3d6f5e5cd56b059b3fa5f59085249bba06e1f3a",
    },
    "sol": {"0333acf0ef562bcfebd06009ac09bd1dd8cbc04c4cf28e08e9e049bd8bf202d2"},
}
PINS = {
    "luna": ("sol_advisor_luna_implementer", "gpt-5.6-luna", "max"),
    "terra": ("sol_advisor_terra_implementer", "gpt-5.6-terra", "max"),
    "sol": ("sol_advisor_sol_reviewer", "gpt-5.6-sol", "xhigh"),
}
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")


class SupportError(Exception):
    """A safe operator-facing failure, with no rollout payload attached."""


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
    # Python 3.11 lacks Path.is_junction(). Reparse points include Windows junctions.
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def assert_directory_chain(path: Path) -> None:
    """Reject links/junctions and non-directories, including existing ancestors."""
    for item in (path, *path.parents):
        info = lstat_or_none(item)
        if info is not None and (is_link(info) or not stat.S_ISDIR(info.st_mode)):
            raise SupportError(f"Unsafe directory (link, reparse point, or non-directory): {item}")


def absolute_path(value: str | Path) -> Path:
    if not str(value).strip():
        raise SupportError("Directory must not be empty.")
    return Path(os.path.abspath(os.path.expanduser(value)))


def read_templates(directory: Path) -> dict[str, bytes]:
    templates = {}
    for role, filename in FILES.items():
        path = directory / filename
        info = lstat_or_none(path)
        if info is None or is_link(info) or not stat.S_ISREG(info.st_mode):
            raise SupportError(f"Shipped template is missing or unsafe: {path}")
        data = path.read_bytes()
        parsed = tomllib.loads(data.decode("utf-8"))
        actual = tuple(parsed.get(key) for key in ("name", "model", "model_reasoning_effort"))
        if actual != PINS[role] or (role == "sol" and parsed.get("sandbox_mode") != "read-only"):
            raise SupportError(f"Shipped template has unexpected role/model/effort pins: {path}")
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
    return "legacy" if hashlib.sha256(installed).hexdigest() in LEGACY[role] else "conflict"


def install(target: Path, template_dir: Path, *, check=False, roles=()) -> None:
    selected = tuple(dict.fromkeys(roles)) or tuple(FILES)
    if any(role not in FILES for role in selected):
        raise SupportError("Unknown role; expected luna, terra, or sol.")
    check = check or bool(roles)
    target = absolute_path(target)
    if target.parent == target:
        raise SupportError("Refusing to use a filesystem root as an agent directory.")
    assert_directory_chain(target)
    templates = read_templates(template_dir)
    states = {role: classify(target / FILES[role], templates[role], role) for role in selected}
    allowed = {"current"} if check else {"missing", "current", "legacy"}
    failures = [f"{role}: {state}" for role, state in states.items() if state not in allowed]
    if failures:
        raise SupportError("Preflight failed; no files changed: " + "; ".join(failures))
    if check:
        print("CHECK PASSED: selected role templates match exactly.")
        return
    # Preflight every role before creating directories or installing any template.
    target.mkdir(parents=True, exist_ok=True)
    assert_directory_chain(target)
    for role, expected in states.items():
        if classify(target / FILES[role], templates[role], role) != expected:
            raise SupportError("Destination changed after preflight; no further files changed.")
    for role, state in states.items():
        destination = target / FILES[role]
        if state == "current":
            print(f"ALREADY CURRENT: {destination}")
            continue
        # Stage a complete, byte-preserving file on the destination filesystem.
        fd, staged_name = tempfile.mkstemp(prefix=".sol-advisor-agent-", dir=target)
        staged = Path(staged_name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(templates[role])
                stream.flush()
                os.fsync(stream.fileno())
            assert_directory_chain(target)
            if classify(destination, templates[role], role) != state:
                raise SupportError("Destination changed after preflight; no further files changed.")
            if state == "missing":
                # Windows rename refuses an existing destination. POSIX rename does
                # not, so use an exclusive hard-link publication there instead.
                if os.name == "nt":
                    os.rename(staged, destination)
                else:
                    os.link(staged, destination)
            else:
                # As in the POSIX installer, migrate ONLY exact historical bytes.
                os.replace(staged, destination)
            print(f"{'INSTALLED' if state == 'missing' else 'MIGRATED'}: {destination}")
        finally:
            if staged.exists():
                staged.unlink()
    if any(classify(target / FILES[role], data, role) != "current" for role, data in templates.items()):
        raise SupportError("Post-install exactness check failed.")
    print("INSTALL PASSED: Luna, Terra, and Sol match exactly. Start a fresh Codex task.")


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

    # Enumerate filenames only; never read unrelated sessions. Explicitly prune
    # junctions as well as symlinks, including on Python 3.11 for Windows.
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
    session = None
    routing = None
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
                    # Retain only allowlisted fields, never messages or credentials.
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
        # Do not echo parse exceptions: they may contain private rollout text.
        raise SupportError("Rollout is unreadable or contains invalid JSON.") from None
    if not session or session["id"] != thread_id or not session["agent_role"] or routing is None:
        raise SupportError("Missing or inconsistent required routing metadata.")
    return {
        "thread_id": session["id"],
        "parent_thread_id": session["parent_thread_id"],
        "agent_role": session["agent_role"],
        "agent_path": session["agent_path"],
        "model_provider": session["model_provider"],
        **routing,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("install", help="Install or verify companion agent templates")
    setup.add_argument("--target-dir")
    setup.add_argument("--check", action="store_true")
    setup.add_argument("--check-role", action="append", choices=tuple(FILES), default=[])
    runtime = commands.add_parser("inspect", help="Print allowlisted routing metadata only")
    runtime.add_argument("--sessions-dir")
    runtime.add_argument("thread_id")
    args = parser.parse_args(argv)
    try:
        if args.command == "install":
            target = absolute_path(args.target_dir) if args.target_dir is not None else codex_home() / "agents"
            install(target, Path(__file__).resolve().parent.parent / "agents", check=args.check, roles=args.check_role)
        else:
            sessions = absolute_path(args.sessions_dir) if args.sessions_dir is not None else codex_home() / "sessions"
            print(json.dumps(inspect_runtime(sessions, args.thread_id), ensure_ascii=True, separators=(",", ":")))
        return 0
    except SupportError as error:
        print(f"ERROR: {error}", file=sys.stderr)
    except (OSError, ValueError):
        print("ERROR: File operation or template validation failed; no unsafe fallback attempted.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
