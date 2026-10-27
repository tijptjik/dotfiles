"""Prepare hook commands once, then run them under a shared scheduler/resource pool."""
from dataclasses import fields
import json
from pathlib import Path
import subprocess

from .core import UpdateError
from .dag import Task, command as run_command
from .presentation import summary
from tjikup import runtime
from tjikup.progress import Progress


def owns_terminal(item):
    marker = item.get("terminal_when_missing")
    return item.get("exclusive", False) or (marker is not None and not Path(marker).expanduser().is_file())


class HookTasks:
    def __init__(self, temporary, log_dir, env):
        self.temporary, self.log_dir = Path(temporary), Path(log_dir)
        self.env = {**env, "FLEET_DEFER_HOOKS": "0", "FLEET_DEFER_SYSTEM_HOOKS": "0",
                    "TJIKUP_NO_SPIN": "1", "TJIKUP_STATUS_LINES": "1", "TJIKUP_NO_SECTIONS": "1"}
        self.progress = Progress()
        self.items, self.outputs, self.results = {}, {}, {}

    def prepare(self, repo, plan, render, *, prefix="", root=False, needs=()):
        """All rendering and syntax checks finish before callers dispatch tasks."""
        prepared, rendered = [], {}
        for item in plan:
            name = prefix + item["id"]
            if item["file"] not in rendered:
                rendered[item["file"]] = render(item)
            content = rendered[item["file"]]
            script = self.temporary / (name.replace(":", "-") + (".py" if item["file"].endswith(".py") else ".fish"))
            if script.suffix == ".fish" and not item.get("exclusive") and not item.get("terminal_when_missing"):
                content = "function sudo; command sudo -n $argv; end\n" + content
            script.write_text(content)
            script.chmod(0o600)
            syntax = (["fish", "--no-config", "--no-execute", str(script)] if script.suffix == ".fish" else
                      ["python3", "-c", "import ast,sys; ast.parse(open(sys.argv[1]).read())", str(script)])
            result = subprocess.run(syntax, capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise UpdateError(f"invalid rendered hook {item['file']}: {result.stderr}")
            command = (["fish", "--no-config"] if script.suffix == ".fish" else ["python3"]) + [str(script)]
            env = {**self.env, **item.get("env", {})}
            if root:
                # Match Chezetc's root execution and SUDO_USER identity. Do not
                # forward arbitrary user credentials or XDG/HOME into root.
                names = ("PATH", "TJIKUP_COLOR", "TJIKUP_NO_SPIN", "TJIKUP_COLUMNS",
                         "TJIKUP_REPORT_FILE", "TJIKUP_STATUS_LINES", "TJIKUP_NO_SECTIONS",
                         "FLEET_DEFER_SYSTEM_HOOKS", *item.get("env", {}))
                command = ["sudo", "-n", "-H", "--", "env", *[f"{key}={env[key]}" for key in names if key in env], *command]

            def action(item=item, command=command, name=name, env=env):
                if owns_terminal(item):
                    lines = []

                    def capture(line):
                        lines.append(line)
                        return line

                    code = runtime.run_stream(command, repo, env=env, timeout=item.get("timeout", 1800),
                                              check=False, formatter=capture)
                    self.outputs[name] = "\n".join(lines)
                else:
                    result = run_command(command, cwd=repo, env=env, timeout=item.get("timeout", 1800))
                    self.outputs[name] = result.stdout
                    log = self.log_dir / (name.replace(":", "-") + ".log")
                    log.write_text(result.stdout)
                    log.chmod(0o600)
                    code = result.returncode
                if code:
                    raise UpdateError(f"{name}: hook failed ({code})")

            task = Task(name, action, tuple(prefix + n for n in item.get("needs", [])) + tuple(needs),
                        tuple(item.get("resources", [])), exclusive=lambda item=item: owns_terminal(item))
            self.items[name] = item
            prepared.append(task)
        return prepared

    def event(self, name, result):
        item = self.items.get(name, {"label": name})
        label, verb = item.get("label", name), item.get("verb", "UPDATE")
        if result.state == "running":
            if not owns_terminal(item):
                self.progress.start(name, label, verb)
            return
        self.results[name] = result
        output = self.outputs.get(name, "")
        outcome = summary(output)
        if result.state == "failed":
            self.progress.finish(name, label, verb="FAILED", icon="✗", note=str(result.error))
            with self.progress.output():
                if output:
                    print(output, end="" if output.endswith("\n") else "\n", flush=True)
                    print(f"Log: {self.log_dir / (name.replace(':', '-') + '.log')}", flush=True)
        elif result.state == "blocked":
            self.progress.finish(name, label, verb="SKIP", icon="-", note="workflow failed")
        else:
            self.progress.finish(name, label, verb="SKIP" if result.state == "skipped" else outcome.verb,
                                 icon=outcome.icon, note=outcome.note or f"{result.seconds:.2f}s")
            if outcome.warnings:
                with self.progress.output():
                    print("\n".join(outcome.warnings), flush=True)

    def save_timings(self, tasks, **metadata):
        records = []
        for task in tasks:
            result = self.results.get(task.name)
            values = ({field.name: getattr(result, field.name) for field in fields(result) if field.name != "error"}
                      if result else {"state": "interrupted"})
            records.append({"id": task.name, "needs": list(task.needs), "resources": list(task.resources), **values})
        path = self.log_dir / "timings.json"
        path.write_text(json.dumps({"version": 1, **metadata, "tasks": records}, indent=2) + "\n")
        path.chmod(0o600)
        return path
