# MCP Quickstart

The MCP server exposes a `dj-company` tool that Claude / Codex / Gemini can call to read & write your company's DJ data.

## 1. Install

```bash
pip install "dynamitejobs[mcp]"
```

## 2. Save your key

```bash
python3 -m dynamitejobs setup --api-key dj_<companyID>_<random>
python3 -m dynamitejobs self-test
```

## 3. Register with your AI tool

### Claude Code (per project)

Add to `.mcp.json` in the project root:

```json
{
  "mcpServers": {
    "dj": {
      "command": "python3",
      "args": ["-m", "dynamitejobs", "--mcp"]
    }
  }
}
```

Restart Claude Code in that project — the `dj` MCP server appears in the tool list.

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "dj": {
      "command": "python3",
      "args": ["-m", "dynamitejobs", "--mcp"]
    }
  }
}
```

### Codex CLI / Cursor / Gemini CLI

See each tool's MCP docs — the binary is `python3 -m dynamitejobs --mcp` regardless of tool.

## 4. Try it

In Claude/Codex:

> "Use the dj tool to list our 5 most recent published jobs and tell me which has the most applications."

The agent will call `dj.jobs(status="published", limit=5)`, then `dj.applications(<jobID>)` for each, and synthesize the answer.
