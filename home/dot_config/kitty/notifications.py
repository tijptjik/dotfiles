"""Route Tjikup's SSH status cards to the local notification service."""

from pathlib import Path
import sys


def main(command):
    # Kitty calls this hook before its normal desktop delivery. Suppress that
    # delivery only after the local service accepts the structured status card.
    runner = str(Path.home() / ".local/bin/tjikup")
    sys.path.insert(0, runner)
    try:
        from tjikup.notifications import ssh_notification_filter
        return ssh_notification_filter(command)
    except (ImportError, OSError, ValueError, AttributeError):
        return False
    finally:
        sys.path.remove(runner)
