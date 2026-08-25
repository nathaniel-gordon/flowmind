# FlowMind — Agentic Workflow Orchestration Engine

> Build multi-step AI workflows as composable actors. FlowMind provides an actor-model runtime where agents exchange typed messages through mailboxes, enabling fault-isolated, auditable, and parallelizable agentic pipelines.

## What FlowMind Does

- **Actor runtime** — each agent is an isolated actor with its own mailbox and state
- **Typed message passing** — strongly typed inter-agent communication prevents silent failures
- **DAG scheduler** — dependency-aware task ordering with parallel execution
- **Audit log** — full message trace for every workflow run, replayable
- **Retry & compensation** — saga-pattern rollback on partial failures

## Architecture

```
WorkflowDefinition (Python DSL)
    └─> ActorRegistry      (spawn, supervise, route)
    └─> Mailbox            (async typed message queues)
    └─> Scheduler          (DAG topological ordering)
    └─> AuditLogger        (append-only execution trace)
    └─> SagaCoordinator    (rollback on failure)
```

## Quickstart

```bash
python examples/build_workflow.py   # build and run a sample agentic DAG
```

## Test

```bash
python tests/test_smoke.py
```

---

## 👤 Author & Contact

- **Author**: Nathaniel Gordon
- **Role**: Senior AI & Machine Learning Engineer
- **GitHub**: [github.com/nathaniel-gordon](https://github.com/nathaniel-gordon)
- **Portfolio / Upwork**: [upwork.com/freelancers/~015fe5a704f8943797](https://www.upwork.com/freelancers/~015fe5a704f8943797)
- **Email**: nathanielgordon346@gmail.com
- **Location**: Tallahassee, FL, USA
