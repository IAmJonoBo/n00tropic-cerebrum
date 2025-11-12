# Minimal dev container (override per framework)
FROM node:24-alpine
WORKDIR /app
COPY ./apps/web/package.json ./apps/web/pnpm-lock.yaml* ./apps/web/
WORKDIR /app/apps/web
RUN corepack enable && corepack prepare pnpm@latest --activate && pnpm install || true
WORKDIR /app
COPY . .
EXPOSE 5173
CMD ["pnpm","run","dev","--prefix","apps/web"]
