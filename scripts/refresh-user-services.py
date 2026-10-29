#!/usr/bin/env python3
"""Activate changed managed daemons and timers without starting stopped units."""
import argparse
import fcntl
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
IGNORED = {"__pycache__", ".git", ".pytest_cache"}


def systemctl(*args):
    return subprocess.run(["systemctl", "--user", *args], check=True,
                          capture_output=True, text=True, timeout=120).stdout


def properties(unit):
    try:
        output = systemctl("show", unit, "--property=LoadState,ActiveState,Type,ExecStart,NeedDaemonReload")
    except subprocess.CalledProcessError as error:
        if "LoadState=not-found" not in (error.stdout or ""):
            raise
        output = error.stdout
    return dict(line.split("=", 1) for line in output.splitlines()
        if "=" in line)


def fingerprint(unit, inputs, info):
    digest = hashlib.sha256(systemctl("cat", unit).encode())

    def visit(path, ancestors=()):
        digest.update(str(path).encode())
        if not path.exists() and not path.is_symlink():
            digest.update(b"missing")
            return
        if path.is_symlink():
            digest.update(os.readlink(path).encode())
            target = path.resolve(strict=True)
            if target in ancestors:
                raise ValueError(f"Symlink cycle in service inputs: {path}")
            visit(target, (*ancestors, target))
            return
        mode = path.stat().st_mode
        digest.update(str(stat.S_IMODE(mode)).encode())
        if stat.S_ISDIR(mode):
            for child in sorted(path.iterdir()):
                if child.name not in IGNORED:
                    visit(child, ancestors)
        elif stat.S_ISREG(mode):
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        else:
            raise ValueError(f"Non-file service input: {path}")

    # Include systemd's actual entry point as well as wrapper/runtime inputs.
    executables = re.findall(r"(?:^|[ {;])path=([^ ;}]+)", info.get("ExecStart", ""))
    for pattern in sorted(set([*inputs, *executables])):
        expanded = os.path.expanduser(pattern)
        digest.update(expanded.encode())
        for path in sorted(glob.glob(expanded)) or [expanded]:
            visit(Path(path))
    return digest.hexdigest()


def inventory():
    units = json.loads((ROOT / "scripts/user-service-inputs.json").read_text())
    # Timer definitions take effect when rearmed; their running jobs stay alone.
    for path in (ROOT / "native/home/files/.config/systemd/user").glob("*.timer*"):
        units[path.name.removesuffix(".j2")] = []
    return units


def refresh(units, state, *, check=False):
    try:
        saved = json.loads(state.read_text())
        if not isinstance(saved, dict):
            saved = {}
    except (FileNotFoundError, ValueError):
        saved = {}
    print("__tjikup_section__:" + os.environ.get("TJIKUP_SERVICE_SECTION", "Services"), flush=True)
    reloaded = False
    pending = 0
    for unit, inputs in units.items():
        info = properties(unit)
        if not check and info.get("NeedDaemonReload") == "yes":
            systemctl("daemon-reload")
            reloaded = True
            info = properties(unit)
        if info.get("LoadState") != "loaded" or info.get("ActiveState") != "active":
            if not os.environ.get("TJIKUP_HIDE_UNCHANGED_SERVICES"):
                print(f"SKIP    - {unit}  inactive or unavailable", flush=True)
            continue
        if unit.endswith(".service") and info.get("Type") == "oneshot":
            raise ValueError(f"Refusing to restart job: {unit}")
        current = fingerprint(unit, inputs, info)
        if saved.get(unit) == current:
            if not os.environ.get("TJIKUP_HIDE_UNCHANGED_SERVICES"):
                print(f"SKIP    ✓ {unit}  runtime unchanged", flush=True)
            continue
        pending += 1
        if check:
            print(f"CHECK   ✓ {unit}  would refresh", flush=True)
            continue
        # try-restart also preserves a service stopped since the active check.
        systemctl("try-restart", unit)
        if properties(unit).get("ActiveState") != "active":
            raise RuntimeError(f"{unit} did not become active after refresh")
        if fingerprint(unit, inputs, properties(unit)) != current:
            raise RuntimeError(f"{unit} inputs changed during refresh; retry")
        saved[unit] = current
        # Checkpoint each successful unit so a later failure only retries pending ones.
        fd, staged = tempfile.mkstemp(dir=state.parent, prefix=".services-")
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(saved, stream)
                stream.write("\n")
            os.replace(staged, state)
        finally:
            Path(staged).unlink(missing_ok=True)
        print(f"RESTART ✓ {unit}  updated runtime active", flush=True)
    if not pending:
        if reloaded:
            print("__stage_verb__:CONFIG", flush=True)
            print("__stage_note__:unit definitions reloaded", flush=True)
        else:
            print("__stage_verb__:SKIP", flush=True)
            print("__stage_note__:no runtime changes", flush=True)
    elif not check:
        print(f"__stage_note__:{pending} active units refreshed", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="preview without changing services or state")
    parser.add_argument("--unit", action="append", help="refresh only this managed unit (repeatable)")
    args = parser.parse_args()
    units = inventory()
    if args.unit:
        unknown = set(args.unit) - units.keys()
        if unknown:
            parser.error("Unknown managed units: " + ", ".join(sorted(unknown)))
        units = {unit: inputs for unit, inputs in units.items() if unit in args.unit}
    state_dir = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "tjikup"
    state = state_dir / "user-services.json"
    try:
        if args.check:
            refresh(units, state, check=True)
        else:
            state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            with (state_dir / "user-services.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                refresh(units, state)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"FAILED  ✗ Service refresh: {error}", flush=True)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr.strip(), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
