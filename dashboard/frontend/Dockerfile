# Production image for the Agentic Dashboard frontend.
# Multi-stage: build static assets with Node, serve them with nginx.
#
#   docker build -f dashboard/frontend/Dockerfile -t agentic-dashboard-frontend ./dashboard/frontend
#
# (The provided dashboard/docker-compose.prod.yml already sets this context.)

# ---- Build stage ----
FROM node:20-alpine AS build

WORKDIR /app

# Install deps (use lockfile-aware install when available)
COPY package.json package-lock.json* ./
RUN npm ci 2>/dev/null || npm install

COPY . .

# Requests are reverse-proxied through nginx in production.
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=${VITE_API_BASE}
# Type-check (tsc -b) and emit the production bundle (vite build).
RUN npm run build

# ---- Serve stage ----
FROM nginx:alpine AS serve

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
    CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
