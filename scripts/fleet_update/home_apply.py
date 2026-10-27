"""Run audited after-hooks as a DAG after Chezmoi's native bootstrap/file phase."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .core import UpdateError
from .dag import Task, run, command as run_command, validate
from tjikup import runtime
from tjikup.progress import Progress
from .presentation import summary


def load_plan(repo):
    manifest = json.loads(Path(__file__).with_name("home-plan.json").read_text())
    directory = repo / "home/.chezmoiscripts"
    actual = {path.name for path in directory.glob("run_after_*")}
    expected = {item["file"] for item in manifest}
    validate([Task(item["id"], None, tuple(item.get("needs", []))) for item in manifest])
    if actual != expected and directory.exists():
        raise UpdateError("After-hook manifest mismatch; update home-plan.json: " +
                          ", ".join(sorted(actual ^ expected)))
    return manifest


def apply_hooks(repo, env):
    manifest = load_plan(repo)
    directory = repo / "home/.chezmoiscripts"
    actual = {path.name for path in directory.glob("run_after_*")}
    # All scripts are rendered before starting mutations; errors fail the plan.
    tasks, outputs = [], {}
    child_env = {**env, "FLEET_DEFER_HOOKS": "0", "TJIKUP_NO_SPIN": "1",
                 "TJIKUP_STATUS_LINES": "1", "TJIKUP_NO_SECTIONS": "1"}
    log_root = Path(env.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "tjikup/logs"
    log_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    log_dir = Path(tempfile.mkdtemp(prefix="home-", dir=log_root))
    progress = Progress()
    with tempfile.TemporaryDirectory(prefix="tjikup-hooks-") as temporary:
        for item in manifest:
            source = directory / item["file"]
            if not source.exists():
                # An absent manifest member is an incompatible checkout, not a skip.
                if actual:
                    raise UpdateError(f"missing hook: {source}")
                continue
            if source.suffix == ".tmpl":
                rendered = subprocess.run(
                    ["chezmoi", "--source", str(repo / "home"), "execute-template", "--file", str(source)],
                    env=child_env, capture_output=True, text=True, timeout=60,
                )
                if rendered.returncode:
                    raise UpdateError(f"cannot render {source.name}: {rendered.stderr}")
                content = rendered.stdout
            else:
                content = source.read_text()
            script = Path(temporary) / source.name.removesuffix(".tmpl")
            if not item.get("exclusive") and not script.name.endswith(".py"):
                # Worker hooks cannot own a password prompt while peers are running.
                content = "function sudo; command sudo -n $argv; end\n" + content
            script.write_text(content)
            interpreter = "python3" if script.suffix == ".py" else "fish"
            command = [interpreter, str(script)]
            if interpreter == "fish":
                command.insert(1, "--no-config")
            syntax = subprocess.run(
                ["fish", "--no-config", "--no-execute", str(script)] if interpreter == "fish"
                else ["python3", "-c", "import ast,sys; ast.parse(open(sys.argv[1]).read())", str(script)],
                capture_output=True, text=True,
            )
            if syntax.returncode:
                raise UpdateError(f"invalid rendered hook {source.name}: {syntax.stderr}")

            def action(item=item, command=command):
                if item.get("exclusive"):
                    code = runtime.run_stream(command, repo, env=child_env,
                                              timeout=1800, check=False)
                else:
                    result = run_command(command, cwd=repo, env=child_env, timeout=1800)
                    outputs[item["id"]] = result.stdout
                    log_file = log_dir / (item["id"] + ".log")
                    log_file.write_text(result.stdout)
                    log_file.chmod(0o600)
                    code = result.returncode
                if code:
                    raise UpdateError(f'{item["id"]}: hook failed ({code})')

            tasks.append(Task(item["id"], action, tuple(item.get("needs", [])),
                              tuple(item.get("resources", [])), exclusive=item.get("exclusive", False)))

        def event(name, result):
            item = next(item for item in manifest if item["id"] == name)
            label = item.get("label", name)
            verb = item.get("verb", "UPDATE")
            if result.state == "running":
                if not item.get("exclusive"):
                    progress.start(name, label, verb)
                return
            output = outputs.get(name, "")
            note, warnings = summary(output)
            if result.state == "failed":
                progress.finish(name, label, verb="FAILED", icon="✗", note=str(result.error))
                with progress.output():
                    if output:
                        print(output, end="" if output.endswith("\n") else "\n", flush=True)
                        print(f"Log: {log_dir / (name + '.log')}", flush=True)
            elif result.state == "blocked":
                progress.finish(name, label, verb="SKIP", icon="-", note="workflow failed")
            else:
                progress.finish(name, label, verb=verb, icon="!" if warnings else "✓",
                                note=note or f"{result.seconds:.2f}s")
                if warnings:
                    with progress.output():
                        print("\n".join(warnings), flush=True)

        # Completion order crosses hook-specific sections, including streamed
        # exclusive hooks. Keep all deferred output under one accurate heading.
        runtime.section_header("Home configuration")
        with progress:
            results = run(tasks, workers=int(os.environ.get("FLEET_JOBS", "4")), event=event)
        failures = [result.error for result in results.values() if result.error]
        if failures:
            raise UpdateError(str(failures[0]))
