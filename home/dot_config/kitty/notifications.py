"""Forward Tjikup display metadata to the local native runner."""
import json
import subprocess


def main(command):
    if command.application_name != "Tjikup":
        return False
    try:
        prefix = "tjikup-status-v1:"
        raw = next(item[len(prefix):] for item in command.notification_types
                   if item.startswith(prefix) and len(item) <= 16384)
        payload = json.loads(raw)
        if set(payload) != {"data", "body"}:
            return False
        payload["title"] = command.title
        result = subprocess.run(["tjikup", "notify", "--stdin"],
                                input=json.dumps(payload), text=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=4, check=False)
        return result.returncode == 0
    except (StopIteration, OSError, ValueError, TypeError, AttributeError,
            subprocess.TimeoutExpired):
        return False
