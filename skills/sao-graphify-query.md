---
name: sao-graphify-query
description: "Query the user's vault knowledge graph via Graphify MCP registered in Hermes (stdio)."
tags: ["graph", "vault", "mcp", "memory"]
---

# SAO Graphify Query Tool

## Purpose
Allow Sira (Hermes) to perform spatial reasoning over the **user's vault** without reading thousands of files.

## How It Works
1. Vault path is stored in `~/.sao/config.json` → key `vault_path` (set by `sao create vault` / `sao setup vault`).
2. On every `sao start` / create / setup, SAO also writes:
   - `~/.hermes/sao_vault_path.txt` (and `%LOCALAPPDATA%/hermes/sao_vault_path.txt`)
   - `~/.hermes/sao_vault.json` (includes `hermes_state_db`)
   - injects absolute path into vault `AGENTS.md` (`{{VAULT_PATH}}` → real path)
3. **Graphify MCP is owned by Hermes (stdio)** — registered under `mcp_servers.graphify` in Hermes `config.yaml`.
   - No separate SAO process on port 20476 required.
   - Hermes restarts Graphify with the agent lifecycle.
4. Env for workers/subconscious: `SAO_VAULT_PATH`, `HERMES_STATE_DB` / `SAO_HERMES_STATE_DB`.

## Resolve vault path (always dynamic)
```bash
# Preferred
cat ~/.sao/config.json
# Pointer for agents
cat ~/.hermes/sao_vault_path.txt
# or
python -c "import json,os; print(json.load(open(os.path.expanduser('~/.sao/config.json')))['vault_path'])"
```

## Resolve Hermes state.db (session source)
```bash
echo $HERMES_STATE_DB
# or
python -c "from scripts.subconscious import resolve_hermes_state_db; print(resolve_hermes_state_db())"
```

## Available Commands (via Hermes Tool / CLI)

### 1. Basic Query (BFS)
```bash
graphify query "Apa saja prinsip E2E testing di vault?"
```

### 2. Path Finding
```bash
graphify path "AGENTS.md" "SOM.md"
```

### 3. Explain Node
```bash
graphify explain "SIS.md"
```

## Integration with Hermes
`sao start` registers Graphify under Hermes **stdio MCP** (not a fixed HTTP port):

```yaml
mcp_servers:
  graphify:
    command: <graphify-venv-python-or-python>
    args: ["-m", "graphify", "--mcp", "<VAULT_PATH_FROM_SAO_CONFIG>"]
    enabled: true
```

Replace paths with values from `~/.sao/config.json` / `sao_vault.json`.  
**Never** hardcode `C:\Users\<someone>\Documents\...`.

Once registered, Sira can call Graphify tools via Hermes MCP.

## Best Practice
1. Always start with `graphify query` to discover relevant nodes.
2. Only `read_file` the nodes returned by Graphify.
3. Never read entire folders manually.
4. Never assume a default vault path — always read config or use the running MCP.

## Benefit
- Token efficient (only relevant files are read).
- Context-aware (understands community clusters in Vault).
- Always up-to-date (`graphify update` on `sao start` + after `sao ingest`).
