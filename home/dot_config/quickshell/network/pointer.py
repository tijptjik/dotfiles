"""Observe Hyprland pointer/bar geometry without input grabs or network access."""

import json
import os
from pathlib import Path
import socket
import time

from network import module_bounds


def hyprland(command):
    path = Path(os.environ["XDG_RUNTIME_DIR"]) / "hypr" / os.environ["HYPRLAND_INSTANCE_SIGNATURE"] / ".socket.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.5)
        connection.connect(str(path))
        connection.sendall(("j/" + command).encode())
        chunks = []
        while chunk := connection.recv(65536):
            chunks.append(chunk)
    return json.loads(b"".join(chunks))


def logical_monitors(monitors):
    result = []
    for monitor in monitors:
        width, height = monitor["width"], monitor["height"]
        if monitor.get("transform", 0) % 2:
            width, height = height, width
        scale = monitor.get("scale", 1)
        result.append(dict(name=monitor["name"], x=monitor["x"], y=monitor["y"],
                           width=width / scale, height=height / scale))
    return result


def hover_anchor(cursor, monitors, layers, locate_module):
    for monitor in monitors:
        for level in layers.get(monitor["name"], {}).get("levels", {}).values():
            for bar in level:
                if bar.get("namespace") not in ("waybar", "desktop-status", "laptop"):
                    continue
                if not (bar["x"] <= cursor["x"] < bar["x"] + bar["w"]
                        and bar["y"] <= cursor["y"] < bar["y"] + bar["h"]):
                    continue
                bounds = locate_module(bar)
                if bounds and bar["x"] + bounds["x"] <= cursor["x"] < bar["x"] + bounds["x"] + bounds["width"]:
                    return dict(screen=monitor["name"],
                                x=bar["x"] - monitor["x"] + bounds["x"] + bounds["width"] / 2,
                                bottom=bar["y"] - monitor["y"])
    return None


def watch():
    monitors, layers, previous, refreshed = [], {}, None, 0
    cache = {}

    def locate(bar):
        key = (bar.get("pid"), bar["x"], bar["y"], bar["w"], bar["h"])
        value, expires = cache.get(key, (None, 0))
        if time.monotonic() >= expires:
            value = module_bounds(bar)
            cache[key] = (value, time.monotonic() + 1)
        return value

    while True:
        try:
            if time.monotonic() - refreshed >= 1:
                monitors = logical_monitors(hyprland("monitors"))
                layers = hyprland("layers")
                refreshed = time.monotonic()
            cursor = hyprland("cursorpos")
            current = dict(cursor=cursor, monitors=monitors,
                           anchor=hover_anchor(cursor, monitors, layers, locate))
            if current != previous:
                print(json.dumps(current), flush=True)
                previous = current
        except (OSError, ValueError, KeyError):
            if previous is not None:
                print(json.dumps(dict(cursor=None, monitors=[], anchor=None)), flush=True)
                previous = None
            time.sleep(1)
        time.sleep(0.06)


if __name__ == "__main__":
    watch()
