# Use Node.js 20 Alpine as base image
FROM node:24-alpine

# Set working directory
WORKDIR /app

# Install pnpm globally
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy package files
COPY package.json pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build the application (if needed)
RUN pnpm run build

# Expose port (adjust if different)
EXPOSE 3000

# Start the application
CMD ["pnpm", "start"]