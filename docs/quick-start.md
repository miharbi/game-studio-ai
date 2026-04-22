# Project Quick Start

This guide walks through the fastest way to get Game Studio AI running for the first time.

If you only need feature-specific reference material after setup, continue with [Agent Authoring Guide](agents.md), [Plan YAML Schema Reference](plans.md), [Engine Support Reference](engines.md), or [API Reference](api.md).

---

## 1. Install the Project

```bash
git clone <repo-url> game-studio-ai
cd game-studio-ai
pip install -e ".[dev]"
```

If you want the native desktop window instead of a browser tab, install the optional desktop dependency too:

```bash
pip install -e ".[desktop]"
```

---

## 2. Start the App

Launch the UI in a browser:

```bash
python runner.py serve
```

Then open `http://localhost:8000`.

Or launch the same UI in a native desktop window:

```bash
python runner.py desktop
```

Both modes use the same FastAPI + htmx interface and the same project data.

---

## 3. Configure Providers in the UI

Open **Setup** in the sidebar.

In **API Keys**:

1. Paste at least one provider key such as `GITHUB_TOKEN` or `OPENAI_API_KEY`
2. Save the form
3. Confirm the provider is now shown as active

Keys are written to `config/.env`, which is git-ignored.

In **Tiers**:

1. Pick a model for Tier 1, Tier 2, and Tier 3
2. Save the configuration

Only models from providers with a configured API key are available in these dropdowns.

---

## 4. Set Your Game Project Path

Still in **Setup**, open the **Project** tab and enter the absolute path to your game project.

The app will auto-detect the engine when possible:

- `godot4` from `project.godot`
- `unity` from `ProjectSettings/ProjectVersion.txt` or `*.sln`
- `unreal5` from `*.uproject`

If you are just exploring the tool, you can skip this step and select an engine manually when you run a plan.

If the detected engine declares `spec_files`, those JSON files from your project are shown with a **found** or **missing** badge. When found, their relevant sections are automatically injected into each agent prompt during runs — no extra configuration needed.

---

## 5. The Dashboard

The Dashboard is the main launching pad for running plans and reviewing recent activity. Open it at `http://localhost:8000`.

### The Run Form

| Field | What it does |
| ----- | ------------ |
| **Plan template** | Selects a YAML file from `plans/templates/`. Each template defines a specific pipeline — use `design_feature` for feature concepts, `write_dialogue` for NPC text, `generate_sprites` for AI images, etc. |
| **Engine** | Overrides the engine for this run only. Leave on *auto-detect* to let the app infer the engine from your project directory (set in Setup → Project). |
| **Input** | Free-text prompt passed directly to the first agent step. Be specific — the more context you give, the better the output. |

Click **Run**. The page redirects to the **Run Detail** view where agent output streams in real time.

### Status Alerts on the Dashboard

| Alert | Meaning |
| ----- | ------- |
| **Setup required** | No model has been assigned to a tier yet — go to Setup → Tiers. |
| **No API key** | A provider is selected but its API key variable is missing — go to Setup → API Keys. |
| **Engine auto-detect unavailable** | No project path is set — go to Setup → Project, or pick an engine manually. |

### Recent Runs

Below the run form the last several pipeline runs are listed with their status:

- **running** — currently executing (click to watch live output)
- **paused** — waiting at a `human_review` gate — click to approve or reject
- **complete** — all steps finished successfully
- **failed** — a step errored; click to see which step and why

Click any run row to open its detail page and read the full agent output.

### Running Your First Plan

Good first inputs to try:

- `Add a wall-jump mechanic for the player character`
- `Design a short tutorial level for a 2D action platformer`
- `Write NPC dialogue for a blacksmith in a ruined village`

---

## 6. The Sprite Gallery

The Sprite Gallery (`/sprites`) shows AI-generated images waiting for your review.

### How Sprites Are Generated

1. From the Dashboard, run a plan that uses the `generate_sprites` template.
2. The agent pipeline writes a **sprite spec** — a JSON object with `name`, `prompt`, `width`, `height`, and optionally `style` for each sprite.
3. The app calls your configured image provider and saves the resulting images to `output/sprites/`.
4. The images appear in the gallery, grouped under **Pending Review**.

### Sprite Providers

Configure the provider in **Setup → Sprites**.

| Provider | Description |
| -------- | ----------- |
| `stub` | Returns a small placeholder PNG immediately — no API calls, ideal for testing the pipeline without spending credits. |
| `openai` | Calls DALL-E 3 via the OpenAI API. Requires `OPENAI_API_KEY` in Setup → API Keys. |
| `stable_diffusion` | Posts to a Stable Diffusion WebUI REST API (local or remote). Set the endpoint URL in the Sprites config panel. |

### Approving and Rejecting

- **Approve** moves the image from `output/sprites/` to `output/approved/` — it is ready to import directly into your engine project.
- **Reject** deletes the image file permanently.

The gallery preview uses CSS `image-rendering: pixelated` so pixel-art sprites do not appear blurry at display scale.

---

## 7. Review the Output

From the UI, you can immediately continue into the main workflows:

- **Agents** to edit or create agent prompts
- **Plans** to edit or create plan templates
- **Engines** to inspect or customize engine configs
- **Sprites** to review generated sprite images

---

## 8. CLI Alternative

If you prefer to work from the terminal after configuration, these are the main commands:

```bash
# Run a plan
python runner.py run --plan plans/templates/design_feature.yaml \
    --engine godot4 \
    --input "Add a wall-jump mechanic"

# Resume an interrupted run
python runner.py resume <run-id>

# List available templates
python runner.py list-plans

# Detect the engine for a project path
python runner.py detect-engine /path/to/project
```

---

## 9. Where to Go Next

- [agents.md](agents.md) for agent authoring details
- [plans.md](plans.md) for plan schema and run behavior
- [engines.md](engines.md) for engine detection and engine config structure
- [api.md](api.md) for the JSON API and Swagger usage