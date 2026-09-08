"""Observe Hyprland pointer/bar geometry without input grabs or network access."""

import json
import os
from pathlib import Path
import socket
import select
import sys
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


def fade_settings(animations):
    settings, curves = animations
    by_name = {entry["name"]: entry for entry in settings}
    by_curve = {entry["name"]: entry for entry in curves}
    result = {}
    for direction in ("In", "Out"):
        config = next((by_name[name] for name in ("fadeLayers" + direction, "fadeLayers", "fade", "global")
                       if by_name.get(name, {}).get("overridden")), {})
        curve = by_curve.get(config.get("bezier"), dict(X0=0.22, Y0=1, X1=0.36, Y1=1))
        result[direction.lower()] = dict(duration=round(config.get("speed", 5) * 100) if config.get("enabled", True) else 0,
                                        curve=[curve["X0"], curve["Y0"], curve["X1"], curve["Y1"], 1, 1])
    return result


def waybar_visible():
    """Fail closed if the auto-hide controller has not published visibility."""
    try:
        return (Path(os.environ["XDG_RUNTIME_DIR"]) / "waybar-visible").read_text() == "visible"
    except (OSError, KeyError):
        return False


def hover_anchor(cursor, monitors, layers, locate_module, visible=True):
    if not visible:
        return None
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
    monitors, layers, previous, refreshed, fades = [], {}, None, 0, {}
    dragging = False
    control_open = True
    control_buffer = ""
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
                fades = fade_settings(hyprland("animations"))
                refreshed = time.monotonic()
            cursor = hyprland("cursorpos")
            current = dict(cursor=cursor, monitors=monitors, fades=fades,
                           anchor=None if dragging else hover_anchor(cursor, monitors, layers, locate, waybar_visible()))
            if current != previous:
                print(json.dumps(current), flush=True)
                previous = current
        except (OSError, ValueError, KeyError):
            if previous is not None:
                print(json.dumps(dict(cursor=None, monitors=[], anchor=None)), flush=True)
                previous = None
            time.sleep(1)
        interval = 1 / 120 if dragging else 0.06
        if control_open:
            if select.select([sys.stdin], [], [], interval)[0]:
                chunk = os.read(sys.stdin.fileno(), 4096).decode()
                control_open = bool(chunk)
                control_buffer += chunk
                while "\n" in control_buffer:
                    command, control_buffer = control_buffer.split("\n", 1)
                    dragging = command == "drag-start"
                if not control_open:
                    dragging = False
        else:
            time.sleep(interval)


if __name__ == "__main__":
    watch()
