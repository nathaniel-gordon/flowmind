"""Smoke test: python tests/test_smoke.py"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import awe.workflows as wfs
from awe.engine import Engine, Step, Workflow
from awe.exprs import evaluate


def main() -> None:
    state = {"a": {"status": "DONE", "output": {"ok": True, "n": 7}}}
    assert evaluate("steps.a.output.ok == True", state)
    assert evaluate("steps.a.output.n > 5", state)
    assert not evaluate("steps.a.output.n < 5", state)
    assert evaluate("not steps.a.output.n < 5", state)

    # cycle detection
    try:
        Workflow("bad", [Step("x", needs=["y"], run="h"), Step("y", needs=["x"], run="h")]).validate()
        raise AssertionError("cycle must be rejected")
    except ValueError:
        pass

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        # pipeline: clean data -> load branch runs, quarantine skipped
        wfs._FLAKY_STATE["charge_failures_left"] = 1
        eng = Engine(wfs.pipeline_workflow(bad_pct=0.02), wfs.PIPELINE_HANDLERS,
                     Path(td) / "p.json", agent_handler=wfs.offline_agent_handler,
                     auto_approve=True, verbose=False)
        s = eng.run()
        assert s["steps"]["load"] == "DONE" and s["steps"]["quarantine"] == "SKIPPED", s

        # dirty data -> quarantine branch, load skipped, report skipped? (needs load)
        eng2 = Engine(wfs.pipeline_workflow(bad_pct=0.2), wfs.PIPELINE_HANDLERS,
                      Path(td) / "p2.json", agent_handler=wfs.offline_agent_handler,
                      auto_approve=True, verbose=False)
        s2 = eng2.run()
        assert s2["steps"]["quarantine"] == "DONE" and s2["steps"]["load"] == "SKIPPED", s2

        # order flow: flaky payment retried, gate pauses, resume completes
        eng3 = Engine(wfs.order_workflow(order_total=2000), wfs.ORDER_HANDLERS,
                      Path(td) / "o.json", agent_handler=wfs.offline_agent_handler,
                      verbose=False)
        s3 = eng3.run()
        assert s3["steps"]["fraud_review"] == "WAITING_APPROVAL", s3
        assert eng3.state["steps"]["charge"]["attempts"] == 2, "retry expected"
        eng3.approve("fraud_review")
        eng4 = Engine(wfs.order_workflow(order_total=2000), wfs.ORDER_HANDLERS,
                      Path(td) / "o.json", agent_handler=wfs.offline_agent_handler,
                      verbose=False)   # resume from persisted state
        s4 = eng4.run()
        assert s4["steps"]["ship"] == "DONE" and s4["steps"]["notify"] == "DONE", s4

        # cheap order: gate condition unmet -> skipped, still ships
        wfs._FLAKY_STATE["charge_failures_left"] = 0
        eng5 = Engine(wfs.order_workflow(order_total=100), wfs.ORDER_HANDLERS,
                      Path(td) / "o2.json", agent_handler=wfs.offline_agent_handler,
                      verbose=False)
        s5 = eng5.run()
        assert s5["steps"]["fraud_review"] == "SKIPPED" and s5["steps"]["ship"] == "DONE", s5

        mmd = wfs.order_workflow().mermaid()
        assert "flowchart TD" in mmd and "charge --> fraud_review" in mmd
    print("OK - conditions, cycles, retries, gates, resume, branches, mermaid all verified")


if __name__ == "__main__":
    main()


def test_smoke():
    main()
