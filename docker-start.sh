#!/bin/bash
# Cycast Docker Quick Start Script

set -e

echo "============================================================"
echo "Cycast Docker Quick Start"
echo "============================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✅ Docker is installed"

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "⚠️  docker-compose is not installed. Using 'docker compose' instead."
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
    echo "✅ docker-compose is installed"
fi

echo ""

# Create music directory if it doesn't exist
if [ ! -d "music" ]; then
    echo "📁 Creating music directory..."
    mkdir -p music
    echo "   ⚠️  Please add MP3/OGG files to ./music/ for playlist fallback"
else
    echo "✅ Music directory exists"
    FILE_COUNT=$(find music -type f \( -name "*.mp3" -o -name "*.ogg" \) | wc -l)
    echo "   Found $FILE_COUNT audio files"
fi

echo ""
echo "============================================================"
echo "Building Docker image..."
echo "============================================================"
echo ""

# Build the image
docker build -t cycast:latest . || {
    echo ""
    echo "❌ Build failed. Please check the error messages above."
    exit 1
}

echo ""
echo "✅ Build successful!"
echo ""
echo "============================================================"
echo "Starting Cycast server..."
echo "============================================================"
echo ""

# Start with docker-compose
$COMPOSE_CMD up -d || {
    echo ""
    echo "❌ Failed to start. Trying to see what went wrong..."
    $COMPOSE_CMD logs
    exit 1
}

echo ""
echo "✅ Server started!"
echo ""

# Wait for server to be ready
echo "⏳ Waiting for server to be ready..."
sleep 3

# Check if server is responding
if curl -s http://localhost:8001/api/status > /dev/null 2>&1; then
    echo "✅ Server is responding!"
else
    echo "⚠️  Server may still be starting up. Check logs with:"
    echo "   $COMPOSE_CMD logs -f"
fi

echo ""
echo "============================================================"
echo "Cycast is ready!"
echo "============================================================"
echo ""
echo "📊 Status page:    http://localhost:8001/"
echo "🎵 Stream URL:     http://localhost:8001/stream"
echo "🎙️  DJ Source URL:  http://localhost:8000/stream"
echo "                   (password: hackme - change in config.hcl!)"
echo ""
echo "Useful commands:"
echo "  View logs:       $COMPOSE_CMD logs -f"
echo "  Stop server:     $COMPOSE_CMD down"
echo "  Restart:         $COMPOSE_CMD restart"
echo "  Shell access:    $COMPOSE_CMD exec cycast /bin/bash"
echo ""
echo "📖 Documentation:  See DOCKER.md for detailed guide"
echo ""
echo "============================================================"
