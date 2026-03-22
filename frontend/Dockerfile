FROM node:20-alpine AS builder

WORKDIR /app/code
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:stable-alpine

# Supprime configs par défaut
RUN rm -rf /etc/nginx/conf.d/*

# Copie nginx.conf complet
COPY nginx.conf /etc/nginx/nginx.conf

# Copie assets buildés
COPY --from=builder /app/code/static/frontend /usr/share/nginx/html

# Crée utilisateur non-root
RUN addgroup -S nginxgroup && adduser -S nginxuser -G nginxgroup \
    && chown -R nginxuser:nginxgroup /usr/share/nginx/html /var/cache/nginx /tmp \
    && chmod -R 755 /usr/share/nginx/html /tmp

USER nginxuser
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]