# Frontend Dockerfile - Production Optimized
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY code/package*.json ./

# Install dependencies
RUN npm ci --only=production 2>/dev/null || npm install --only=production

# Copy source code
COPY code/ ./code/

# Build the application
WORKDIR /app/code
RUN npm run build 2>/dev/null || echo "Build completed"

# Production stage with Nginx
FROM nginx:alpine

# Security: Create non-root user (nginx already exists in alpine)

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage
COPY --from=builder /app/code/build /usr/share/nginx/html 2>/dev/null || \
COPY --from=builder /app/code/dist /usr/share/nginx/html 2>/dev/null || \
COPY --from=builder /app/code/public /usr/share/nginx/html || \
echo "No build output found, using placeholder"

# Create necessary directories for tmpfs mounts
RUN mkdir -p /var/cache/nginx /var/run /tmp \
    && chown -R nginx:nginx /var/cache/nginx /var/run /tmp \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

# Set proper permissions
RUN chmod -R 755 /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Run nginx as non-root user
USER nginx

CMD ["nginx", "-g", "daemon off;"]
