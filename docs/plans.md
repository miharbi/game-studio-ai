# Plan YAML Schema Reference

Plans are YAML files in `plans/templates/` or `plans/active/`. They define a sequential pipeline of agent steps. You can create, edit, and run plans from the **web UI** or work with the files and CLI directly.

For installation, setup, and your first run, start with [Project Quick Start](quick-start.md).

---

## Using the Web UI

### Running plans

Open the **Dashboard** (`/`). Select a plan template from the dropdown, pick an engine, enter your input text, and click **Run**. The run detail page streams live agent output via Server-Sent Events. When a `human_review` gate is reached, an approval panel appears — approve to continue or reject with feedback.

> The **Run** button is disabled when no model configuration is set — navigate to **Setup** to configure providers and API keys first.

### Editing plan templates

Navigate to **Plans** in the sidebar. The page lists all templates from `plans/templates/`.

- **Edit** — click any plan name to open it in the CodeMirror YAML editor. The step list, gate types, and dependencies are all editable. Changes save immediately via `PUT /edit/plans/{filename}`.
- **Create** — click **New Plan**, fill in the fields, add steps, and save. The file is created under `plans/templates/` automatically.
- **Delete** — use the delete button on the plan detail page.

> If CodeMirror fails to load (e.g. no internet for the ESM CDN), the editor falls back to a plain textarea.

### Resuming interrupted runs

If a run was interrupted (e.g. you closed the browser), you can resume it from the Dashboard's recent runs list, or via CLI:

```bash
python runner.py resume <run-id>
```

---

## Editing Files Directly

### Top-level fields

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `task` | string | yes | Unique plan name (used in logs and DB) |
| `description` | string | yes | Human-readable description |
| `engine` | string \| null | no | `godot4`, `unity`, `unreal5`, or `null` for auto-detect |
| `input` | string | no | Input context injected into the first step prompt |
| `steps` | list | yes | Ordered list of pipeline steps |

### Step fields

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `id` | string | yes | Unique step identifier within this plan |
| `agent` | string | yes | Agent name (must match a file in `agents/`) |
| `tier` | int | yes | 1, 2, or 3 — used for model routing |
| `action` | string | yes | Instruction injected into the agent's user turn |
| `gate` | string | yes | `auto`, `conditional`, or `human_review` |
| `depends_on` | list | no | List of step IDs whose output is available in context |
| `validate_as` | string | no | Schema type for output validation (see below) |

### Gate types

| Gate | Behavior |
| ---- | -------- |
| `auto` | Always proceeds — no pause |
| `conditional` | Proceeds unless the agent output contains "REJECTED" (case-insensitive) |
| `human_review` | Pauses the pipeline; waits for approval via CLI prompt or web UI `/runs/{id}/gate` endpoint |

### Validate_as schema types

| Schema | What it checks |
| ------ | -------------- |
| `json` | Output contains valid JSON (inside a ` ```json ` fence or bare) |
| `level_json` | JSON with required level fields: `id`, `name_display`, `waves`, `props` |
| `sprite_spec` | JSON with `name`, `prompt`, `width`, `height` |
| `code_block` | Output contains at least one fenced code block |
| `feature_design` | Markdown with `## Concept`, `## Mechanics`, `## Risks` sections |
| `barrio_bravo_world` | Full Barrio Bravo world JSON block — validates required keys, wave gaps, speaker/trigger enums, `street_food` prop count per combat wave, ≥ 4 `scenario_ads`, ≥ 11 dialogues, boss block, and all 20 `art_direction` keys |

Validation errors are logged but do not stop the pipeline unless the gate is `conditional` and "REJECTED" appears in the output.

### Example: minimal plan

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

---

## CLI Reference

```bash
# Run a plan
python runner.py run --plan plans/templates/design_feature.yaml \
    --engine godot4 --input "Add a wall-jump mechanic"

# Dry run (print steps without calling LLMs)
python runner.py run --plan plans/templates/design_feature.yaml --dry-run

# Resume an interrupted run
python runner.py resume <run-id>

# List available templates
python runner.py list-plans
```

Completed steps are saved to `runs.db`. If a run is interrupted, `resume` skips finished steps and continues from the first incomplete one.
