# Why open the workspace file?

This project is organized as a multi-root workspace and contains several folders such as `n00t`, `n00plicate`, `n00-cortex` and `n00-frontiers`. If you open the repository folder directly in VS Code you may not see the multi-root layout or folders listed as separate root entries.

## How to open the workspace file

1. In VS Code: File -> Open Workspace... -> choose `n00tropic-cerebrum.code-workspace` at the repository root.
2. Alternatively, from the Command Palette: `File: Open Workspace` and select the same file.

## Reloading

If Explorer still looks different after opening the workspace, use Developer: Reload Window to ensure styles and settings are reloaded.

Tip: Avoid adding the repository root (`.` / `cerebrum-root`) and the submodule folders at the same time in the workspace if you want each submodule to appear as an independent top-level folder. When both are present, VS Code may hide the nested submodule roots in Explorer and they can appear empty.

If you prefer the workspace to show everything exactly as the OS folder (no filters):

- `explorer.excludeGitIgnore: false`: show files in Explorer even if they are in `.gitignore`.
- `search.useIgnoreFiles: false`: include files that are normally gitignored in search.
- `files.exclude` is set only to hide `**/.git` by default; change this if you prefer other folders hidden.

If `n00t` or `n00plicate` still fail to appear in the Explorer after opening this workspace file, verify the folder exists on disk and note how VS Code was opened (for example, `Open Folder` or `Open Workspace`).

Pro tip to match repos & branches visually

- Install GitLens (`eamodio.gitlens`) for helpful overlays in Explorer and the status bar. It shows branch and remote info next to repositories and files.
- Use Git Graph (`mhutchie.git-graph`) to open a graphical view of remotes and branches.
- Ensure `git.autoRepositoryDetection` is enabled (workspace setting) so submodule repositories are discovered and listed in the Source Control view.

How to get branches and remotes visible in Explorer and Source Control

1. Install GitLens (recommended):
   - Open Extensions view → search `GitLens` → Install.
   - Open the GitLens view (left sidebar) → Repositories → click a repo to expand branches/tags.
2. Use the built-in Source Control view: the repo drop-down in the Source Control panel shows each micro-repo and its current branch.
3. Auto-fetch: `git.autofetch` is enabled in the workspace to keep remote branch lists up-to-date automatically.
