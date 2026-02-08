# Cycast Docker Deployment Guide

## Quick Start

### Using Docker Compose (Recommended)

```bash
# 1. Create music directory
mkdir music
# Add your MP3/OGG files to ./music/

# 2. Start the server
docker-compose up -d

# 3. View logs
docker-compose logs -f

# 4. Access
# Status: http://localhost:8001
# Stream: http://localhost:8001/stream
# DJ Source: http://localhost:8000/stream (password: hackme)
```

### Using Docker CLI

```bash
# Build the image
docker build -t cycast:latest .

# Run the container
docker run -d \
  --name cycast \
  -p 8000:8000 \
  -p 8001:8001 \
  -v $(pwd)/music:/app/music:ro \
  cycast:latest

# View logs
docker logs -f cycast
```

## Image Details

**Multi-stage build:**
- Build stage: Compiles Cython extensions with gcc
- Runtime stage: Minimal Python 3.11 slim image
- Final size: ~200-250 MB (vs ~1GB with build tools)

**Security:**
- Runs as non-root user (`cycast:cycast`, UID 1000)
- No unnecessary packages in runtime image
- Read-only music volume mount

**Features:**
- Health check included
- Automatic restart (docker-compose)
- Optimized layer caching

## Volume Mounts

### Music Directory (Required for Playlist)

```bash
# Mount local music directory
-v ./music:/app/music:ro
```

The `:ro` makes it read-only for security.

### Custom Configuration

```bash
# Mount custom config
-v ./my-config.hcl:/app/config.hcl:ro

docker run -d \
  --name cycast \
  -p 8000:8000 \
  -p 8001:8001 \
  -v $(pwd)/music:/app/music:ro \
  -v $(pwd)/config.hcl:/app/config.hcl:ro \
  cycast:latest
```

### Logs

```bash
# Persist logs outside container
-v ./logs:/var/log/cycast

docker run -d \
  --name cycast \
  -p 8000:8000 \
  -p 8001:8001 \
  -v $(pwd)/music:/app/music:ro \
  -v $(pwd)/logs:/var/log/cycast \
  cycast:latest
```

## Environment Variables

### Log Level

```bash
# Set log level
-e CYCAST_LOG_LEVEL=DEBUG

docker run -d \
  --name cycast \
  -e CYCAST_LOG_LEVEL=WARNING \
  -p 8000:8000 \
  -p 8001:8001 \
  cycast:latest
```

Levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`

## Port Mapping

Default ports:
- `8000` - Source port (where DJs connect)
- `8001` - Listener port (HTTP streaming + web UI)

### Custom Ports

```bash
# Map to different host ports
-p 9000:8000 \  # DJ connects to localhost:9000
-p 9001:8001    # Listeners use localhost:9001
```

## Docker Compose Configuration

### Basic Setup

```yaml
version: '3.8'

services:
  cycast:
    build: .
    ports:
      - "8000:8000"
      - "8001:8001"
    volumes:
      - ./music:/app/music:ro
    restart: unless-stopped
```

### Production Setup

```yaml
version: '3.8'

services:
  cycast:
    build: .
    image: cycast:latest
    container_name: cycast-server
    restart: unless-stopped
    
    ports:
      - "8000:8000"
      - "8001:8001"
    
    volumes:
      - ./music:/app/music:ro
      - ./config.hcl:/app/config.hcl:ro
      - ./logs:/var/log/cycast
    
    environment:
      - CYCAST_LOG_LEVEL=INFO
    
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 256M
    
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/status')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### With Nginx Reverse Proxy

```yaml
version: '3.8'

services:
  cycast:
    build: .
    restart: unless-stopped
    volumes:
      - ./music:/app/music:ro
    networks:
      - cycast-net
  
  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    networks:
      - cycast-net
    depends_on:
      - cycast

networks:
  cycast-net:
    driver: bridge
```

## Building Custom Images

### Build with Custom Tag

```bash
docker build -t myorg/cycast:v1.0 .
```

### Build for Different Architectures

