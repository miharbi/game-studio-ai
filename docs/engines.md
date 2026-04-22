# Engine Support Reference

Each engine has a YAML config in `config/engines/` that controls:

- **Detection hints** — file patterns used by `detect()` to identify the engine
- **Sprite dimensions** — pixel sizes per asset type
- **Agent context** — a paragraph injected into every agent prompt when that engine is active
- **Spec files** — optional list of JSON files inside the game project that serve as a living game bible, injected per-agent

For installation and first-time project setup, start with [Project Quick Start](quick-start.md).

---

## Using the Web UI

### Setting the project path and auto-detection

Navigate to **Setup** (`/edit/config`) → **Project** tab. Enter the absolute path to your game project root. The server scans the directory against all `detect_files` entries in `config/engines/*.yaml` and shows which engine it matched. The detected engine is injected into every agent prompt for that run.

After detection, a **Spec Files** card shows each file declared in the engine's `spec_files:` list with a **found** or **missing** badge. Missing spec files are skipped at runtime without stopping the run.

### Editing engine configs

Navigate to **Engines** in the sidebar. The page lists all engine YAML files from `config/engines/`.

- **Edit** — click any engine name to open it in the CodeMirror YAML editor. You can modify detection patterns, sprite dimensions, and the agent context paragraph. Changes save immediately via `PUT /edit/engines/{filename}`.
- **Create** — click **New Engine** to add a custom engine config.
- **Delete** — use the delete button on the engine detail page.

> If CodeMirror fails to load (e.g. no internet for the ESM CDN), the editor falls back to a plain textarea.

---

## Auto-Detection

Detection also runs from the CLI:

```bash
python runner.py detect-engine /path/to/project
```

Or pass `--engine` explicitly to skip detection:

```bash
python runner.py run --plan plans/templates/design_feature.yaml --engine godot4
```

---

## Engine Configs

### Godot 4

**Detection:** presence of `project.godot` in the project root

**Spec files declared:**

| Path | Purpose |
| ---- | ------- |
| `data/game_spec.json` | Full game bible — art style, characters, audio, VFX, world authoring rules |
| `data/level_template.json` | Blank world skeleton that `level_designer` and `world_builder` must fill in |

Relevant sections from `game_spec.json` are injected per-agent (e.g. `art_director` receives `art_style` + `characters` + `vfx`; `writer` receives `characters` + `audio`). Both files are injected for `level_designer` and `world_builder`.

**Sprite dimensions:**

| Asset type | Width | Height | Notes |
| ---------- | ----- | ------ | ----- |
| player | 48 | 64 | Base sprite size |
| enemy | 32 | 48 | Base enemy size |
| boss | 64 | 80 | Boss characters |
| background | 768 | 144 | Parallax layer strip |
| prop | 32 | 32 | Environmental props |
| ui | 16 | 16 | Icon assets |

**Key conventions injected into agents:**

- Static typing on all GDScript variables, params, and return types
- `CharacterBody2D` for all characters; never `RigidBody2D` for player
- Physics layers: 1=player, 2=enemy, 3=hitbox, 4=world, 5=props
- Scene transitions always via `GameManager` helpers
- Input by action name, never keycodes
- Audio via `AudioManager` autoload
- Debug output via `DebugOverlay.log()`, never `print()`
- UI strings from `LevelManager.ui()` with hardcoded fallback

---

### Unity

**Detection:** `ProjectSettings/ProjectVersion.txt` or any `*.sln` file

**Sprite dimensions:**

| Asset type | Width | Height |
| ---------- | ----- | ------ |
| player | 64 | 64 |
| enemy | 48 | 48 |
| background | 1920 | 1080 |
| prop | 64 | 64 |
| ui | 32 | 32 |

**Key conventions injected into agents:**

- C# with full type annotations
- `MonoBehaviour` lifecycle (`Awake`, `Start`, `Update`, `FixedUpdate`)
- `ScriptableObject` for data-driven content
- `[SerializeField]` for inspector-exposed fields
- Input via `Input System` package, not legacy `Input.GetKey()`
- Audio via `AudioSource` components managed by an AudioManager
- Physics: `Rigidbody2D` with `Kinematic` for character controllers
- UI: `TextMeshPro` for all text elements

---

### Unreal Engine 5

**Detection:** any `*.uproject` file in the project root

**Sprite dimensions:**

| Asset type | Width | Height |
| ---------- | ----- | ------ |
| player | 256 | 256 |
| enemy | 128 | 128 |
| background | 3840 | 2160 |
| prop | 128 | 128 |
| ui | 64 | 64 |

**Key conventions injected into agents:**

- Blueprint-first approach; C++ for performance-critical systems only
- `PaperZDCharacter` for 2D characters
- Data-driven content via `DataTable` assets
- Input via Enhanced Input System with `InputAction` and `InputMappingContext`
- Audio via MetaSound and Audio Manager Blueprint subsystem
- UI: UMG with Widget Blueprints; no hardcoded positioning

---

## Adding a New Engine

### Via the web UI

1. Navigate to **Engines** in the sidebar
2. Click **New Engine**
3. Paste the YAML structure below and customize it
4. Save — the engine is immediately available

### Via file

1. Create `config/engines/myengine.yaml` with the structure:

    ```yaml
    id: myengine
    name: My Engine
    detect_files:
      - "marker_file.ext"
    sprite_dimensions:
      player: {width: 64, height: 64}
      background: {width: 1920, height: 1080}
    spec_files:                    # optional — omit if you have no game-bible JSON files
      - "data/game_spec.json"
    agent_context: |
      This project uses My Engine. Follow these conventions: ...
    ```

2. The engine is immediately available for detection (no code change needed).

3. To load `spec_files` at runtime, ensure a project path is saved in **Setup → Project**.

> **Note:** The old `detection.files` key is **not** supported. Use `detect_files` (a top-level list).
