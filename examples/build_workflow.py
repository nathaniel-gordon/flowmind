"""Example: Actor Model with Mailboxes & Deterministic Workflow Engine.

Run directly:
    python examples/build_workflow.py

This script demonstrates the library-first interface for stateful agentic workflows:
  - Step isolation via message-driven actor mailboxes
  - Resumable state persistence across crashes / approval gates
  - Branching, retries, and automated Mermaid DAG export
"""
from __future__ import annotations

from pathlib import Path

from awe.engine import Engine
from awe.workflows import (
    ORDER_HANDLERS,
    PIPELINE_HANDLERS,
    offline_agent_handler,
    order_workflow,
    pipeline_workflow,
)

OUT = Path(__file__).parent.parent / "output"
OUT.mkdir(exist_ok=True)

# ── 1. Pipeline Workflow Execution (Actor Message Passing) ───────────────────
print("=================================================================")
print("  STEP 1: Data Pipeline Workflow (Clean Data -> Load Branch)    ")
print("=================================================================")
state_pipeline = OUT / "data-pipeline.state.json"
if state_pipeline.exists():
    state_pipeline.unlink()

engine_pipeline = Engine(
    pipeline_workflow(),
    PIPELINE_HANDLERS,
    state_pipeline,
    agent_handler=offline_agent_handler,
    auto_approve=True,
)
res1 = engine_pipeline.run()
print(f"Pipeline Result Status: {res1}")

# ── 2. Order Fulfillment with Approval Gate & State Resume ─────────────────
print("\n=================================================================")
print("  STEP 2: Order Fulfillment with Human Approval Gate & Resume   ")
print("=================================================================")
state_order = OUT / "order-fulfillment.state.json"
if state_order.exists():
    state_order.unlink()

# Run until paused at fraud review gate
engine_order = Engine(
    order_workflow(),
    ORDER_HANDLERS,
    state_order,
    agent_handler=offline_agent_handler,
    auto_approve=False,
)
status_paused = engine_order.run()
print(f"Workflow paused at gate: {status_paused}")

# Simulate human supervisor approving the gate
print("... [Human Supervisor] Approving 'fraud_review' step ...")
engine_order.approve("fraud_review")

# Resume execution from checkpointed state
print("... Resuming actor engine from mailbox state checkpoint ...")
engine_resumed = Engine(
    order_workflow(),
    ORDER_HANDLERS,
    state_order,
    agent_handler=offline_agent_handler,
    auto_approve=False,
)
res2 = engine_resumed.run()
print(f"Final Resumed Status: {res2}")

# ── 3. Mermaid DAG Generation ───────────────────────────────────────────────
print("\n=================================================================")
print("  STEP 3: Mermaid Workflow DAG Topology                         ")
print("=================================================================")
mermaid_order = order_workflow().mermaid()
print(mermaid_order)

(OUT / "order_dag.mmd").write_text(mermaid_order, encoding="utf-8")
(OUT / "pipeline_dag.mmd").write_text(pipeline_workflow().mermaid(), encoding="utf-8")
print(f"\nArtifacts saved: State files and Mermaid DAGs -> {OUT}")
