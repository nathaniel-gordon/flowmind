# FlowMind — Actor-Model Agentic Workflow & Saga Orchestration

FlowMind is an agentic workflow execution engine built on the **Actor Model**. Workflow steps execute as isolated message-driven actors communicating strictly via asynchronous mailboxes. This architecture provides deterministic scheduling, dynamic branching, retry policies, and automated compensation sagas for multi-agent systems.

## Architectural Advantages

- **State Isolation**: Actors maintain encapsulated private state; no shared-memory race conditions during concurrent agent tool executions.
- **Deterministic Scheduling**: Message mailboxes support priority queues and pause-and-resume execution checkpoints.
- **Compensation Sagas**: When a multi-step workflow fails midway (e.g. database update fails after cloud resource provisioning), FlowMind unwinds the DAG in reverse order, executing registered rollback actions.
- **Mermaid DAG Export**: Workflows automatically serialize to standard Mermaid flowchart diagrams.

## Topology Example

```
[Trigger] ──► [Planner Actor] ──► [Parallel Researcher Actors]
                                            │
                                            ▼
[Notifier] ◄── [Compensation Saga] ◄── [Aggregator Actor]
```

## Usage

```bash
# Run sample workflow pipeline with execution trace export
python -m wfe --run-sample --export-mermaid
```

## Tests

```bash
pytest tests/ -v
```
