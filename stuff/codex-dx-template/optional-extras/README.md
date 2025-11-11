# Optional Extras: Docker Deployment

This directory contains Docker files and setup instructions for deploying the Codex DX Template in a containerized environment.

## Prerequisites

- Docker installed on your system
- Docker Compose (optional, for multi-service setups)

## Quick Start

1. **Build the Docker image:**

   ```bash
   docker build -t codex-dx-template .
   ```

2. **Run the container:**

   ```bash
   docker run -p 3000:3000 codex-dx-template
   ```

   Adjust the port if your application uses a different one.

## Docker Compose (Multi-Service)

If your project has both Node.js and Python components, use the provided `docker-compose.yml`:

```bash
docker-compose up --build
```

This will start all services defined in the compose file.

## Environment Variables

Set environment variables as needed for your application. For example:

```bash
docker run -e NODE_ENV=production -e API_KEY=your_key -p 3000:3000 codex-dx-template
```

## Development vs Production

- **Development**: Use `docker-compose.dev.yml` for development with volume mounts.
- **Production**: Use the standard `Dockerfile` and `docker-compose.yml` for optimized builds.

## Troubleshooting

- **Port conflicts**: Change the host port in `docker run` or `docker-compose.yml`.
- **Permissions**: Ensure Docker has access to the project directory.
- **Build failures**: Check that all dependencies are properly listed in `package.json` or `requirements.txt`.

## Customization

Modify the `Dockerfile` and `docker-compose.yml` to fit your specific project needs. For example:

- Add more services for databases or caches.
- Include additional build steps for your application.
- Adjust base images for different Node.js or Python versions.
