# ERPNext Docker Image Cache

The platform team keeps a minimal `docker compose` definition here so we can pull
and cache the latest ERPNext images before orchestration scripts need them. The
stack is intentionally inert – every service runs `tail -f /dev/null` by default
so developers don’t accidentally boot a full bench when they only need fresh
images.

## Usage

```bash
# Ensure secrets (optional) exist
cp local.env.example local.env  # if you want docker compose to export these vars

# Pull the currently pinned versions (see .env)
docker compose -f docker-compose.yml pull

# Or run the workspace helper to fetch the newest tags
node scripts/docker-sync.mjs --only erpnext
```

The helper script updates `.env` with the latest `frappe/erpnext-*` tag observed
on Docker Hub and records the result in
`n00tropic_HQ/12-Platform-Ops/telemetry/docker-sync.log`. Breaking changes are
handled manually during integration tests, so the automation simply fetches the
new images and leaves them paused until the bench stack or CI decides to run
with them.
