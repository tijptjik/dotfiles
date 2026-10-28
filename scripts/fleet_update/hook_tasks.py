"""Prepare hook commands once, then run them under a shared scheduler/resource pool."""
from contextlib import redirect_stdout
from dataclasses import fields
import json
import re
from pathlib import Path
import subprocess
import sys

from .core import UpdateError
from .dag import Task, command as run_command
from .icons import HookProgress
from .presentation import ANSI, ROW, DeferredSection, summary
from tjikup import runtime


def rendered_noop(content):
    """Recognize a host guard's empty result, without duplicating role policy.

    Only the exact shared Fish deferral preamble may be ignored. Any other
    executable line keeps the hook active, including an explicit SKIP result.
    """
    lines = [line.strip() for line in content.splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    if (len(lines) >= 3 and
            re.fullmatch(r'if test "\$FLEET_DEFER_(?:SYSTEM_)?HOOKS" = 1', lines[0]) and
            lines[1:3] == ["exit 0", "end"]):
        lines = lines[3:]
    return not lines


def owns_terminal(item):
    marker = item.get("terminal_when_missing")
    return item.get("exclusive", False) or (marker is not None and not Path(marker).expanduser().is_file())


class TerminalOutput:
    """Forward interactive output; the scheduler renders structured status rows."""
    def __init__(self, stream, before_output=lambda: None):
        self.stream = stream
        self.before_output = before_output

    def write(self, value):
        if ROW.match(ANSI.sub("", value).strip()):
            return len(value)
        if ANSI.sub("", value).strip():
            self.before_output()
        return self.stream.write(value)

    def __getattr__(self, name):
        return getattr(self.stream, name)


class HookTasks:
    def __init__(self, temporary, log_dir, env):
        self.temporary, self.log_dir = Path(temporary), Path(log_dir)
        self.env = {**env, "FLEET_DEFER_HOOKS": "0", "FLEET_DEFER_SYSTEM_HOOKS": "0",
                    "TJIKUP_NO_SPIN": "1", "TJIKUP_STATUS_LINES": "1", "TJIKUP_NO_SECTIONS": "1"}
        self.progress = HookProgress()
        self.items, self.outputs, self.results = {}, {}, {}
        self.inactive = set()

    def prepare(self, repo, plan, render, *, prefix="", root=False, needs=()):
        """All rendering and syntax checks finish before callers dispatch tasks."""
        prepared, rendered = [], {}
        for item in plan:
            name = prefix + item["id"]
            if item["file"] not in rendered:
                rendered[item["file"]] = render(item)
            content = rendered[item["file"]]
            inactive = not item["file"].endswith(".py") and rendered_noop(content)
            if inactive:
                self.inactive.add(name)
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
            if item.get("status_sections"):
                # The parent records and decorates the individual service rows.
                env["TJIKUP_STATUS_SECTIONS"] = "1"
                env.pop("TJIKUP_REPORT_FILE", None)
            if root:
                # Match Chezetc's root execution and SUDO_USER identity. Do not
                # forward arbitrary user credentials or XDG/HOME into root.
                names = ("PATH", "TJIKUP_COLOR", "TJIKUP_NO_SPIN", "TJIKUP_COLUMNS",
                         "TJIKUP_REPORT_FILE", "TJIKUP_STATUS_LINES", "TJIKUP_NO_SECTIONS",
                         "TJIKUP_STATUS_SECTIONS",
                         "FLEET_DEFER_SYSTEM_HOOKS", *item.get("env", {}))
                command = ["sudo", "-n", "-H", "--", "env", *[f"{key}={env[key]}" for key in names if key in env], *command]

            def action(item=item, command=command, name=name, env=env):
                if owns_terminal(item):
                    lines = []

                    def capture(line):
                        lines.append(line)
                        return line

                    with redirect_stdout(TerminalOutput(sys.stdout, self.progress.show_section)):
                        code = runtime.run_stream(command, repo, env=env, timeout=item.get("timeout", 1800),
                                                  check=False, formatter=capture)
                    self.outputs[name] = "\n".join(lines)
                else:
                    result = run_command(command, cwd=repo, env=env, timeout=item.get("timeout", 1800))
                    self.outputs[name] = result.stdout
                    code = result.returncode
                log = self.log_dir / (name.replace(":", "-") + ".log")
                log.write_text(self.outputs[name])
                log.chmod(0o600)
                if code:
                    raise UpdateError(f"{name}: hook failed ({code})")

            task = Task(name, action, tuple(prefix + n for n in item.get("needs", [])) + tuple(needs),
                        tuple(item.get("resources", [])), check=lambda inactive=inactive: inactive,
                        exclusive=lambda item=item, inactive=inactive: not inactive and owns_terminal(item))
            self.items[name] = item
            prepared.append(task)
        return prepared

    def event(self, name, result):
        if name in self.inactive:
            if result.state != "running":
                self.results[name] = result
            return
        item = self.items.get(name, {"label": name})
        label, verb = item.get("label", name), item.get("verb", "UPDATE")
        if result.state == "running":
            if not owns_terminal(item):
                self.progress.start(name, label, verb)
            return
        self.results[name] = result
        output = self.outputs.get(name, "")
        if item.get("status_sections") and result.state in {"done", "failed"}:
            self.progress.discard(name)
            rendered = self.service_sections(name, output)
            if result.state == "done" and rendered:
                return
        outcome = summary(output)
        if not output.strip() and name in {'system:files', 'home:chezetc-wrapper', 'chezetc-wrapper'}:
            outcome.verb = verb
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

    def service_sections(self, name, output):
        """Replay a completed server update atomically, retaining its headings.

        Child hooks still run buffered and cannot interleave a Docker heading
        with another task's rows. The private log retains all pending rows.
        """
        rendered = False
        section = None

        def show_section():
            self.progress.show_section()
            if section:
                section.show()

        with self.progress.output():
            for index, line in enumerate(ANSI.sub("", output).splitlines()):
                if line.startswith("__tjikup_section__:"):
                    title = line.partition(":")[2]
                    if title in {"Docker services", "Native applications"}:
                        section = DeferredSection(title)
                        rendered = True
                    continue
                match = ROW.match(line.strip())
                if match:
                    verb, icon, content = match.groups()
                    if icon == "...":
                        continue
                    fields = re.split(r"\s{2,}", content, maxsplit=1)
                    note = fields[1] if len(fields) == 2 else ""
                    if runtime.outcome_verb(verb, icon, note) != "SKIP":
                        show_section()
                    self.progress.finish(f"{name}:{index}", fields[0], verb=verb,
                                         icon=icon, note=note)
                    rendered = True
                elif line.strip():
                    show_section()
                    print(line, flush=True)
        return rendered

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
