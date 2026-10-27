"""Run audited after-hooks as a DAG after Chezmoi's native bootstrap/file phase."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .core import UpdateError
from .dag import Task, run, command as run_command, validate
from tjikup import runtime


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
    child_env = {**env, "FLEET_DEFER_HOOKS": "0", "TJIKUP_NO_SPIN": "1"}
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
                    code = result.returncode
                if code:
                    raise UpdateError(f'{item["id"]}: hook failed ({code})')

            tasks.append(Task(item["id"], action, tuple(item.get("needs", [])),
                              tuple(item.get("resources", [])), exclusive=item.get("exclusive", False)))

        def event(name, result):
            if result.state == "running":
                runtime.stage_started("DAG", name)
                return
            if outputs.get(name):
                print(outputs[name], end="" if outputs[name].endswith("\n") else "\n", flush=True)
            if result.state == "failed":
                runtime.stage_label("FAILED", "✗", name, str(result.error))
            elif result.state == "blocked":
                runtime.stage_skip(name, "workflow failed")
            else:
                runtime.stage_result("DAG", name, f"{result.seconds:.2f}s")

        results = run(tasks, workers=int(os.environ.get("FLEET_JOBS", "4")), event=event)
        failures = [result.error for result in results.values() if result.error]
        if failures:
            raise UpdateError(str(failures[0]))