```bash
# For ARM (Raspberry Pi)
docker buildx build --platform linux/arm64 -t cycast:arm64 .

# For AMD64 (most servers)
docker buildx build --platform linux/amd64 -t cycast:amd64 .

# Multi-platform
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t myorg/cycast:latest \
  --push .
```

## Container Management

### View Logs

```bash
# All logs
docker logs cycast

# Follow logs (tail -f style)
docker logs -f cycast

# Last 100 lines
docker logs --tail 100 cycast

# With timestamps
docker logs -t cycast
```

### Container Shell

```bash
# Get a shell inside the container
docker exec -it cycast /bin/bash

# Run a command
docker exec cycast python -c "import audio_buffer; print('OK')"
```

### Resource Monitoring

```bash
# Real-time stats
docker stats cycast

# One-time stats
docker stats --no-stream cycast
```

### Restart/Stop

```bash
# Restart
docker restart cycast

# Stop
docker stop cycast

# Start
docker start cycast

# Remove (will delete container, not image)
docker rm -f cycast
```

## Health Check

The image includes a built-in health check that pings `/api/status` every 30 seconds.

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' cycast

# View health check logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' cycast
```

Status values:
- `starting` - Container just started
- `healthy` - Health check passing
- `unhealthy` - Health check failing

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs cycast

# Check if ports are already in use
netstat -tuln | grep -E ':(8000|8001)'

# Try running interactively
docker run -it --rm -p 8000:8000 -p 8001:8001 cycast:latest
```

### Permission Issues

```bash
# Ensure music directory is readable
chmod -R a+r music/

# Check volume mount
docker exec cycast ls -la /app/music
```

### Cython Extensions Not Working

```bash
# Verify extensions were built
docker exec cycast ls -la /app/*.so

# Should see:
# audio_buffer.cpython-311-x86_64-linux-gnu.so
# stream_broadcaster.cpython-311-x86_64-linux-gnu.so

# Rebuild image from scratch
docker build --no-cache -t cycast:latest .
```

### High Memory Usage

```bash
# Check buffer size in config
docker exec cycast cat config.hcl | grep size_mb

# Limit container memory
docker update --memory 512M cycast
```

## Production Deployment

### 1. Use docker-compose

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

### 2. Behind Nginx

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream cycast {
        server cycast:8001;
    }

    server {
        listen 80;
        server_name radio.example.com;

        location / {
            proxy_pass http://cycast;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /stream {
            proxy_pass http://cycast;
            proxy_buffering off;
            proxy_set_header Host $host;
        }
    }
}
```

### 3. With SSL (Let's Encrypt)

```bash
# Use certbot to get SSL cert
docker run -it --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  certbot/certbot certonly \
  --standalone \
  -d radio.example.com

# Update nginx config to use SSL
# Mount certs in docker-compose.yml
```

### 4. Auto-restart with systemd

Create `/etc/systemd/system/cycast.service`:

```ini
[Unit]
Description=Cycast Radio Server
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/cycast
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable cycast
sudo systemctl start cycast
```

## Image Registry

### Push to Docker Hub

```bash
# Tag
docker tag cycast:latest username/cycast:latest

# Login
docker login

# Push
docker push username/cycast:latest
```

### Private Registry

```bash
# Tag for private registry
docker tag cycast:latest registry.example.com/cycast:latest

# Push
docker push registry.example.com/cycast:latest
```

## Best Practices

1. **Use docker-compose** for easier management
2. **Mount music as read-only** (`:ro`)
3. **Set resource limits** to prevent runaway memory
4. **Use health checks** for monitoring
5. **Run as non-root** (already configured)
6. **Keep logs outside container** with volume mount
7. **Use specific image tags** not `:latest` in production
8. **Back up your config.hcl**
9. **Monitor with** `docker stats`
10. **Update regularly** `docker pull` and `docker-compose up -d`

## Quick Reference

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# Logs
docker-compose logs -f

# Update
docker-compose pull
docker-compose up -d

# Shell
docker-compose exec cycast /bin/bash

# Stats
docker stats $(docker-compose ps -q)
```

Enjoy your containerized Cycast server! 🐳🎵
