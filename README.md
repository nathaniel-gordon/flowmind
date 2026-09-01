<div align="center">

# 🌊 FlowMind

**Actor-model workflow engine with automatic rollback sagas for multi-agent pipelines.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-Passing-22c55e?style=for-the-badge&logo=pytest&logoColor=white)](tests/)
[![Domain](https://img.shields.io/badge/Domain-Agentic%20Workflows-8b5cf6?style=for-the-badge)](https://github.com/nathaniel-gordon/flowmind)

<br/>

*Each workflow step runs as an isolated message-driven actor. Sagas register compensating rollback actions before executing — so if a multi-step workflow fails midway, FlowMind unwinds it cleanly in reverse.*

</div>

---

## 🧠 What Is This?

> **For non-technical readers:** When a complex task involves many steps in sequence (like booking a flight, then a hotel, then a rental car), what happens if the car rental fails? You need to undo the hotel and flight too — in the right order. FlowMind is an orchestration engine that coordinates multi-step AI agent workflows with this exact guarantee: every step registers how to undo itself before it runs, so any failure triggers an automatic, ordered rollback. No half-completed workflows left in broken states.

---

## 🏗️ Actor Model Architecture

FlowMind implements the **Actor Model** for workflow execution. Steps run as isolated, message-driven actors that communicate exclusively through typed asynchronous mailboxes — no shared state, no race conditions. The scheduler dispatches messages from mailboxes in priority order and supports pause-and-resume execution checkpoints for long-running pipelines.

```
[Trigger] ──► [Planner Actor]
                    │
                    ▼ dispatches tasks via mailbox
        ┌───────────┼───────────┐
        ▼           ▼           ▼
[Researcher A] [Researcher B] [Researcher C]   ← parallel actors
        │           │           │
        └───────────┼───────────┘
                    ▼ results aggregated
             [Aggregator Actor]
                    │
                    ▼
             [Notifier Actor] ──► output
                    │
                    ▼ (if any step fails)
          [Compensation Saga]
            executes registered
            rollback actions
            in reverse order
```

---

## 🔬 Technical Design

**State Isolation** — Each actor holds private, encapsulated state. No actor can mutate another's state directly. All communication is via message passing through the mailbox. This eliminates shared-memory race conditions during concurrent tool executions in multi-agent workflows — a common failure mode in threading-based orchestrators.

**Compensation Sagas** — When a workflow step executes, it registers its compensating (rollback) action before committing. If a downstream step fails, the saga registry iterates registered compensations in LIFO order and executes them. For example: if database write succeeds but cloud resource provisioning fails, the database write's compensation (delete the record) executes automatically. The workflow is returned to a consistent state without manual intervention.

**Priority Mailboxes** — Actors support priority-ordered message queues. High-priority control messages (pause, cancel, compensate) preempt normal workflow messages regardless of queue depth. This allows clean cancellation of long-running actor pipelines without waiting for pending messages to drain.

**Mermaid DAG Export** — Every workflow automatically serializes its execution graph to a standard Mermaid flowchart diagram. This provides a visual audit trail of what ran, in what order, with what results — useful for debugging complex multi-agent pipelines.

| Property | Threading-Based Orchestrator | FlowMind Actor Model |
|---|---|---|
| **Shared State** | Mutex-guarded shared memory | No shared state — mailbox only |
| **Failure Recovery** | Manual rollback code | Automatic LIFO saga compensation |
| **Concurrent Execution** | Thread pool with lock contention | Isolated actors, no contention |
| **Audit Trail** | Log files | Mermaid DAG export |

---

## 🚀 Getting Started

```bash
git clone https://github.com/nathaniel-gordon/flowmind
cd flowmind
pip install -e .
```

### Run Sample Workflow

```bash
# Run sample actor pipeline with execution trace and Mermaid export
python -m wfe --run-sample --export-mermaid
```

### Run Tests

```bash
pytest tests/ -v
```

---

## 📁 Project Structure

```
flowmind/
├── wfe/
│   ├── actor.py        # Actor base class, mailbox, and message dispatcher
│   ├── saga.py         # Compensation saga registry & LIFO rollback
│   ├── scheduler.py    # Priority mailbox scheduler & checkpoint support
│   ├── export.py       # Mermaid DAG workflow graph export
│   └── __main__.py
└── tests/
```

---

<div align="center">

*Built by [Nathaniel Gordon](https://github.com/nathaniel-gordon)*

</div>
