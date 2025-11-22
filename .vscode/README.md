# Visual Studio Code workspace visibility

This workspace has been configured so the Explorer reflects the actual files on disk, including files normally hidden by `.gitignore`.

Key settings:

- `explorer.excludeGitIgnore: false`: show files normally hidden by `.gitignore`.
- `search.useIgnoreFiles: false`: include all files in Search results regardless of `.gitignore`.
- `files.exclude` minimal: only `**/.git` is kept hidden by default.
- `files.watcherExclude` excludes `node_modules` and virtual environments from filesystem watchers to avoid performance issues while keeping them visible in Explorer.

If you prefer to hide large folders such as `node_modules` in the Explorer while keeping the rest of the filesystem visible, open `.vscode/n00tropic-cerebrum.code-workspace` and enable the patterns in `files.exclude`.

To revert to the typical VS Code defaults:

1. Set `explorer.excludeGitIgnore: true` to hide files from `.gitignore`.
2. Add a `**/node_modules` `**/.venv-*` pattern in `files.exclude`.

Need a different visibility mix (for example, hide `node_modules` but still show virtual environments)? Share the desired patterns and the workspace settings can be updated to match.
