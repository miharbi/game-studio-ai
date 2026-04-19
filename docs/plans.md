# Plan YAML Schema Reference

Plans are YAML files in `plans/templates/` or `plans/active/`. They define a sequential pipeline of agent steps.

## Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `task` | string | yes | Unique plan name (used in logs and DB) |
| `description` | string | yes | Human-readable description |
| `engine` | string \| null | no | `godot4`, `unity`, `unreal5`, or `null` for auto-detect |
| `input` | string | no | Input context injected into the first step prompt |
| `steps` | list | yes | Ordered list of pipeline steps |

## Step fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique step identifier within this plan |
| `agent` | string | yes | Agent name (must match a file in `agents/`) |
| `tier` | int | yes | 1, 2, or 3 — used for model routing |
| `action` | string | yes | Instruction injected into the agent's user turn |
| `gate` | string | yes | `auto`, `conditional`, or `human_review` |
| `depends_on` | list | no | List of step IDs whose output is available in context |
| `validate_as` | string | no | Schema type for output validation (see below) |

## Gate types

| Gate | Behavior |
|---|---|
| `auto` | Always proceeds — no pause |
| `conditional` | Proceeds unless the agent output contains "REJECTED" (case-insensitive) |
| `human_review` | Pauses the pipeline; waits for approval via CLI prompt or web UI `/runs/{id}/gate` endpoint |

## Validate_as schema types

| Schema | What it checks |
|---|---|
| `json` | Output contains valid JSON (inside a ` ```json ` fence or bare) |
| `level_json` | JSON with required level fields: `id`, `name_display`, `waves`, `props` |
| `sprite_spec` | JSON with `name`, `prompt`, `width`, `height` |
| `code_block` | Output contains at least one fenced code block |
| `feature_design` | Markdown with `## Concept`, `## Mechanics`, `## Risks` sections |

Validation errors are logged but do not stop the pipeline unless the gate is `conditional` and "REJECTED" appears in the output.

## Example: minimal plan

```yaml
task: quick_design
description: One-shot feature concept
engine: godot4
input: "Add a double-jump power-up"

steps:
  - id: concept
    agent: game_designer
    tier: 2
    action: "Write a one-paragraph concept for this feature."
    gate: human_review
    validate_as: feature_design
```

## Resuming a plan

Completed steps are saved to `runs.db`. If a run is interrupted, resume it with:

```bash
python runner.py resume <run-id>
```

Steps already in the database are skipped; execution continues from the first incomplete step.
