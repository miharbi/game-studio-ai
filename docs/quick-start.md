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

## 5. Run Your First Plan

Go back to the **Dashboard**.

1. Choose a plan template
2. Choose an engine or leave it on auto-detect
3. Enter your request in the input box
4. Click **Run**

Good first prompts:

- `Add a wall-jump mechanic for the player character`
- `Design a short tutorial level for a 2D action platformer`
- `Write NPC dialogue for a blacksmith in a ruined village`

The run detail page streams live agent output. If a step uses a `human_review` gate, the pipeline pauses until you approve or reject that checkpoint.

---

## 6. Review the Output

From the UI, you can immediately continue into the main workflows:

- **Agents** to edit or create agent prompts
- **Plans** to edit or create plan templates
- **Engines** to inspect or customize engine configs
- **Sprites** to review generated sprite images

---

## CLI Alternative

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

## Where to Go Next

- [agents.md](agents.md) for agent authoring details
- [plans.md](plans.md) for plan schema and run behavior
- [engines.md](engines.md) for engine detection and engine config structure
- [api.md](api.md) for the JSON API and Swagger usage