#!/usr/bin/python3
"""Update Si's running Compose services and idle Plex, with bounded operations."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt
import fcntl
import http.client
import json
import os
import re
from pathlib import Path
import socket
import subprocess
import sys
import time
from threading import Lock
import xml.etree.ElementTree as ET

COMPOSE = ["docker", "compose", "--project-directory", "/home/m/dockers", "-f", "/home/m/dockers/docker-compose.yaml"]
PREFERENCES = Path("/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Preferences.xml")
BACKUP_RECEIPT = Path("/var/lib/si-app-backup/last-success.json")
STATE = Path("/var/lib/si-app-updates")
MAX_BACKUP_AGE = dt.timedelta(hours=24)
IMAGE_WORKERS = 3
FROZEN_SERVICES = {"ephemera": "final release"}


def report(stage: str, subject: str, note: str) -> None:
    # The Fish hook renders these events with Chezetc's normal status helper.
    print("\t".join(part.replace("\t", " ").replace("\n", " ") for part in (stage, subject, note)), flush=True)


class UpdateFailure(Exception):
    pass


class Updater:
    def __init__(self) -> None:
        self.deadline = time.monotonic() + 1200
        self.failed = False
        STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.record = STATE / dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        self.record.mkdir(mode=0o700)
        self.sequence = 0
        self.log_lock = Lock()

    def command(self, args: list[str], *, timeout: int = 120, accepted: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess:
        remaining = int(self.deadline - time.monotonic())
        if remaining < 1:
            raise UpdateFailure("update time budget exhausted; retry next run")
        try:
            result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=min(timeout, remaining), check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            # Do not dump command arguments, config/environment output, or tokens.
            raise UpdateFailure(f"{args[0]} failed or timed out") from error
        if result.returncode not in accepted:
            with self.log_lock:
                self.sequence += 1
                log = self.record / f"error-{self.sequence}.log"
            log.write_text(result.stdout + result.stderr)
            raise UpdateFailure(f"{args[0]} exited {result.returncode}; {log}")
        return result

    def problem(self, subject: str, error: Exception) -> None:
        self.failed = True
        report("WARN", subject, str(error))

    def backup_ready(self) -> bool:
        try:
            receipt = json.loads(BACKUP_RECEIPT.read_text())
            completed = dt.datetime.fromisoformat(receipt["completedAt"])
            age = dt.datetime.now(dt.timezone.utc) - completed
            if dt.timedelta(0) <= age <= MAX_BACKUP_AGE:
                return True
        except (OSError, ValueError, KeyError, TypeError):
            pass
        self.command(["systemctl", "start", "--no-block", "si-app-backup.service"])
        report("SKIP", "App updates", "waiting for a fresh backup; retry after backup finishes")
        return False

    def sessions(self) -> int | None:
        connection = None
        try:
            token = ET.parse(PREFERENCES).getroot().get("PlexOnlineToken")
            if not token:
                return None
            # Fixed loopback target, no proxy or redirects, token only in a header.
            connection = http.client.HTTPConnection("127.0.0.1", 32400, timeout=8)
            connection.request("GET", "/status/sessions", headers={"X-Plex-Token": token, "Accept": "application/xml"})
            response = connection.getresponse()
            if response.status != 200:
                return None
            payload = response.read(1024 * 1024 + 1)
            if len(payload) > 1024 * 1024:
                return None
            root = ET.fromstring(payload)
            count = int(root.attrib["size"])
            if root.tag != "MediaContainer" or count < 0 or count != len(root):
                return None
            return count
        except (OSError, ValueError, KeyError, ET.ParseError, http.client.HTTPException):
            return None
        finally:
            if connection is not None:
                connection.close()

    def plex_idle(self) -> bool:
        count = self.sessions()
        if count is None:
            report("SKIP", "Plex", "session check unavailable; keeping current version")
        elif count:
            report("SKIP", "Plex", f"{count} active session(s)")
        return count == 0

    def update_plex(self) -> None:
        installed = self.command(["rpm", "-q", "plexmediaserver"], accepted=(0, 1))
        if installed.returncode:
            report("SKIP", "Plex", "not installed")
            return
        old_version = self.command(["rpm", "-q", "--qf", "%{VERSION}", "plexmediaserver"]).stdout.strip()
        if not self.plex_idle():
            return
        available = self.command(["dnf", "-q", "check-upgrade", "plexmediaserver"], accepted=(0, 100))
        if available.returncode == 0:
            report("SKIP", "Plex", "no changes")
            return
        if not self.backup_ready():
            return
        report("SYNC", "Plex", "downloading update")
        self.command(["dnf", "-y", "upgrade", "--downloadonly", "plexmediaserver"], timeout=300)
        # Download first so the last session check is close to the RPM transaction.
        if not self.plex_idle():
            return
        report("UPDATE", "Plex", "no sessions; installing")
        self.command(["dnf", "-y", "--cacheonly", "upgrade", "plexmediaserver"], timeout=300)
        self.command(["systemctl", "is-active", "--quiet", "plexmediaserver"])
        version = self.command(["rpm", "-q", "--qf", "%{VERSION}", "plexmediaserver"]).stdout.strip()
        report("UPDATE", f"Plex ({old_version})", version)

    def containers(self) -> dict[str, list[dict]]:
        ids = self.command(COMPOSE + ["ps", "--status", "running", "--quiet"]).stdout.split()
        if not ids:
            return {}
        rows = json.loads(self.command(["docker", "inspect", *ids]).stdout)
        services: dict[str, list[dict]] = {}
        for row in rows:
            labels = row["Config"].get("Labels") or {}
            if labels.get("com.docker.compose.oneoff", "false").lower() == "true":
                continue
            service = labels.get("com.docker.compose.service")
            if service:
                services.setdefault(service, []).append({
                    "id": row["Id"], "image": row["Image"],
                    "image_ref": row["Config"]["Image"],
                })
        return services

    def image_version(self, image_id: str) -> str:
        """Prefer publisher version metadata; never infer a version from latest."""
        short_id = image_id.removeprefix("sha256:")[:12]
        try:
            raw = self.command(["docker", "image", "inspect", "--format", "{{json .Config.Labels}}", image_id]).stdout
            labels = json.loads(raw) or {}
            version = labels.get("org.opencontainers.image.version") or labels.get("org.label-schema.version")
            if not version:
                match = re.search(r"version:-\s+(\S+)", labels.get("build_version", ""))
                version = match.group(1) if match else None
            if isinstance(version, str) and version.lower() not in {"latest", "main", "master", "develop", "unknown"}:
                version = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", version).strip()
                if version and len(version) <= 40:
                    return version
        except (UpdateFailure, OSError, ValueError, TypeError, AttributeError):
            pass
        return short_id

    def version_change(self, containers: list[dict], image_id: str) -> tuple[str, str]:
        old_ids = sorted({row["image"] for row in containers})
        old_versions = [self.image_version(old_id) for old_id in old_ids]
        new_version = self.image_version(image_id)
        # Rebuilt releases sometimes reuse their version label. Show identities
        # in that case so an update never appears to be version X -> version X.
        if new_version in old_versions:
            old_versions = [old_id.removeprefix("sha256:")[:12] for old_id in old_ids]
            new_version = image_id.removeprefix("sha256:")[:12]
        return ", ".join(dict.fromkeys(old_versions)), new_version

    def prepare_image(self, name: str, spec: dict, containers: list[dict], project: str) -> tuple[str | None, str]:
        """Pull/build without touching containers; only the caller prints status."""
        if name in FROZEN_SERVICES:
            return None, FROZEN_SERVICES[name]
        image = spec.get("image") or f"{project}-{name}"
        if "@sha256:" in image:
            return None, "digest pinned"
        if "build" in spec:
            self.command(COMPOSE + ["build", "--pull", name], timeout=300)
        else:
            self.command(COMPOSE + ["pull", "--policy", "always", name])
        image_id = self.command(["docker", "image", "inspect", "--format", "{{.Id}}", image]).stdout.strip()
        if not image_id:
            raise UpdateFailure("image identity unavailable")
        if all(row["image"] == image_id for row in containers):
            return None, "no changes"
        return image_id, "new image available"

    def update_docker(self) -> None:
        config = json.loads(self.command(COMPOSE + ["config", "--format", "json"]).stdout)
        if config.get("name") != "dockers":
            raise UpdateFailure("unexpected Compose project; refusing updates")
        services = config["services"]
        before = self.containers()
        # Record only rollback image/container metadata, never Compose secrets.
        (self.record / "containers-before.json").write_text(json.dumps(before, indent=2))
        if not before:
            report("SKIP", "Docker images", "no running services")
            return
        changed: dict[str, str] = {}
        report("SYNC", "Docker images", f"checking images; {IMAGE_WORKERS} workers")
        # Registry I/O and local builds are independent. Keep all output and
        # container changes on this thread, reporting workers as they finish.
        with ThreadPoolExecutor(max_workers=IMAGE_WORKERS) as pool:
            futures = {
                pool.submit(self.prepare_image, name, services[name], containers, config["name"]): name
                for name, containers in before.items() if name in services
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    image_id, note = future.result()
                except (UpdateFailure, OSError, ValueError, KeyError, TypeError) as error:
                    report("WARN", name, f"keeping current image; {error}")
                    continue
                if image_id is None:
                    report("SKIP", name, note)
                else:
                    changed[name] = image_id
                    report("CHECK", name, note)
        if not changed or not self.backup_ready():
            return
        self.command(["python3", "/etc/si-provision/storage.py", "--check-docker"])
        # Pin each chosen image ID for this transaction. A concurrent tag pull
        # must not change the image we have just selected for recreation.
        override = self.record / "images.json"
        override.write_text(json.dumps({"services": {name: {"image": image} for name, image in changed.items()}}, indent=2))
        compose = COMPOSE + ["-f", str(override)]
        for name, image_id in sorted(changed.items()):
            try:
                # Leave enough time for the full readiness check before starting
                # another recreation near the end of this pass.
                if self.deadline - time.monotonic() < 210:
                    raise UpdateFailure("insufficient time for recreation; retry next run")
                current = self.containers().get(name, [])
                if {row["id"] for row in current} != {row["id"] for row in before[name]}:
                    self.problem(name, UpdateFailure("container state changed; deferred"))
                    continue
                old_version, new_version = self.version_change(before[name], image_id)
                report("UPDATE", f"{name} ({old_version})", "recreating")
                self.command(compose + ["up", "-d", "--no-deps", "--no-build", "--pull", "never", "--wait", "--wait-timeout", "180", name], timeout=210)
                after = self.containers().get(name, [])
                if len(after) != len(before[name]) or any(row["image"] != image_id for row in after):
                    raise UpdateFailure("running image does not match update")
                report("UPDATE", f"{name} ({old_version})", new_version)
            except UpdateFailure as error:
                self.problem(name, error)
                # A failed migration/health check needs review, not a blind
                # downgrade of potentially migrated application databases.
                break

    def run(self) -> int:
        # Serialize with backup/restore; do not interrupt an active snapshot.
        with open("/run/lock/si-app-backup.lock", "a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                report("SKIP", "App updates", "backup or restore in progress")
                return 0
            for section, subject, operation in (
                    ("Docker services", "Docker images", self.update_docker),
                    ("Native applications", "Plex", self.update_plex)):
                report("SECTION", section, "begin")
                try:
                    operation()
                except (UpdateFailure, OSError, ValueError, KeyError, TypeError) as error:
                    self.problem(subject, error)
        return 1 if self.failed else 0


def main() -> int:
    if socket.gethostname() != "si" or os.geteuid() != 0:
        raise SystemExit("This updater requires root on si")
    os.umask(0o077)
    with open("/run/lock/si-app-updates.lock", "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            report("SKIP", "App updates", "another update is running")
            return 0
        return Updater().run()


if __name__ == "__main__":
    sys.exit(main())
