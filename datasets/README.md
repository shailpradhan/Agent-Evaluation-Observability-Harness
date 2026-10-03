# Evaluation Datasets (Task Corpus)

This directory houses the versioned task datasets used to evaluate AI agents.

## Dataset Format

Datasets can be defined in YAML format containing:
- `version`: Semantic version string (e.g. `"1.0.0"`)
- `name`: Dataset identifier
- `description`: Overview of tasks in this corpus
- `tasks`: Array of task definitions:
  - `id`: Unique task identifier
  - `prompt`: The user instruction or input to the agent
  - `expected_outcome`: Key outcomes / attributes expected
  - `expected_tools`: Tools expected to be invoked
  - `rubric`: Evaluation criteria for LLM judge
  - `metadata`: Tags, difficulty, category

