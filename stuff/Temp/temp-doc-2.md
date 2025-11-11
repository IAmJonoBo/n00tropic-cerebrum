**Copilot, perform an E2E docs migration to Antora (multi-repo, tagged, searchable)**

You are an expert repo-migration assistant. Execute the following tasks exactly, opening PRs as needed. Use concise commits with conventional prefixes (e.g., **docs:**, **ci:**). Assume this repo is the **root** (**n00-cerebrum**) and may reference sibling repos in the **IAmJonoBo** org.

## **0) Preconditions**

* Create a new branch in **each affected repo** named **docs/antora-migration**.
* Detect all repos in this org that belong to the n00 ecosystem (pattern: **n00*** or those linked in this superrepo’s README/submodules). If discovery fails, at minimum apply the steps to this repo and leave TODOs for others.

## **1) Per-repo structure (standalone docs)**

For **each** repo (including this one if it has product/service docs):

1. Add **docs/antora.yml** with this minimal component descriptor (substitute sensible **name:**; for **version**, prefer latest git tag else **main**):

```
name: <component-name>
title: <Human Title>
version: ~
nav:
  - modules/ROOT/nav.adoc
```

2. Create the Antora module layout:

```
docs/
  modules/
    ROOT/
      pages/
      partials/
      images/
      examples/
```

3. Convert existing Markdown docs to AsciiDoc (lossless where possible). For each ***.md** under **docs/** or legacy locations, run **Kramdown-AsciiDoc** and place results under **pages/**, preserving relative paths:

```
# example conversion; keep original MD, write .adoc siblings in pages/
kramdoc -o docs/modules/ROOT/pages/${file%.md}.adoc $file
```

4. On **every page**, ensure a proper header with title and attributes (one per line). Include tagging and review metadata:

```
= <Page Title>
:page-tags: diataxis:<tutorial|howto|reference|explanation>, domain:<product|platform|ops>, audience:<user|operator|agent|contrib>, stability:<draft|beta|stable>
:reviewed: 2025-11-11
```

5. Create a curated **docs/modules/ROOT/nav.adoc** representing the per-repo standalone navigation.
6. Replace inline code/config blocks that duplicate source with **includes** from real files using **tagged regions**. Add tags in code files:

```
# in source file (example)
# tag::snippet-cli[]
n00 --help
# end::snippet-cli[]
```

Then include in docs:

```
include::../../../../path/to/file.ext[tags=snippet-cli]
```

7. Factor repeated blurbs/tables into **partials/** and reuse via **include::partial$`<name>`.adoc[]**.

## **2) Root aggregation from** ****

## **n00-cerebrum**

1. **Add **antora-playbook.yml** at repo root:**

```
site:
  title: n00 Docs
  start_page: n00-cerebrum::index.adoc
content:
  sources:
    # One entry per repo; prefer 'start_paths: docs' once each repo is migrated
    - url: https://github.com/IAmJonoBo/n00-cerebrum.git
      branches: [ main ]
      start_paths: [ docs ]
    # Add more repos discovered by pattern (fill automatically)
    # - url: https://github.com/IAmJonoBo/<other-repo>.git
    #   branches: [ main ]
    #   start_paths: [ docs ]
ui:
  bundle:
    url: https://cdn.antora.org/ui/default
    snapshot: true
antora:
  extensions:
    - @antora/lunr-extension
asciidoc:
  attributes:
    page-pagination: ''
    sectanchors: ''
    icons: font
    source-highlighter: highlight.js
runtime:
  fetch: true
```

2. Create a root landing page **docs/modules/ROOT/pages/index.adoc** that links to components and Diátaxis sections; ensure it’s tagged and includes a short taxonomy guide.
3. Create root curation nav **docs/modules/ROOT/nav.adoc** that stitches together the ecosystem.

## **3) Search (now/offline and prod)**

* **Now (offline):** Use the Lunr extension (already added in playbook) and verify a client-side index is generated in **build/site**.
* **Prod option A:** wire **Algolia DocSearch** (crawler-based).
* **Prod option B:** wire **Typesense DocSearch** (self-hosted).
  Create **docs/search/README.adoc** that explains which mode is active and how to re-index.

**If ****Typesense** is chosen, add scripts/docsearch.typesense.env.example** and **docsearch.config.json** plus a GH Action **search-reindex.yml** that runs the ****typesense-docsearch-scraper** on deploy.

## **4) CI: link health, style, metadata, build & deploy**

1. **Vale** (prose lint). Add a **.vale.ini** at repo root and a **styles/n00** folder with basic rules (Oxford English and terminology).
2. **Lychee** (link checker). Add **.lychee.toml** tuned for rate limits and domain allowlists.
3. **Front-matter / attribute checks.** For AsciiDoc pages, enforce presence of **:page-tags:** and **:reviewed:** using a tiny Node script **scripts/check-attrs.mjs** (fail if missing or if **:reviewed:** > 90 days old).
4. **DangerJS** for PR policy (e.g., docs touched ⇒ require **:reviewed:** updated).
5. **Antora build & Pages deploy.** Add **ci/docs.yml** (GitHub Actions) that runs vale, lychee, attribute checks, builds Antora (with Lunr), uploads artifact, then deploys to **GitHub Pages** for this repo. If you publish elsewhere, adapt to Cloudflare Pages.

### **Files to add**

**.vale.ini**

```
StylesPath = styles
MinAlertLevel = warning
Packages = Google, Microsoft
[*.{adoc,md}]
BasedOnStyles = Vale, Google, Microsoft
# Prefer Oxford English; you can add custom substitutions in styles/n00
```

**styles/n00/Headings.yml** (example house style rule)

```
extends: existence
message: "Avoid gerunds in headings."
level: warning
scope: heading
tokens:
  - '\b\w+ing\b'
```

**.lychee.toml**

```
verbose = true
exclude = ["^mailto:", "localhost", "127.0.0.1"]
retry = { count = 2, code = [429, 500, 502, 503, 504] }
```

**scripts/check-attrs.mjs**

```
import { readFileSync } from "node:fs";
import { glob } from "glob";

const files = await glob("docs/modules/**/pages/**/*.adoc");
let failed = false, now = new Date();

