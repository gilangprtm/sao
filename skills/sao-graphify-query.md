---
name: sao-graphify-query
description: "Query the user's vault knowledge graph via local Graphify MCP (port 20476)."
tags: ["graph", "vault", "mcp", "memory"]
---

# SAO Graphify Query Tool

## Purpose
Allow Sira (Hermes) to perform spatial reasoning over the **user's vault** without reading thousands of files.

## How It Works
1. Vault path is stored in `~/.sao/config.json` → key `vault_path` (set by `sao create vault` / `sao setup vault`).
2. `sao start` launches Graphify MCP on `localhost:20476` against **that** vault path (never a hardcoded user folder).
3. Query tools hit the running MCP — do **not** invent absolute paths.

## Resolve vault path (if needed)
```bash
# Windows / Git Bash
cat ~/.sao/config.json
# or
python -c "import json,os; print(json.load(open(os.path.expanduser('~/.sao/config.json')))['vault_path'])"
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
`sao start` should keep MCP registration in sync with the vault path from config. Example shape (path is **dynamic**):

```yaml
mcp:
  servers:
    graphify:
      command: ["python", "-m", "graphify", "--mcp", "<VAULT_PATH_FROM_SAO_CONFIG>"]
```

Replace `<VAULT_PATH_FROM_SAO_CONFIG>` with the real `vault_path` from `~/.sao/config.json`.  
**Never** hardcode `C:\Users\<someone>\Documents\...`.

Once registered, Sira can call:
- `graphify_query`
- `graphify_path`
- `graphify_explain`

## Best Practice
1. Always start with `graphify query` to discover relevant nodes.
2. Only `read_file` the nodes returned by Graphify.
3. Never read entire folders manually.
4. Never assume a default vault path — always read config or use the running MCP.

## Benefit
- Token efficient (only relevant files are read).
- Context-aware (understands community clusters in Vault).
- Always up-to-date (`graphify update` on `sao start` + after `sao ingest`).
