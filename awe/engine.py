"""Workflow engine: DAG validation, execution with retries, gates, persistence, resume."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .exprs import evaluate

PENDING, RUNNING, DONE, FAILED, SKIPPED, WAITING = \
    "PENDING", "RUNNING", "DONE", "FAILED", "SKIPPED", "WAITING_APPROVAL"


@dataclass
class Step:
    id: str
    kind: str = "python"            # python | agent | approval
    run: str = ""                   # handler name (python), goal (agent)
    needs: list[str] = field(default_factory=list)
    retries: int = 0
    backoff_s: float = 0.05
    when: str = ""                  # condition; unmet -> SKIPPED
    params: dict = field(default_factory=dict)


@dataclass
class Workflow:
    name: str
    steps: list[Step]

    def validate(self) -> None:
        ids = {s.id for s in self.steps}
        if len(ids) != len(self.steps):
            raise ValueError("duplicate step ids")
        for s in self.steps:
            missing = set(s.needs) - ids
            if missing:
                raise ValueError(f"step {s.id} needs unknown steps {missing}")
        order = self.topo_order()
        if len(order) != len(self.steps):
            raise ValueError("workflow contains a cycle")

    def topo_order(self) -> list[Step]:
        by_id = {s.id: s for s in self.steps}
        seen: dict[str, int] = {}
        order: list[Step] = []

        def visit(sid: str) -> None:
            state = seen.get(sid, 0)
            if state == 1:
                raise ValueError("cycle detected")
            if state == 2:
                return
            seen[sid] = 1
            for dep in by_id[sid].needs:
                visit(dep)
            seen[sid] = 2
            order.append(by_id[sid])

        for s in self.steps:
            visit(s.id)
        return order

    def mermaid(self) -> str:
        lines = ["flowchart TD"]
        shape = {"python": ('["', '"]'), "agent": ('(["', '"])'), "approval": ('{{"', '"}}')}
        for s in self.steps:
            o, c = shape.get(s.kind, ('["', '"]'))
            label = f"{s.id}{': ' + s.when if s.when else ''}"
            lines.append(f'    {s.id}{o}{label}{c}')
        for s in self.steps:
            for dep in s.needs:
                lines.append(f"    {dep} --> {s.id}")
        return "\n".join(lines)


class Engine:
    def __init__(self, workflow: Workflow, handlers: dict[str, Callable[..., Any]],
                 state_path: str | Path, agent_handler: Callable[[str, dict], Any] | None = None,
                 auto_approve: bool = False, verbose: bool = True):
        workflow.validate()
        self.wf = workflow
        self.handlers = handlers
        self.agent_handler = agent_handler
        self.state_path = Path(state_path)
        self.auto_approve = auto_approve
        self.verbose = verbose
        self.state: dict = self._load_state()

    # ---------- state ----------
    def _load_state(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        return {"workflow": self.wf.name,
                "steps": {s.id: {"status": PENDING, "attempts": 0, "output": None,
                                 "error": None} for s in self.wf.steps}}

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, indent=2, default=str),
                                   encoding="utf-8")

    def approve(self, step_id: str) -> None:
        st = self.state["steps"][step_id]
        if st["status"] != WAITING:
            raise ValueError(f"step {step_id} is not waiting for approval ({st['status']})")
        st["status"] = DONE
        st["output"] = {"approved": True, "by": "manual"}
        self._save()

    # ---------- execution ----------
    def run(self) -> dict:
        for step in self.wf.topo_order():
            st = self.state["steps"][step.id]
            if st["status"] in (DONE, SKIPPED):
                continue
            deps = [self.state["steps"][d] for d in step.needs]
            if any(d["status"] == FAILED for d in deps):
                st["status"] = SKIPPED
                st["error"] = "upstream failure"
                self._save()
                continue
            if any(d["status"] in (SKIPPED,) for d in deps) and step.kind != "python":
                pass  # allow python join steps after skipped branches
            if step.when:
                try:
                    if not evaluate(step.when, self.state["steps"]):
                        st["status"] = SKIPPED
                        st["error"] = f"condition not met: {step.when}"
                        self._log(f"SKIP {step.id} ({step.when})")
                        self._save()
                        continue
                except KeyError as exc:
                    st["status"] = SKIPPED
                    st["error"] = str(exc)
                    self._save()
                    continue
            if step.kind == "approval":
                if self.auto_approve:
                    st["status"] = DONE
                    st["output"] = {"approved": True, "by": "auto"}
                    self._log(f"GATE {step.id}: auto-approved")
                    self._save()
                    continue
                st["status"] = WAITING
                self._log(f"GATE {step.id}: waiting for approval — resume after `approve`")
                self._save()
                return self.status()
            self._execute(step, st)
            self._save()
            if st["status"] == FAILED:
                self._log(f"FAIL {step.id}: {st['error']}")
        return self.status()

    def _execute(self, step: Step, st: dict) -> None:
        ctx = {"params": step.params,
               "outputs": {d: self.state["steps"][d]["output"] for d in step.needs}}
        for attempt in range(step.retries + 1):
            st["attempts"] += 1
            st["status"] = RUNNING
            try:
                if step.kind == "agent":
                    if self.agent_handler is None:
                        raise RuntimeError("no agent handler configured")
                    out = self.agent_handler(step.run, ctx)
                else:
                    out = self.handlers[step.run](**{**step.params, "ctx": ctx})
                st["status"] = DONE
                st["output"] = out
                st["error"] = None
                self._log(f"DONE {step.id} (attempt {st['attempts']})")
                return
            except Exception as exc:
                st["error"] = f"{type(exc).__name__}: {exc}"
                if attempt < step.retries:
                    time.sleep(step.backoff_s * 2 ** attempt)
        st["status"] = FAILED

    def status(self) -> dict:
        counts: dict[str, int] = {}
        for s in self.state["steps"].values():
            counts[s["status"]] = counts.get(s["status"], 0) + 1
        return {"workflow": self.wf.name, "counts": counts,
                "steps": {k: v["status"] for k, v in self.state["steps"].items()}}

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"  [{self.wf.name}] {msg}")
