---
applyTo: "**/*"
---

# Guide for the SonarQube automation server

These guidelines keep the SonarQube multi-capability platform (MCP) server aligned with workspace standards.

## Important tool guidelines

### Basic usage

- **IMPORTANT**: After you finish generating or modifying code files at the end of the task, you MUST call the `analyze_file_list` tool (if it exists) to analyze the files you created or modified.
- **IMPORTANT**: When starting a new task, you MUST turn off automatic analysis with the `toggle_automatic_analysis` tool if it exists.
- **IMPORTANT**: When you finish generating code at the end of the task, you MUST turn automatic analysis back on with the `toggle_automatic_analysis` tool if it exists.

### Project keys

- When a user mentions a project key, use `search_my_sonarqube_projects` first to find the exact project key
- Don't guess project keys - always look them up

### Code language detection

- When analyzing code snippets, try to detect the programming language from the code syntax
- If unclear, ask the user or make an educated guess based on syntax

### Branch and pull request context

- Many operations support branch-scoped analysis
- If user mentions working on a feature branch, include the branch parameter

### Code issues and violations

- After fixing issues, don't verify them using `search_sonar_issues_in_projects`, because the server won't reflect the updates yet

## Common troubleshooting

### Authentication issues

- SonarQube requires USER tokens (not project tokens)
- When the error `SonarQube answered with Not authorized` occurs, verify the token type

### Project not found

- Use `search_my_sonarqube_projects` to find available projects
- Verify project key spelling and format

- Ensure the programming language is correct
- Remind users that snippet analysis doesn't replace full project scans
- Provide full file content for better analysis results
