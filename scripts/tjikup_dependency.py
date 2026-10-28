"""Check the runner dependency before starting or installing fleet commands."""

import inspect
from pathlib import Path
import shlex
import sys


def check_runtime():
    try:
        from tjikup.progress import Progress
        from tjikup.runtime import run_stream
        if "stderr_handler" not in inspect.signature(run_stream).parameters:
            raise ModuleNotFoundError("stderr relay is unavailable", name="tjikup.runtime")
    except ModuleNotFoundError as error:
        if error.name not in {"tjikup", "tjikup.progress", "tjikup.runtime"}:
            raise
        installer = Path(__file__).resolve().with_name("install-tjikup.sh")
        print(
            "fleet-update: the Tjikup runner is missing or outdated "
            f"({error.name} is unavailable).\n"
            "Update your tjikOS checkout (TJIKOS_REPO or ~/code/tjikos), "
            "then reinstall the runner:\n"
            f"  bash {shlex.quote(str(installer))}\n"
            "Updating dotfiles alone does not update the installed runner. "
            "See docs/tjikup.md#installation-and-migration.",
            file=sys.stderr,
        )
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(0 if check_runtime() else 1)