for (const f of files) {
  const s = readFileSync(f, "utf8");
  const hasTags = /^:page-tags:\s?.+/m.test(s);
  const m = /^:reviewed:\s?(\d{4}-\d{2}-\d{2})/m.exec(s);
  if (!hasTags) { console.error(`Missing :page-tags: -> ${f}`); failed = true; }
  if (!m) { console.error(`Missing :reviewed: -> ${f}`); failed = true; }
  else {
    const dt = new Date(m[1]);
    const age = (now - dt) / (1000*60*60*24);
    if (age > 90) { console.error(`Stale :reviewed: (${m[1]}) -> ${f}`); failed = true; }
  }
}
if (failed) process.exit(1);
```

**Dangerfile.ts** (key checks)

```
import { danger, fail, warn, message } from "danger";
const mdChanged = danger.git.modified_files.filter(f => f.endsWith(".adoc") || f.endsWith(".md"));
if (mdChanged.length) {
  message(`Docs changed: ${mdChanged.length} files`);
  // Encourage review date updates when docs change
  const stale = mdChanged.filter(f => danger.github.utils.fileContents(f).then(c => !/^:reviewed:\s?\d{4}-\d{2}-\d{2}/m.test(c)));
  Promise.all(stale).then(list => { if (list.length) warn("Some docs missing :reviewed: date."); });
}
```

**.github/workflows/docs.yml**

```
name: docs
on:
  push: { branches: [ main ] }
  pull_request:
permissions:
  contents: write
  pages: write
  id-token: write
