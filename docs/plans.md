# Plan YAML Schema Reference

Plans are YAML files in `plans/templates/` or `plans/active/`. They define a sequential pipeline of agent steps. You can create, edit, and run plans from the **web UI** or work with the files and CLI directly.

For installation, setup, and your first run, start with [Project Quick Start](quick-start.md).

---

## Using the Web UI

### Running a plan from the Dashboard

Open the **Dashboard** (`/`).

1. Select a plan template from the dropdown — each entry corresponds to a YAML file in `plans/templates/`.
2. Choose an engine, or leave it on *auto-detect* to let the app read your project directory.
3. Type your input text — this is injected verbatim into the first step's agent prompt.
4. Click **Run**.

You are redirected to the **Run Detail** page, which streams live agent output via Server-Sent Events. Each completed step is marked in the **Pipeline** sidebar on the left.

> The **Run** button is disabled when no model configuration is set. Navigate to **Setup** to configure providers and API keys first.

### Gates and the human review flow

Every step has a **gate** that controls whether the pipeline pauses after that step:

| Gate | Runtime behaviour |
| ---- | ----------------- |
| `auto` | The next step starts immediately after the current one finishes. |
| `conditional` | Continues automatically unless the agent output contains the word `REJECTED` (case-insensitive). Use this for self-checking steps. |
| `human_review` | The pipeline **pauses**. An approval panel appears on the Run Detail page. Review the agent's output, then either **Approve** to continue or **Reject** and type feedback — the feedback is prepended to the next agent's prompt. |

### Parallel execution with depends_on

By default steps run sequentially. When two or more steps share the same `depends_on` list, they run **in parallel** — each in its own async task, pulling output from the same parent step(s). The pipeline waits for all parallel branches to complete before continuing to any downstream step.

Example — `write_lore` and `write_mechanics` both depend on `concept`, so they run at the same time:

```yaml
steps:
  - id: concept
    agent: creative_director
    tier: 1
    action: "Draft a one-paragraph concept."
    gate: auto

  - id: write_lore
    agent: writer
    tier: 3
    action: "Expand the concept into lore."
    gate: auto
    depends_on: [concept]

  - id: write_mechanics
    agent: game_designer
    tier: 2
    action: "Expand the concept into mechanics."
    gate: auto
    depends_on: [concept]

  - id: review
    agent: producer
    tier: 1
    action: "Consolidate lore and mechanics into a feature brief."
    gate: human_review
    depends_on: [write_lore, write_mechanics]
```

### Editing plan templates

Navigate to **Plans** in the sidebar. The page lists all templates from `plans/templates/`.

Click any plan to open the **Edit Plan** page, which has two views:

**List view** — a form-based editor. Each step is a card with fields for ID, Agent, Action, Gate, Depends On, and Validate As. Drag the handle on the left to reorder steps. Click **Add Step** to append a new one.

**Flow view** — a visual node graph powered by Drawflow. Each step is a node showing the agent name, gate badge, and a Validate As badge. Draw edges by dragging from the output port (right dot) of one node to the input port (left dot) of another — this sets the `depends_on` relationship. Click the ✏ icon on a node to open the side panel and edit its fields.

Changes are saved via **Save** (or Ctrl/Cmd+S) — they write the YAML file to `plans/templates/` immediately.

- **Create** — click **New Plan** on the Plans list page, fill in the fields, add steps, and save.
- **Delete** — use the **Delete** button on the Edit Plan page.

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
