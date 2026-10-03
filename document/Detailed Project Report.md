# Detailed Project Report: Agent Evaluation & Observability Harness

 I reviewed the project page you shared. The project is called **Agent Evaluation & Observability Harness**. Its core purpose is to bring the discipline of **software testing into AI-agent development**. Instead of trusting an agent because its final answer “looks good,” the system records what the agent did, replays those actions under controlled conditions, grades the result, tracks changes between versions, and can block a bad change in CI.  ResuMax

 Original project page — Agent Evaluation & Observability Harness

---

 ## 1\. Executive summary

 ### The project in one sentence

 > **Build a testing and observability platform that determines whether an AI agent is behaving correctly and whether a new model/prompt version has become better or worse.**

 Traditional software has:

```
Code
  ↓
Unit Tests
  ↓
Integration Tests
  ↓
CI
  ↓
Deploy
```

 AI agents need something more sophisticated:

```
AI Agent
   ↓
Observe what it did
   ↓
Capture trajectory
   ↓
Replay with controlled tools
   ↓
Evaluate against task/rubric
   ↓
Calculate metrics
   ↓
Compare against previous version
   ↓
CI decision
   ↓
PASS / BLOCK
```

 That is the **core idea** of this project. The project page describes the same flow using OpenTelemetry instrumentation, versioned evaluation datasets, trajectory replay, an LLM judge, a metrics database, and pytest-based CI gating.  ResuMax

---

 # 2\. Why does this project exist?

 This is the most important question.

 Imagine you have an AI customer-support agent.

 A user says:

```
"Please refund my order #1234."
```

 The agent might:

```
1. Look up order #1234
2. Check refund eligibility
3. Call refund API
4. Confirm refund
5. Respond to user
```

 You modify the system prompt.

 Now the agent does:

```
1. Look up order #1234
2. Immediately tell user the refund is complete
```

 The final response might still look convincing:

```
"Your refund has been processed."
```

 A basic test might say:

```
✓ Response contains "refund"
```

 But the agent actually **failed**.

 It didn't verify the order or perform the operation.

 This illustrates the fundamental problem:

 > **AI agents aren't just producing text. They're taking sequences of actions.**

 Therefore, testing only the final text isn't enough.

 You need to evaluate the **entire trajectory**.

---

 # 3\. What is an AI-agent trajectory?

 A trajectory is the sequence of actions an agent takes while solving a task.

 For example:

```
USER
│
│ "Refund order #1234"
│
▼
AGENT
│
├── LLM reasoning
│
├── lookup_order(1234)
│
├── check_refund_policy()
│
├── refund_order(1234)
│
├── LLM generates response
│
└── "Your refund has been processed."
```

 The harness captures these operations.

 The project specifically describes capturing:

 - tool calls
- intermediate outputs
- latency
- token information
- OpenTelemetry spans

 during live or replayed runs.  ResuMax

 So instead of storing only:

```
Final answer = "Your refund has been processed."
```

 you have:

```
Task
 ↓
Agent decisions
 ↓
Tool calls
 ↓
Tool responses
 ↓
LLM calls
 ↓
Latency/tokens
 ↓
Final answer
```

 That complete record is the **trajectory**.

---

 # 4\. The central architecture

 The entire project can be understood as six components.

```
                    ┌──────────────────────┐
                    │      AI AGENT        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ 1. OBSERVABILITY     │
                    │    OpenTelemetry     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ 2. TASK CORPUS       │
                    │    YAML / JSON       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ 3. REPLAY ENGINE     │
                    │    Mock tools        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ 4. LLM JUDGE         │
                    │    Rubric + Score    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ 5. METRICS DATABASE  │
                    │    SQLite/Postgres   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ 6. CI GATE           │
                    │    pytest            │
                    └──────────────────────┘
```

 The project page explicitly lays out this six-stage flow: instrument → task corpus → replay → judge → store → CI assert.  ResuMax

---

 # 5\. Component 1 — Agent observability

 The first question is:

 > **What exactly did my agent do?**

 This is where **OpenTelemetry** is used.

 OpenTelemetry lets you represent operations as structured traces/spans.

 For example:

```
Trace: agent_run_001

├── LLM Call
│   ├── input
│   ├── output
│   ├── tokens
│   └── latency
│
├── Tool Call
│   ├── name = lookup_order
│   ├── arguments = 1234
│   └── response
│
├── Tool Call
│   ├── name = refund_order
│   ├── arguments = 1234
│   └── response
│
└── Final LLM Call
    ├── input
    ├── output
    └── latency
```

 This gives you **observability**.

 Without observability:

```
Agent → "Refund successful"
```

 With observability:

```
Agent
 ├── lookup_order
 ├── check_policy
 ├── refund_order
 ├── 3 LLM calls
 ├── 1.8 sec
 ├── 1,240 tokens
 └── final response
```

 That difference is fundamental.

 The project specifically highlights OpenTelemetry spans, tool-call attributes, latency, and tokens.  ResuMax

---

 # 6\. Component 2 — Evaluation task corpus

 The second problem is:

 > **What should the agent have done?**

 You need a collection of test cases.

 For example:

```
- id: refund_order

  prompt: |
    Refund order #1234

  expected_outcome:
    refund_processed: true

  expected_tools:
    - lookup_order
    - check_refund_policy
    - refund_order

  rubric:
    - Correct order identified
    - Eligibility checked
    - Refund executed
    - User receives accurate response
```

 Another:

```
- id: cancel_order

  prompt: |
    Cancel order #5678

  expected_outcome:
    order_cancelled: true

  rubric:
    - Correct order identified
    - Cancellation eligibility checked
    - Cancellation executed
    - User receives accurate response
```

 This becomes your **evaluation dataset**.

 The project calls for a versioned YAML/JSON corpus containing the input prompt, expected outcome, and grading criteria.  ResuMax

---

 # 7\. Why version the dataset?

 Because your evaluation itself changes over time.

 Imagine:

```
Dataset v1
──────────
10 test cases
```

 Later:

```
Dataset v2
──────────
25 test cases
```

 Now you can say:

```
Agent v10
tested against
Dataset v1
```

 versus:

```
Agent v11
tested against
Dataset v2
```

 This makes your testing process reproducible.

 It also means the evaluation suite becomes part of the project's source-controlled engineering process.

---

 # 8\. Component 3 — Trajectory replay

 This is one of the most important pieces.

 Suppose your agent calls:

```
weather_api()
```

 or:

```
database.lookup_customer()
```

 or:

```
payment.refund()
```

 You don't want every test run to call real services.

 Why?

 Because it can:

 - cost money
- produce different results
- modify real data
- make tests slow
- make tests flaky
- make regression testing difficult

 So the system records the tool response.

 Example:

```
{
  "tool": "lookup_order",
  "input": {
    "order_id": "1234"
  },
  "output": {
    "status": "delivered",
    "amount": 100
  }
}
```

 During replay:

```
Agent
 ↓
lookup_order(1234)
 ↓
Replay engine
 ↓
Recorded response
```

 Instead of:

```
Agent
 ↓
Real API
 ↓
Unknown response
```

 The project specifically proposes using recorded tool responses as mocks so trajectories can be replayed without spending real API budget.  ResuMax

---

 # 9\. Why deterministic replay matters

 Imagine you're testing two prompt versions.

 ### Prompt A

```
"You are a helpful support agent."
```

 ### Prompt B

```
"You are a highly concise support agent."
```

 You want to know:

 > Did Prompt B improve the agent?

 If the external APIs return different data during the two tests, your comparison isn't fair.

 Instead:

```
Same task
   +
Same tool responses
   +
Different prompt
   =
Controlled experiment
```

 This is essentially applying **scientific experimental control** to AI-agent development.

---

 # 10\. Component 4 — LLM-as-a-Judge

 Now we have the trajectory.

 But how do we decide whether it's good?

 This is where the **LLM judge** comes in.

 The system sends the task, rubric, and trajectory to a judging model.

 Conceptually:

```
             ┌──────────────┐
             │ Test Task    │
             └──────┬───────┘
                    │
             ┌──────▼───────┐
             │ Rubric       │
             └──────┬───────┘
                    │
             ┌──────▼───────┐
             │ Trajectory   │
             └──────┬───────┘
                    │
                    ▼
             ┌───────────────┐
             │  LLM JUDGE    │
             └───────┬───────┘
                     │
                     ▼
                Structured
                  score
```

 For example:

```
{
  "score": 0.91,
  "correctness": 0.95,
  "tool_usage": 0.90,
  "final_response": 0.88
}
```

 The project describes a configurable judge returning a 0–1 score with grading dimensions and explanations.  ResuMax

---

 # 11\. Why use an LLM judge?

 Because many agent behaviors cannot easily be tested with:

```
assert output == expected_output
```

 For example:

```
Expected:
"Tell the customer their refund was processed."
```

 But the agent might produce:

```
"Done — the refund has been successfully initiated and should
appear in your account within five business days."
```

 It's not an exact string match, but it's potentially a perfectly good answer.

 An LLM judge can evaluate **meaning and behavior**, rather than exact strings.

