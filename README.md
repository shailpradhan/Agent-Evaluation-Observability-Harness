# Agent Evaluation & Observability Harness

An end-to-end testing, observability, and evaluation platform for AI agents. It instruments multi-step agent workflows via OpenTelemetry, enables deterministic offline replay using recorded mock tools, and evaluates trajectory correctness with structured LLM-as-a-judge rubrics to prevent regressions across model, prompt, and tool iterations.

## Core Lifecycle

```
AI Agent ➔ Observe (OTel) ➔ Record ➔ Replay (Mock Tools) ➔ Evaluate (LLM Judge) ➔ Measure (DB) ➔ Compare ➔ Gate (CI)
```

---

## Foundation 1: Architecture Overview

Foundation 1 sets up the core data contracts, schema definitions, and directory structure:

1. **Project Structure**: Modular package layout supporting agent definitions, OpenTelemetry instrumentation, task corpus management, trajectory replay, LLM judge, and metrics persistence.
2. **Data Models (`agent_eval.models`)**:
   - `Trajectory`, `TrajectoryStep`, `ToolCall`, `ToolResponse`, `LLMCall`: Full agent execution recording.
   - `JudgeResult`, `RubricEvaluation`, `DimensionScores`: Structured LLM-as-a-judge scoring and rubric assessment.
   - `EvalRun`, `EvalResult`, `RegressionReport`: Run metrics, pass rates, latency/token metrics, and regression detection.
   - `MockToolEntry`, `ReplaySession`: Deterministic tool replay records.
3. **Task Schema (`agent_eval.schema`)**:
   - `Task`: Standard evaluation task specification (`id`, `prompt`, `expected_outcome`, `expected_tools`, `rubric`, `metadata`).
   - `EvaluationDataset`: Versioned task collection with YAML/JSON loader and serialization utilities.

---

## Directory Structure

```
Agent/
├── pyproject.toml              # Project dependencies and configuration
├── README.md                   # Harness overview and guide
├── datasets/                   # Versioned evaluation task corpus
│   ├── refund.yaml
│   └── cancellation.yaml
├── agent_eval/                 # Core harness package
│   ├── schema/                 # Task and dataset schemas
│   ├── models/                 # Trajectory, Judge, Metrics, and Replay models
│   ├── agent/                  # Agent implementation (Phase 1 next steps)
│   ├── telemetry/              # OpenTelemetry instrumentation (Phase 2)
│   ├── replay/                 # Trajectory replay engine (Phase 2)
│   ├── judge/                  # LLM judge engine (Phase 2)
│   ├── storage/                # SQLite/Postgres persistence (Phase 3)
│   └── evaluation/             # Test runner and regression detector (Phase 4)
└── tests/                      # Unit test suite
```

---

## Quickstart

### Running the Deterministic Agent Example

The first agent-layer implementation is provider-independent. `Agent` receives
an `LLM` implementation and a collection of tools; `FakeLLM` simulates only the
example refund flow and does not perform real reasoning or call an external API.

```powershell
python -m agent_eval.agent.demo
```

The example prints a final response and the ordered tool calls. The LLM and
tools are injected when constructing `Agent`, so a future provider adapter can
implement `LLM.generate(messages)` without changing the orchestration code.
Tool inputs and outputs are validated with Pydantic models, and the LLM must
return either a JSON `tool_call` or a JSON `final_response`.
Tool implementations receive their declared Pydantic input model and return
their declared Pydantic output model. The sample store includes delivered order
`1234` and cancelled order `5678`; unknown orders produce an explicit lookup
error, and refunds for an eligible order are idempotent within the process.

The agent layer intentionally does not record telemetry or persist executions.
In the next phase, an outer adapter can observe LLM/tool boundaries and map the
returned `AgentResult` and call sequence into trajectory/trace data without
making the agent depend on OpenTelemetry, storage, or the replay engine.

### Loading an Evaluation Dataset

```python
from agent_eval.schema import EvaluationDataset

# Load versioned evaluation dataset
dataset = EvaluationDataset.load_from_yaml("datasets/refund.yaml")

print(f"Loaded {dataset.name} (v{dataset.version}) with {len(dataset.tasks)} tasks.")
for task in dataset.tasks:
    print(f"- Task: {task.id} -> Prompt: {task.prompt}")
    print(f"  Expected tools: {task.expected_tools}")
    print(f"  Rubric: {task.rubric}")
```

### Recording a Trajectory

```python
from agent_eval.models import Trajectory, ToolCall, ToolResponse, LLMCall

traj = Trajectory(run_id="run_001", task_id="refund_order")

# Record an LLM call
traj.record_llm_call(
    LLMCall(
        model="gemini-2.5-pro",
        prompt="Refund order #1234",
        response="Calling lookup_order(1234)",
        input_tokens=50,
        output_tokens=20,
        latency_ms=350.0
    )
)

# Record a tool call and response
call = ToolCall(tool="lookup_order", arguments={"order_id": "1234"})
traj.record_tool_call(call)
traj.record_tool_response(
    ToolResponse(
        tool="lookup_order",
        input={"order_id": "1234"},
        output={"status": "delivered", "amount": 100}
    )
)

print(f"Trajectory recorded: {len(traj.steps)} steps, {traj.total_tokens} tokens.")
```
