# Build assets inside the image; no local dist directory is required.
FROM oven/bun:1.2.20@sha256:78f46b81b82d767ee8d729411f6f95089a403c21f17c20a5789df00263d7c5b5 AS builder
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
COPY . .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN bun run build

FROM nginx:alpine@sha256:df221db836e1754089190208cee7eeda94f233197056426eda74a43ab1abeac2
ARG VCS_REF=unknown
LABEL org.opencontainers.image.revision="${VCS_REF}"
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist/ /usr/share/nginx/html/
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -T 3 -O /dev/null http://127.0.0.1:3000/health || exit 1
CMD ["nginx", "-g", "daemon off;"]