---

 # 12\. But LLM judges have a problem

 LLMs aren't perfectly consistent judges.

 For example:

```
Run 1 → 0.91
Run 2 → 0.87
Run 3 → 0.94
```

 even when the trajectory hasn't changed.

 That's why the project specifically emphasizes:

 - rubric design
- grading dimensions
- structured output schemas
- reducing judge variance

 as part of the engineering challenge.  ResuMax

 This is actually an important part of the project: **you're not just calling an LLM—you are designing a reliable evaluation system around an unreliable evaluator.**

---

 # 13\. Component 5 — Metrics database

 Every evaluation produces information.

 For example:

```
Run ID:          104
Model:           Model-A
Prompt version:  v12
Dataset version: v5

Pass rate:       92%
Mean score:      0.89
Token cost:      $1.42
P95 latency:     3.2 sec
```

 The project proposes storing per-run metrics in SQLite or Postgres.  ResuMax

 A conceptual schema might be:

```
EVAL_RUN
────────────────────────
run_id
model_version
prompt_version
dataset_version
mean_score
pass_rate
token_cost
p95_latency
timestamp
```

 And:

```
EVAL_RESULT
────────────────────────
result_id
run_id
task_id
score
passed
latency
tokens
```

 This allows historical comparison.

---

 # 14\. Regression detection

 Now we reach the real business value.

 Suppose the current production agent has:

```
Mean score = 0.91
Pass rate  = 94%
```

 You change the system prompt.

 New results:

```
Mean score = 0.79
Pass rate  = 82%
```

 The harness should detect:

```
                 OLD       NEW

Mean score       0.91      0.79  ↓
Pass rate        94%       82%   ↓
Latency          2.4s      2.8s  ↑
```

 And report:

```
REGRESSION DETECTED
```

 This is why the project isn't simply an evaluation script.

 It's a **regression-testing system for AI agents**.

---

 # 15\. Component 6 — pytest and CI

 The final step is automation.

 Imagine:

```
def test_agent_quality():
    result = evaluate_agent()

    assert result.mean_score >= 0.85
```

 Then:

```
Developer changes prompt
          ↓
       Git push
          ↓
    GitHub Actions
          ↓
        pytest
          ↓
    Agent evaluation
          ↓
      Score = 0.78
          ↓
      Threshold = 0.85
          ↓
         FAIL
```

 The pull request can then be blocked.

 If:

```
Score = 0.92
Threshold = 0.85
```

 then:

```
PASS
```

 The project explicitly proposes a pytest plugin that fails the suite when the aggregate score drops below a configurable threshold, enabling CI gating.  ResuMax

---

 # 16\. The core idea in one diagram

 This is the diagram I would remember for an interview:

```
                    AI AGENT
                       │
                       ▼
              ┌─────────────────┐
              │   OBSERVE       │
              │ OpenTelemetry   │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    RECORD       │
              │   Trajectory    │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │     REPLAY      │
              │ Mock tool calls │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │     EVALUATE    │
              │    LLM Judge    │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │     MEASURE     │
              │ Scores/Metrics  │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    COMPARE      │
              │ Old vs New      │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │      CI         │
              │ PASS / BLOCK    │
              └─────────────────┘
```

---

 # 17\. What problem does each technology solve?

 | Technology | Purpose |
| --- | --- |
| **Python** | Main implementation language |
| **OpenTelemetry** | Capture agent traces/spans |
| **LLM-as-judge** | Evaluate complex agent behavior |
| **YAML/JSON** | Store evaluation tasks |
| **Replay engine** | Make tests reproducible |
| **Mocks** | Avoid real external API calls |
| **SQLite/Postgres** | Store evaluation history |
| **Pydantic** | Validate structured data |
| **pytest** | Turn evaluations into tests |
| **GitHub Actions** | Run evaluations automatically in CI |
| **TypeScript** | Listed as an additional project language |
| **FastAPI** | Suggested extension for a dashboard |

 The project's stated stack includes Python, TypeScript, LLM-as-judge, OpenTelemetry, pytest, trajectory replay, evaluation datasets, CI gating, SQLite, Pydantic, and GitHub Actions.  ResuMax

---

 # 18\. What makes this different from normal unit testing?

 This is a key conceptual distinction.

 ### Traditional software

 You might test:

```
assert calculate_tax(100) == 10
```

 The expected result is deterministic.

 ### AI agent

 You might have:

```
Input:
"Find me the cheapest flight."
```

 There isn't necessarily one exact correct string.

 The agent could:

```
Search flights
Compare prices
Check baggage
Return recommendation
```

 or:

```
Search flights
Compare prices
Return recommendation
```

 Both might be acceptable depending on the rubric.

 Therefore AI testing often needs:

