# API Reference

Interactive documentation is available at **`/docs`** (Swagger UI) and **`/redoc`** (ReDoc) when the server is running.

Only JSON endpoints are listed below. HTML UI routes (`/`, `/sprites`, `/edit/*`, `/runs/*`) are excluded.

For installation and first-time app setup, start with [Project Quick Start](quick-start.md).

---

## Using the UI vs the API

Most day-to-day work is easier from the HTML UI:

- Use the **Dashboard** to start runs and review gate decisions
- Use **Sprites** to approve or reject generated images
- Use **Agents**, **Plans**, **Engines**, and **Setup** to edit project data

Use the API when you want to automate the app from another tool, script custom integrations, or test behavior outside the built-in UI.

---

## Runs

Start plan runs, stream live agent output via SSE, and resolve gate checkpoints.

### `POST /plans/run` — Start a plan run

Validates the plan, checks that at least one LLM provider has an active API key, then launches the plan executor in a background thread.

#### Request Body for `POST /plans/run` (`application/json`)

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `plan` | string | yes | Plan template filename (e.g. `design_feature.yaml`) |
| `engine` | string | no | Engine override (e.g. `unity`). Empty = auto-detect from project path |
| `input_text` | string | no | Context passed to the first agent step |

#### Response `200` for `POST /plans/run`

```json
{ "run_id": "abc123" }
```

#### Errors for `POST /plans/run`

| Code | Reason |
| ---- | ------ |
| `404` | Plan file not found |
| `422` | No active LLM provider — add an API key in Setup |

---

### `GET /runs/{run_id}/stream` — Stream run output (SSE)

Server-Sent Events stream for a live run. Connect with `EventSource` or `hx-sse`.

- Each event contains a chunk of agent output as HTML-safe text.
- `data: __DONE__` signals completion.
- Keep-alive comments (`: keep-alive`) are sent every 30 s while idle.

#### Path Params for `GET /runs/{run_id}/stream`

| Param | Type | Description |
| ----- | ---- | ----------- |
| `run_id` | string | Run ID returned by `POST /plans/run` |

#### Response for `GET /runs/{run_id}/stream`

`text/event-stream`

---

### `POST /runs/{run_id}/gate` — Resolve a gate checkpoint

Approve or reject a `human_review` gate. Approved gates let the pipeline continue; rejected gates halt the run and the agent receives the feedback string.

#### Path Params for `POST /runs/{run_id}/gate`

| Param | Type | Description |
| ----- | ---- | ----------- |
| `run_id` | string | Run ID |

#### Request Body for `POST /runs/{run_id}/gate` (`application/json`)

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `approved` | boolean | yes | `true` to approve, `false` to reject |
| `feedback` | string | no | Rejection reason sent back to the agent |

#### Response `200` for `POST /runs/{run_id}/gate`

```json
{ "status": "approved", "run_id": "abc123" }
```

---

## Sprites

Approve or reject generated sprite images in the pending review queue.

Pending sprites live in `output/sprites/`. Approved sprites are moved to `output/approved/`.

### `POST /sprites/{name}/approve` — Approve a pending sprite

#### Path Params for `POST /sprites/{name}/approve`

| Param | Type | Description |
| ----- | ---- | ----------- |
| `name` | string | Sprite filename (e.g. `hero_idle.png`) |

#### Response `200` for `POST /sprites/{name}/approve`

```json
{ "status": "approved", "path": "/absolute/path/to/output/approved/hero_idle.png" }
```

#### Errors for `POST /sprites/{name}/approve`

`404` if sprite not found.

---

### `POST /sprites/{name}/reject` — Reject and delete a pending sprite

#### Path Params for `POST /sprites/{name}/reject`

| Param | Type | Description |
| ----- | ---- | ----------- |
| `name` | string | Sprite filename |

#### Response `200` for `POST /sprites/{name}/reject`

```json
{ "status": "rejected", "name": "hero_idle.png" }
```

#### Errors for `POST /sprites/{name}/reject`

`404` if sprite not found.

---

## Agents

CRUD for agent persona Markdown files stored under `agents/{tier}/`.

### `PUT /edit/agents/{tier}/{filename}` — Save an agent persona file

#### Path Params for `PUT /edit/agents/{tier}/{filename}`

| Param | Type | Description |
| ----- | ---- | ----------- |
| `tier` | string | `tier1`, `tier2`, or `tier3` |
| `filename` | string | e.g. `creative_director.md` |

#### Request Body for `PUT /edit/agents/{tier}/{filename}` (`application/json`)

| Field | Type | Description |
| ----- | ---- | ----------- |
| `name` | string | Agent display name |
| `tier` | integer | 1–3 |
| `reports_to` | string | Parent agent name |
| `domain` | string | Specialty domain |
| `model_override` | string | Optional model override |
| `body` | string | Markdown body content |

#### Response `200` for `PUT /edit/agents/{tier}/{filename}`

```json
{ "status": "saved", "file": "tier1/creative_director.md" }
```

---

### `POST /edit/agents/{tier}` — Create a new agent persona file

#### Path Params for `POST /edit/agents/{tier}`

- `tier`: `tier1`, `tier2`, or `tier3`

#### Request Body for `POST /edit/agents/{tier}`

Same schema as `PUT` above.

#### Response `201` for `POST /edit/agents/{tier}`

