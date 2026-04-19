# Engine Support Reference

Each engine has a YAML config in `config/engines/` that controls:

- **Detection hints** — file patterns used by `detect()` to identify the engine
- **Sprite dimensions** — pixel sizes per asset type
- **Agent context** — a paragraph injected into every agent prompt when that engine is active

## Engine configs

### Godot 4 (`config/engines/godot4.yaml`)

**Detection:** presence of `project.godot` in the project root

**Sprite dimensions:**

| Asset type | Width | Height | Notes |
|---|---|---|---|
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

### Unity (`config/engines/unity.yaml`)

**Detection:** `ProjectSettings/ProjectVersion.txt` or any `*.sln` file

**Sprite dimensions:**

| Asset type | Width | Height |
|---|---|---|
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

### Unreal Engine 5 (`config/engines/unreal5.yaml`)

**Detection:** any `*.uproject` file in the project root

**Sprite dimensions:**

| Asset type | Width | Height |
|---|---|---|
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

## Adding a new engine

1. Create `config/engines/myengine.yaml` with the structure:

```yaml
name: My Engine
detection:
  files: ["marker_file.ext"]
sprite_dimensions:
  player: {width: 64, height: 64}
  background: {width: 1920, height: 1080}
agent_context: |
  This project uses My Engine. Follow these conventions: ...
```

2. Add a detection case in `src/engines/detect.py` → `detect()` function.

3. The new engine is immediately available with `--engine myengine`.