jobs:
  build-validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0, submodules: recursive }
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - name: Install Antora + extensions
        run: |
          # Install Antora tooling locally via pnpm and run using pnpm exec
          pnpm install
          pnpm exec antora antora-playbook.yml --stacktrace
      - name: Vale
        uses: errata-ai/vale-action@v2
        with: { files: "docs" }
      - name: Link check
        uses: lycheeverse/lychee-action@v2
        with:
          args: --config .lychee.toml 'docs/**/*.adoc' 'docs/**/*.md' '**/*.html'
      - name: Attr checks
        run: node scripts/check-attrs.mjs
      - name: Build Antora
  run: pnpm exec antora antora-playbook.yml --stacktrace
      - name: Upload site artifact
        uses: actions/upload-pages-artifact@v3
        with: { path: build/site }
  deploy:
    if: github.ref == 'refs/heads/main'
    needs: build-validate
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to GitHub Pages
        uses: actions/deploy-pages@v4
```

> If publishing to Cloudflare Pages, swap the deploy job for a **wrangler pages deploy** step.

## **5) Optional: Typesense DocSearch integration**

* **Add **.github/workflows/search-reindex.yml** that runs after **deploy** and executes the ****typesense-docsearch-scraper** using docsearch.config.json**.**
* Provide **docsearch.config.json** with selectors for Antora’s HTML.

## **6) Optional: MCP “docs” server (read-only)**

Create a small MCP server (Python) that serves three tools: **search(query)**, **get_page(id)**, **list_tags()**. Put it in **mcp/docs_server/** with a README and an example client config. Ensure **allowlisted** paths to **build/site** and **docs/**.

**Skeleton **mcp/docs_server/server.py**:**

```
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("n00-docs")

@mcp.tool()
def list_tags() -> list[str]:
    # parse tags from pages (e.g., scan .adoc headers) or from a generated JSON during build
    return sorted(set( ... ))

@mcp.tool()
def search(query: str) -> list[dict]:
    # simple grep/Lunr-query wrapper over build/site index.json
    return [ ... ]  # [{id, title, url, score, tags}]

@mcp.tool()
def get_page(id: str) -> dict:
    return { "id": id, "html": open(f"build/site/{id}.html").read() }

if __name__ == "__main__":
    mcp.run()
```

Add a **Makefile** target **make mcp-dev** to run it locally.

## **7) E2E validation**

1. **Build** with pnpm exec antora antora-playbook.yml** and confirm output in **build/site**.**
2. **Search (Lunr):** confirm the search box returns results; verify tags are present in page metadata and visible in the UI (can be surfaced via a small UI partial if desired).
3. **Links & style:** GH Action shows **Vale** and **Lychee** passing.
4. **Freshness:** the attribute script and DangerJS pass; no **:reviewed:** older than 90 days.
5. **Includes:** intentionally change a tagged source snippet and rebuild; confirm docs update by construction.
6. **(Optional) DocSearch:** run reindex workflow and verify results.
7. **(Optional) MCP server:** run locally, call **list_tags**, **search**, **get_page**, verify content.

## **8) Deliverables**

* PR(s) per repo adding Antora structure, converted pages, tags, nav.
* Root PR adding **antora-playbook.yml**, root pages/nav, CI workflows, and (optional) search/MCP extras.
* A short **CONTRIBUTING-docs.adoc** explaining Diátaxis, tagging, review SLA, and snippet tagging.

---

## **Notes and key references**

* Antora is built for **single or multi-repository** sites; aggregate with a **playbook** and **content.sources**. Modules hold pages/partials/examples/images. Page attributes (including custom **page-***) flow to the UI/search.
* Use **include tagged regions** to pull real code/config snippets to prevent drift.
* **Lunr extension** provides offline search; DocSearch (Algolia) or **Typesense DocSearch** are production options.
* **Vale** for style linting; GitHub Action available. **Lychee** for link checking; Action available.
* Markdown → AsciiDoc migration via **kramdown-asciidoc** (preferred) or Pandoc.
* MCP spec/registry if exposing docs to agents via a read-only server.
