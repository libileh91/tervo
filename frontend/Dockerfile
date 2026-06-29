# ResQ — Frontend Dockerfile (Nginx static serving).
#
# Serves the pre-built `dist/` folder via Nginx.
# The API reverse proxy is handled by 1Panel, not Nginx.
#
# Usage:
#   docker build -t resq-frontend:latest -f frontend/Dockerfile frontend/
#   docker run -p 80:80 resq-frontend:latest

FROM nginx:alpine

# Copy the pre-built static files
COPY dist/ /usr/share/nginx/html

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Minimal nginx config — just serves static files, no proxy
RUN echo 'server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
