"""Place the audio panel and route existing PulseAudio-compatible playback."""
import json
import fcntl
import os
from pathlib import Path
import subprocess
import sys


def pactl(*args):
    return subprocess.check_output(["pactl", *args], text=True, stderr=subprocess.PIPE, timeout=5)


def master(action):
    # Serialize wheel events so fast scrolling cannot read the same old volume.
    with open(Path(os.environ["XDG_RUNTIME_DIR"]) / "audio-master.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        sinks = json.loads(pactl("-f", "json", "list", "sinks"))
        default = pactl("get-default-sink").strip()
        active = next((s for s in sinks if s["name"] == default), None)
        if active is None:
            raise ValueError("No active output device is available.")
        if action == "mute":
            pactl("set-sink-mute", active["name"], "0" if active["mute"] else "1")
        else:
            channels = list(active["volume"].values())
            current = sum(v["value"] for v in channels) / len(channels) / 65536 * 100
            volume = max(0, min(100, round(current) + int(action)))
            pactl("set-sink-volume", active["name"], str(volume) + "%")


def route(name):
    if not name:
        raise ValueError("The selected output is unavailable.")
    sinks = json.loads(pactl("-f", "json", "list", "sinks"))
    if not any(s["name"] == name for s in sinks):
        raise ValueError("The selected output was disconnected.")
    pactl("set-default-sink", name)
    failures = []
    for stream in json.loads(pactl("-f", "json", "list", "sink-inputs")):
        try:
            pactl("move-sink-input", str(stream["index"]), name)
        except subprocess.CalledProcessError:
            # Clients may disappear between enumeration and moving.
            remaining = json.loads(pactl("-f", "json", "list", "sink-inputs"))
            if any(s["index"] == stream["index"] for s in remaining):
                failures.append(str(stream["index"]))
    if failures:
        raise ValueError("Output changed; could not move playback clients: " + ", ".join(failures))


if __name__ == "__main__":
    try:
        if sys.argv[1] == "anchor":
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "network"))
            import network
            network.MODULE_KIND = "audio"
            print(json.dumps(network.anchor()))
        elif sys.argv[1] == "master":
            master(sys.argv[2])
        elif sys.argv[1] == "route":
            route(sys.argv[2])
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(str(error))
        sys.exit(1)
