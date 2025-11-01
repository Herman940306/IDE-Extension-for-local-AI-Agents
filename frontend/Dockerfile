# syntax=docker/dockerfile:1.6

# Frontend multi-stage: build with Node, serve via nginx
FROM node:20.19-alpine AS builder
WORKDIR /app
# Install deps
COPY package*.json /app/
RUN npm ci
# Copy source and build
COPY . /app
RUN npm run build

# Runtime image
FROM nginx:1.27.2-alpine AS web
# Copy built static assets
COPY --from=builder /app/dist /usr/share/nginx/html
# Default nginx config is sufficient for static; can be swapped with custom if needed
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
