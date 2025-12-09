# AI Workflow MCP Server

This MCP (Model Context Protocol) server provides tools and resources for AI-assisted development workflows, optimized for integration with GitHub Copilot in VS Code.

## Features

### Tools

- **run_workflow_phase**: Execute individual workflow phases (planning, architecture, coding, debugging, review)
- **run_full_workflow**: Execute the complete AI workflow sequentially
- **get_workflow_status**: Check the status of workflow artifacts and script availability

### Resources

- **ai-workflow://artifact/{phase}/{file}**: Access workflow artifacts from any phase
- **ai-workflow://capabilities/manifest**: Access the capabilities manifest

## Installation

### For VS Code + GitHub Copilot

1. Install the MCP server package:

   ```bash
   npm install -g @n00tropic/ai-workflow-mcp
   ```

2. Configure VS Code settings (`.vscode/settings.json`):

   ```json
   {
     "mcp": {
       "servers": {
         "ai-workflow": {
           "command": "ai-workflow-mcp",
           "cwd": "/path/to/your/workspace"
         }
       }
     }
   }
   ```

### Manual Installation

1. Clone the repository and navigate to the MCP server directory
2. Install dependencies:

   ```bash
   npm install
   ```

3. Run the server:

   ```bash
   npm start
   ```

## Usage with GitHub Copilot

Once configured, you can use Copilot Chat to interact with AI workflows:

```bash
/run_workflow_phase planning
/run_full_workflow
/get_workflow_status
```

The MCP server provides context-aware suggestions and can execute workflow phases directly from your IDE.

## Architecture

The server dynamically discovers workflow scripts and artifacts, providing a clean interface for AI-assisted development without interrupting existing services. It follows MCP conventions for pluggable integration.

## Error Handling

- Graceful degradation when scripts are missing
- Non-blocking execution for interactive phases
- Comprehensive error reporting for debugging

## Security

- No network access required
- Local file system access only
- No persistent state or external dependencies
