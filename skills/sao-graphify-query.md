---
name: sao-graphify-query
description: "Query Sira-Vault knowledge graph using local Graphify MCP server (port 20476)."
tags: ["graph", "vault", "mcp", "memory"]
---

# SAO Graphify Query Tool

## Purpose
Allow Sira (Hermes) to perform spatial reasoning over the entire Sira-Vault without reading thousands of files.

## How It Works
Graphify MCP server is launched by `start.ps1` and listens on `localhost:20476`. It indexes `C:\Users\gilang\Documents\Sira-Vault`.

## Available Commands (via Hermes Tool)

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
Since Graphify runs as MCP server, Hermes can register it via:
```yaml
mcp:
  servers:
    - name: graphify
      command: ["python", "-m", "graphify", "--mcp", "C:/Users/gilang/Documents/Sira-Vault"]
```

Once registered, Sira can call:
- `graphify_query`
- `graphify_path`
- `graphify_explain`

## Best Practice
1. Always start with `graphify query` to discover relevant nodes.
2. Only `read_file` the nodes returned by Graphify.
3. Never read entire folders manually.

## Benefit
- Token efficient (only relevant files are read).
- Context-aware (understands community clusters in Vault).
- Always up-to-date (Graphify --update runs on git commit).