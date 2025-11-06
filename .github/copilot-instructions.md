# GitHub Copilot Instructions for n00tropic Cerebrum

## AI Workflow Integration

When working with AI-assisted development workflows:

- Use the available MCP tools to execute workflow phases
- Always check workflow status before making changes
- Prefer interactive mode for planning phases, automated for implementation
- Generate artifacts in the appropriate directories

## Available MCP Tools

- `run_workflow_phase`: Execute individual phases (planning, architecture, coding, debugging, review)
- `run_full_workflow`: Execute complete workflow sequentially
- `get_workflow_status`: Check artifact status and script availability

## Workflow Best Practices

1. Start with planning phase to gather requirements
2. Use architecture phase for design decisions
3. Implement in coding phase with proper error handling
4. Test thoroughly in debugging phase
5. Review and deploy in final phase

## Code Quality Standards

- Follow TypeScript/JavaScript best practices
- Include proper error handling and logging
- Generate comprehensive tests
- Document APIs and interfaces
- Use semantic versioning for releases

## Security Considerations

- Validate all inputs and sanitize data
- Use parameterized queries for database operations
- Implement proper authentication and authorization
- Log security events appropriately
- Follow principle of least privilege
