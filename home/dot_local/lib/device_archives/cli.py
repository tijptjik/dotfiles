"""CLI: backups never synchronize implicitly; plans never modify application data."""

import argparse
import difflib
import json
import os
from pathlib import Path
import subprocess
import sys
import sqlite3
import tempfile

from .core import Archives, ArchiveError, read_json, scan, safe_name, digest


def review(archives, plan_path, file):
    plan = read_json(plan_path)
    if not file:
        report = {
            k: plan[k]
            for k in ("folder", "source", "created_at", "changes", "conflicts")
        }
        report["conflict_details"] = {
            name: {
                "base": plan["base"].get(name),
                "local": plan["local"].get(name),
                "source": plan["incoming"].get(name),
            }
            for name in plan["conflicts"]
        }
        print(json.dumps(report, indent=2))
        return
    safe_name(file)
    if scan(archives.home / plan["folder"], plan["policy"]) != plan["local"]:
        raise ArchiveError("Local state changed; create a new plan")
    with tempfile.TemporaryDirectory(dir=archives.state) as tmp:
        _, manifest = archives.fetch(
            plan["folder"],
            plan["source"],
            Path(tmp),
            plan["ref"]["snapshot"],
            tree=True,
        )
        contents = []
        for root, entries in (
            (archives.home / plan["folder"], plan["local"]),
            (Path(tmp) / "tree", manifest["entries"]),
        ):
            entry = entries.get(file)
            if entry is None:
                contents.append("")
                continue
            if entry["type"] != "file" or entry["size"] > 1024 * 1024:
                raise ArchiveError(
                    "Use the manifest diff for binary, symlink, or large files"
                )
            data = (root / file).read_bytes()
            if b"\0" in data:
                raise ArchiveError("Binary file; compare manifest hashes")
            contents.append(data.decode("utf-8"))
        print(
            "".join(
                difflib.unified_diff(
                    contents[0].splitlines(True),
                    contents[1].splitlines(True),
                    fromfile="local/" + file,
                    tofile=plan["source"] + "/" + file,
                )
            ),
            end="",
        )


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(
        description="Verified device backups and reviewed directory sync"
    )
    parser.add_argument(
        "--config", type=Path, default=Path.home() / ".config/archive-policy.json"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    st = sub.add_parser("status", help="Show policy and local backup/sync receipts")
    st.add_argument(
        "--devices",
        "--targets",
        nargs="+",
        help="Filter folder assignments by device groups or hostnames; does not run remotely",
    )
    dv = sub.add_parser(
        "devices", help="Resolve device selectors and list folder assignments"
    )
    dv.add_argument("selectors", nargs="*", default=["all"])
    sub.add_parser("ready", help="Check whether this device completed its initial sync")
    b = sub.add_parser("backup", help="Snapshot configured folders without syncing")
    b.add_argument("folders", nargs="*")
    p = sub.add_parser(
        "prune", help="Preview retention; --apply deletes superseded snapshots"
    )
    p.add_argument("folders", nargs="*")
    p.add_argument("--apply", action="store_true")
    s = sub.add_parser(
        "sync", help="Write a reviewable three-way plan; does not apply it"
    )
    s.add_argument("folders", nargs="*")
    s.add_argument("--from", dest="source", default="fi")
    s.add_argument("--snapshot")
    a = sub.add_parser(
        "apply", help="Apply a pinned plan after verifying unchanged local files"
    )
    a.add_argument("plan", type=Path)
    a.add_argument(
        "--resolutions",
        type=Path,
        help='JSON mapping each conflict path to "local" or "source"',
    )
    r = sub.add_parser(
        "review", help="List plan changes or show a local/source text diff"
    )
    r.add_argument("plan", type=Path)
    r.add_argument("--file")
    d = sub.add_parser(
        "diff", help="Compare the latest two machine snapshots of a folder"
    )
    d.add_argument("folder")
    d.add_argument("--left", default="fi")
    d.add_argument("--right", default="li")
    d.add_argument(
        "--file", help="Show text diff for one regular file (may contain secrets)"
    )
    r = sub.add_parser(
        "restore", help="Restore selected machine snapshot to a NEW staging directory"
    )
    r.add_argument("folder")
    r.add_argument("--from", dest="source", required=True)
    r.add_argument("--snapshot")
    r.add_argument("--to", type=Path, required=True)
    h = sub.add_parser(
        "history", help="List immutable snapshots for a machine and folder"
    )
    h.add_argument("folder")
    h.add_argument("--from", dest="source", default="fi")
    args = parser.parse_args()
    try:
        config = read_json(args.config.expanduser())
        if config["version"] != 2:
            raise ArchiveError("Unsupported policy version")
        app = Archives(config)
        for name in ("source", "left", "right"):
            if hasattr(args, name):
                setattr(args, name, app.device(getattr(args, name)))
        with app.locked():
            if args.command == "devices":
                for device in app.devices(args.selectors):
                    print(
                        json.dumps(
                            {
                                "device": device,
                                "folders": [
                                    f
                                    for f in config["folders"]
                                    if app.eligible(f, device)
                                ],
                            }
                        )
                    )
            elif args.command == "ready":
                app.ready()
                print("Backup readiness checks passed")
            elif args.command == "status":
                for folder, policy in config["folders"].items():
                    if args.devices and not any(
                        app.eligible(folder, d) for d in app.devices(args.devices)
                    ):
                        continue
                    receipts = list(
                        (app.state / "sync").glob("*/" + digest(folder) + ".json")
                    )
                    print(
                        json.dumps(
                            {
                                "folder": folder,
                                "mode": policy["mode"],
                                "devices": policy.get("devices", []),
                                "backup_here": app.eligible(folder),
                                "backup": read_json(
                                    app.state / "backups" / (digest(folder) + ".json")
                                )
                                if (
                                    app.state / "backups" / (digest(folder) + ".json")
                                ).exists()
                                else None,
                                "sync": [
                                    read_json(p)
                                    | {"entries": "(manifest retained locally)"}
                                    for p in receipts
                                ],
                            }
                        )
                    )
            elif args.command == "backup":
                app.ready()
                folders = args.folders or [
                    f for f in config["folders"] if app.eligible(f)
                ]
                failures = []
                for folder in folders:
                    try:
                        app.backup(folder)
                    except (
                        ArchiveError,
                        OSError,
                        subprocess.CalledProcessError,
                        sqlite3.Error,
                    ) as error:
                        failures.append(folder)
                        print(f"FAILED {folder}: {error}", file=sys.stderr, flush=True)
                if failures:
                    raise ArchiveError("Failed folders: " + ", ".join(failures))
            elif args.command == "prune":
                for folder in args.folders or [
                    f for f in config["folders"] if app.eligible(f)
                ]:
                    print(json.dumps(app.prune(folder, apply=args.apply)))
            elif args.command == "sync":
                folders = args.folders or [
                    f
                    for f, p in config["folders"].items()
                    if p["mode"] in ("sync", "master") and app.eligible(f)
                ]
                for folder in folders:
                    path, plan = app.plan(folder, args.source, args.snapshot)
                    print(
                        json.dumps(
                            {
                                "folder": folder,
                                "plan": str(path),
                                "changes": plan["changes"],
                                "conflicts": plan["conflicts"],
                            },
                            indent=2,
                        )
                    )
            elif args.command == "apply":
                print(
                    json.dumps(
                        app.apply(
                            args.plan,
                            read_json(args.resolutions) if args.resolutions else None,
                        ),
                        indent=2,
                    )
                )
            elif args.command == "review":
                review(app, args.plan, args.file)
            elif args.command == "restore":
                print(
                    json.dumps(
                        app.restore(args.folder, args.source, args.to, args.snapshot),
                        indent=2,
                    )
                )
            elif args.command == "diff":
                result = app.diff(args.folder, args.left, args.right, args.file)
                if args.file:
                    print(result["text_diff"], end="")
                else:
                    print(json.dumps(result, indent=2))
            elif args.command == "history":
                print(
                    "\n".join(
                        x
                        for x in app.store.completed(
                            app.prefix(args.folder, args.source)
                        )
                    )
                )
    except (
        ArchiveError,
        OSError,
        ValueError,
        KeyError,
        subprocess.CalledProcessError,
        sqlite3.Error,
    ) as error:
        print(f"device-archives: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
