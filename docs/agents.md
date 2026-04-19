# Agent Authoring Guide

Agents are markdown files with a YAML frontmatter block followed by the system prompt body.

## File location

```
agents/
├── tier1/    # creative_director, technical_director, producer
├── tier2/    # leads and directors
└── tier3/    # specialist implementers
```

## Format

```markdown
---
name: my_agent
tier: 2
reports_to: creative_director
domain: my specialized domain
model_override: github/gpt-4.1   # optional — overrides config/models.yaml for this agent
---
You are the My Agent. Write the full system prompt here.

Your responsibilities:
- ...

Your output format:
## Section heading
[description]
```

## Required frontmatter fields

| Field | Type | Description |
|---|---|---|
| `name` | string | Snake_case agent name, matches the filename (without `.md`) |
| `tier` | int | 1, 2, or 3 |
| `reports_to` | string \| null | Parent agent name, or `null` for Tier 1 roots |
| `domain` | string | One-line description of expertise |

## Optional frontmatter fields

| Field | Type | Description |
|---|---|---|
| `model_override` | string | litellm model ID — overrides the tier default for this specific agent |

## System prompt guidelines

- **Be specific about output format.** Agents that produce structured output (JSON, code, design specs) should include the exact format in their system prompt so the orchestrator can validate it.
- **Include a constraint section.** List the rules the agent must never break (e.g., no hardcoded values, 60-character dialogue limit).
- **Engine awareness.** The orchestrator injects engine context automatically, but agents can reference engine-specific patterns explicitly.
- **Tier 1 agents own decisions.** Their prompts should include APPROVED/REJECTED patterns since they are used as gates.

## Referencing a custom agent in a plan

Use the `name` field value exactly as the `agent` field in a plan step:

```yaml
steps:
  - id: my_step
    agent: my_agent
    tier: 2
    action: "Do something with my agent."
    gate: auto
```