```
Behavior
+
Trajectory
+
Rubric
+
Semantic evaluation
```

 rather than only:

```
input → exact output
```

---

 # 19\. What does "observability" mean here?

 **Evaluation** and **observability** are related but different.

 ### Observability asks:

 > What happened?

 Example:

```
Agent called search 3 times.
Agent called database once.
Agent used 2,400 tokens.
Agent took 4.2 seconds.
```

 ### Evaluation asks:

 > Was what happened good?

 Example:

```
Tool usage: 0.8
Correctness: 0.9
Final answer: 0.95
Overall: 0.88
```

 So:

```
OBSERVABILITY
       ↓
"What happened?"

EVALUATION
       ↓
"Was it good?"

REGRESSION
       ↓
"Did it get worse?"
```

 This project combines all three.

---

 # 20\. What happens when you change the model?

 This is another major use case.

 Suppose:

```
Current:

GPT-A
Prompt v7
Score = 0.91
```

 You want to test:

```
Candidate:

GPT-B
Prompt v7
```

 The harness runs the same evaluation dataset:

```
Dataset
   │
   ├── Test 1
   ├── Test 2
   ├── Test 3
   ├── ...
   └── Test 100
```

 Then:

```
GPT-A → 0.91
GPT-B → 0.94
```

 You have evidence that GPT-B performed better on your evaluation suite.

 This makes the harness useful not only for prompt engineering but also for **model selection**.

---

 # 21\. What happens when you change the prompt?

 Same concept.

```
Prompt v10
    ↓
Score = 0.89
```

 Change prompt:

```
Prompt v11
    ↓
Score = 0.84
```

 The system can identify:

```
Prompt v11 introduced regression
```

 So prompt engineering becomes less like:

 > "I think this prompt is better."

 and more like:

 > "This prompt increased the evaluation score from 0.89 to 0.94 across 100 tasks."

 That's a much more engineering-oriented approach.

---

 # 22\. What is the real value of the project?

 The deepest idea is **trust**.

 AI systems are probabilistic.

 Traditional software gives you confidence through:

```
Tests
+
Version control
+
CI
+
Code review
```

 AI-agent development needs the equivalent:

```
Evaluation datasets
+
Trajectory observability
+
Replay
+
LLM judging
+
Regression metrics
+
CI gating
```

 The project essentially creates a **safety net for agent development**, which is exactly how the project page characterizes its purpose.  ResuMax

---

 # 23\. End-to-end example

 Let's imagine you're developing a travel agent.

 User:

```
"Find me a flight from Chennai to London."
```

 The agent does:

```
1. Parse request
2. Search flights
3. Filter results
4. Compare prices
5. Check baggage
6. Return recommendation
```

 The harness records:

```
Trajectory #812

LLM call
Search tool
Search tool
Filter
LLM call
Final answer

Latency: 4.1 sec
Tokens: 2,100
```

 The evaluation task says:

```
expected:
  - Search flights
  - Compare multiple options
  - Include price
  - Include relevant flight details
  - Don't invent unavailable flights
```

 The LLM judge evaluates:

```
Correctness       0.95
Tool usage        0.90
Completeness      0.85
No hallucination  1.00

Overall           0.92
```

 Database:

```
run = 812
score = 0.92
```

 Then you modify the prompt.

 New result:

```
score = 0.71
```

 CI:

```
Required score = 0.85
Actual score   = 0.71

❌ FAIL
```

 The prompt change cannot merge.

 That is the project working exactly as intended.

---

 # 24\. The project lifecycle

 The project page recommends four broad implementation phases.  ResuMax

 I would interpret them as:

 ### Phase 1 — Foundation

 Build:

```
Project structure
↓
Data models
↓
Task schema
↓
Basic agent
```

 ### Phase 2 — First working pipeline

 Build:

```
Agent
↓
Trace
↓
Task
↓
Replay
↓
Judge
↓
Score
```

 Get one complete evaluation working before adding complexity.

 ### Phase 3 — Persistence

 Add:

```
SQLite/Postgres
↓
Historical runs
↓
Metrics
↓
Version comparison
```

 ### Phase 4 — Production hardening

 Add:

```
pytest
↓
CI
↓
Failure reporting
↓
Thresholds
↓
Testing
↓
Documentation
```

---

 # 25\. Possible final repository

 A sensible architecture could look like:

```
agent-eval-harness/
│
├── agent/
│   ├── agent.py
│   └── tools.py
│
├── telemetry/
│   ├── tracer.py
│   └── spans.py
│
├── datasets/
│   ├── refund.yaml
│   ├── cancellation.yaml
│   └── search.yaml
│
├── replay/
│   ├── recorder.py
│   ├── mock_tools.py
│   └── engine.py
│
├── judge/
│   ├── judge.py
│   ├── rubric.py
│   └── schemas.py
│
├── storage/
│   ├── database.py
│   └── models.py
│
├── evaluation/
│   ├── runner.py
│   ├── metrics.py
│   └── regression.py
│
├── pytest_plugin/
│   └── plugin.py
│
├── tests/
│   ├── test_agent.py
│   ├── test_replay.py
│   ├── test_judge.py
│   └── test_regression.py
│
├── .github/
│   └── workflows/
│       └── evaluation.yml
│
├── pyproject.toml
└── README.md
```

---

 # 26\. What the project teaches you

 This project is valuable because it crosses several engineering areas.

 ### AI engineering

 You learn:

```
Agents
LLMs
Prompt evaluation
LLM judges
Tool calling
```

 ### Backend engineering

 You learn:

```
APIs
Data models
Persistence
SQLite/Postgres
Pydantic
```

 ### QA/testing

 You learn:

```
Test datasets
Mocks
Replay
Regression testing
Assertions
Thresholds
```

 ### Observability

 You learn:

```
Traces
Spans
Telemetry
Latency
Tokens
Agent execution graphs
```

 ### DevOps

 You learn:

```
pytest
CI
GitHub Actions
PR gating
Automated quality checks
```

 The project itself is categorized under AI & Agents and says it fits ML/AI, QA/SDET, and backend roadmaps.  ResuMax

---

 # 27\. Extensions you could build later

 The project also suggests several ways to take it further.  ResuMax

 ### Dashboard

 Build:

```
FastAPI
+
HTML dashboard
```

 showing:

```
Score over time

1.0 ┤             ●
0.9 ┤      ●  ●
0.8 ┤  ●
0.7 ┤
    └────────────────
      commits
```

 You could identify exactly which Git commit caused a regression.

 ### Mutation testing

 Automatically modify:

```
Prompt
Tool description
Agent configuration
```

 and see how much the evaluation score changes.

 That tells you how **brittle** the agent is.

 ### Multi-turn evaluation

 Instead of:

```
User → Agent
```

 test:

```
User
 ↓
Agent
 ↓
User follow-up
 ↓
Agent
 ↓
User clarification
 ↓
Agent
```

 Then evaluate whether the agent maintains context correctly.

 These are explicitly suggested extensions on the project page.  ResuMax

---

 # 28\. The most important mental model

 Don't think of this project as:

 > "I'm building a tool that checks whether an AI answer is correct."

 Think of it as:

 > **"I'm building an automated quality-control system for AI agents."**

 The difference is important.

 It covers the entire lifecycle:

```
                  AI AGENT
                     │
                     ▼
               OBSERVE IT
                     │
                     ▼
               RECORD IT
                     │
                     ▼
              REPLAY IT
                     │
                     ▼
              EVALUATE IT
                     │
                     ▼
              MEASURE IT
                     │
                     ▼
              COMPARE IT
                     │
                     ▼
               TEST IT
                     │
                     ▼
              GATE CHANGES
```

 That is the **core idea** of the project.

---

 # 29\. Final project definition

 If you had to explain this project in an interview, I would describe it like this:

 > **“I built an evaluation and observability harness for AI agents. It instruments agent executions using OpenTelemetry to capture tool calls, intermediate outputs, latency, and token usage. I created versioned task datasets with expected outcomes and grading rubrics, then built a replay engine that mocks recorded tool responses so agent versions can be tested deterministically without repeatedly calling external APIs. Each trajectory is evaluated using an LLM-as-a-judge system, producing structured scores that are stored alongside run metrics such as pass rate, mean score, token cost, and latency. Finally, I integrated the evaluation system with pytest and CI so that regressions below a configurable quality threshold automatically fail the build and can block a pull request.”**

 That description captures essentially the whole architecture in one paragraph.  ResuMax

 ## Bottom line

 The project is fundamentally about solving this problem:

 **“How do we safely evolve AI agents without accidentally making them worse?”**

 Its answer is:

 **Observe → Record → Replay → Evaluate → Measure → Compare → Gate.**

 That is why this is a stronger project than a simple chatbot: it addresses the **engineering infrastructure around AI agents**, especially reliability, reproducibility, evaluation, observability, and automated regression prevention. The official project estimates roughly **20–35 hours** and lists Python/TypeScript with OpenTelemetry, LLM-as-judge, pytest, trajectory replay, SQLite, Pydantic, and GitHub Actions.  ResuMax
