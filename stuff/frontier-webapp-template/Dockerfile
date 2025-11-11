# Minimal dev container (override per framework)
FROM node:20-alpine
WORKDIR /app
COPY ./apps/web/package.json ./apps/web/package-lock.json* ./apps/web/
RUN cd apps/web && npm install --no-audit --no-fund || true
COPY . .
EXPOSE 5173
CMD ["npm","run","dev","--prefix","apps/web"]
