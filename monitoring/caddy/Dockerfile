# Build Caddy with Prometheus metrics plugin
FROM caddy:2.8.4-builder AS builder
RUN xcaddy build \
    --with github.com/mohammed90/caddy-prometheus

FROM caddy:2.8.4
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
# Use default Caddy entrypoint; config mounted via compose