```json
{ "status": "created", "file": "tier2/my_agent.md" }
```

#### Errors for `POST /edit/agents/{tier}`

- `409` if the agent already exists
- `422` if the tier directory is invalid

---

### `DELETE /edit/agents/{tier}/{filename}` — Delete an agent persona file

#### Response `200` for `DELETE /edit/agents/{tier}/{filename}`

```json
{ "status": "deleted", "file": "tier3/my_agent.md" }
```

#### Errors for `DELETE /edit/agents/{tier}/{filename}`

`404` if not found.

---

## Plans

CRUD for plan template YAML files stored under `plans/templates/`.

### `PUT /edit/plans/{filename}` — Save a plan template

#### Path Params for `PUT /edit/plans/{filename}`

- `filename`: e.g. `design_feature.yaml`

#### Request Body for `PUT /edit/plans/{filename}` (`application/json`)

| Field | Type | Description |
| ----- | ---- | ----------- |
| `task` | string | Internal task identifier |
| `description` | string | Human-readable description |
| `engine` | string | Engine override or empty |
| `input_text` | string | Input prompt shown to user |
| `steps` | array | List of step objects (see below) |

Each step object:

| Field | Type | Description |
| ----- | ---- | ----------- |
| `id` | string | Unique step identifier |
| `agent` | string | Agent filename stem |
| `tier` | integer | 1–3 |
| `action` | string | Instruction passed to the agent |
| `gate` | string | `auto` or `human_review` |
| `depends_on` | string | Step ID this step waits for |
| `validate_as` | string | Output schema type for validation |

#### Response `200` for `PUT /edit/plans/{filename}`

```json
{ "status": "saved", "file": "design_feature.yaml" }
```

---

### `POST /edit/plans` — Create a new plan template

#### Request Body for `POST /edit/plans`

Same schema as `PUT` above.

#### Response `201` for `POST /edit/plans`

```json
{ "status": "created", "file": "my_plan.yaml" }
```

#### Errors for `POST /edit/plans`

`409` if the plan already exists.

---

### `DELETE /edit/plans/{filename}` — Delete a plan template

#### Response `200` for `DELETE /edit/plans/{filename}`

```json
{ "status": "deleted", "file": "my_plan.yaml" }
```

#### Errors for `DELETE /edit/plans/{filename}`

`404` if not found.

---

## Config

Read and write `config/models.yaml` (model routing) and `config/.env` (API keys).

### `PUT /edit/config` — Save model configuration

Validates the YAML before writing. Optionally updates the project path in `config/settings.yaml` and returns auto-detected engine context.

#### Request Body for `PUT /edit/config` (`application/json`)

| Field | Type | Description |
| ----- | ---- | ----------- |
| `content` | string | Full `models.yaml` content |
| `project_path` | string \| null | Absolute path to the game project root |

#### Response `200` for `PUT /edit/config`

```json
{
  "status": "saved",
  "file": "models.yaml",
  "detected_engine": { "id": "godot4", "name": "Godot 4", "matched": "project.godot" },
  "spec_files": [
    { "path": "data/game_spec.json", "exists": true },
    { "path": "data/level_template.json", "exists": true }
  ]
}
```

`detected_engine` is `null` when no engine is detected or `project_path` was not provided.  
`spec_files` is an empty array when no engine is detected or the engine declares no spec files.  
Each entry in `spec_files` has `path` (relative to project root) and `exists` (boolean).

---

### `PUT /edit/config/keys` — Save API keys to .env

Merges the provided keys into `config/.env`. Only key names declared in `models.yaml` providers (`env_key` field) are accepted. Values are never echoed back in responses.

#### Request Body for `PUT /edit/config/keys` (`application/json`)

| Field | Type | Description |
| ----- | ---- | ----------- |
| `keys` | object | `{ "OPENAI_API_KEY": "sk-..." }` |

#### Response `200` for `PUT /edit/config/keys`

```json
{ "status": "saved", "updated": 1 }
```

#### Errors for `PUT /edit/config/keys`

`422` if a key name is not declared in `models.yaml`.

---

## Engines

CRUD for engine context YAML files stored under `config/engines/`.

### `PUT /edit/engines/{filename}` — Save an engine config file

#### Path Params for `PUT /edit/engines/{filename}`

- `filename`: e.g. `unity.yaml`

#### Request Body for `PUT /edit/engines/{filename}` (`application/json`)

| Field | Type | Description |
| ----- | ---- | ----------- |
| `content` | string | Full YAML content |

#### Response `200` for `PUT /edit/engines/{filename}`

```json
{ "status": "saved", "file": "unity.yaml" }
```

---

### `POST /edit/engines` — Create a new engine config file

#### Request Body for `POST /edit/engines` (`application/json`)

| Field | Type | Description |
| ----- | ---- | ----------- |
| `new_name` | string | Engine filename (`.yaml` appended if missing) |
| `content` | string | Initial YAML content |

#### Response `201` for `POST /edit/engines`

```json
{ "status": "created", "file": "my_engine.yaml" }
```

#### Errors for `POST /edit/engines`

`409` if the file already exists.

---

### `DELETE /edit/engines/{filename}` — Delete an engine config file

#### Response `200` for `DELETE /edit/engines/{filename}`

```json
{ "status": "deleted", "file": "my_engine.yaml" }
```

#### Errors for `DELETE /edit/engines/{filename}`

`404` if not found.
