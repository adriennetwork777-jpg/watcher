FROM node:20-alpine AS builder

WORKDIR /app/code
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:stable-alpine

# Copie nginx.conf complet
COPY nginx.conf /etc/nginx/nginx.conf

# Copie assets buildés
COPY --from=builder /app/code/static/frontend /usr/share/nginx/html

# Crée utilisateur non-root et tous les dossiers temp nécessaires
RUN addgroup -S nginxgroup && adduser -S nginxuser -G nginxgroup \
    && mkdir -p /var/lib/nginx/client_body \
                 /var/lib/nginx/proxy_temp \
                 /var/lib/nginx/fastcgi_temp \
                 /var/lib/nginx/uwsgi_temp \
                 /var/lib/nginx/scgi_temp \
                 /var/cache/nginx/client_temp \
                 /var/run/nginx \
    && chown -R nginxuser:nginxgroup /usr/share/nginx/html /var/lib/nginx /var/cache/nginx /var/run/nginx \
    && chmod -R 755 /usr/share/nginx/html /var/lib/nginx /var/cache/nginx /var/run/nginx

# Passe à l’utilisateur non-root
USER nginxuser

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]