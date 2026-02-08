# Cycast - Icecast-Compatible Streaming Server

A high-performance internet radio streaming server written in Python with Cython optimizations. Accepts live sources from Mixxx, VLC, or any Icecast-compatible source client and falls back to predefined playlists when no DJ is connected.

**Modern Architecture:**
- 🚀 **Cython optimizations** for 3-5x performance improvement
- 🎨 **Flask web application** running on **Tornado** for production-grade performance
- 📝 **HCL configuration** for human-friendly configuration files
- 🎵 **Beautiful web UI** with real-time updates
- 📊 **RESTful API** for status and statistics

## Features

- **Live Source Support**: Accept streams from Mixxx, VLC, BUTT, or any Icecast/Shoutcast source client
- **Playlist Fallback**: Automatically plays from a playlist when no live source is connected
- **High Performance**: Cython-optimized audio buffer and broadcaster for efficient streaming
- **Multiple Listeners**: Handle many simultaneous listeners efficiently with Tornado
- **Web Status Page**: Beautiful, responsive UI with real-time updates via AJAX
- **RESTful API**: JSON endpoints for status and statistics
- **HCL Configuration**: Easy-to-read and maintain configuration files
- **Seamless Switching**: Automatically switches between live source and playlist

## Architecture

The server uses multiple technologies for optimal performance:

**Backend:**
1. **audio_buffer.pyx**: High-performance circular buffer with zero-copy operations (Cython)
2. **stream_broadcaster.pyx**: Efficient multi-listener broadcaster with dynamic buffering (Cython)
3. **cycast_server.py**: Main server logic, source handling, and coordination (Python)

**Web Layer:**
4. **flask_app.py**: Flask application for UI and API endpoints
5. **Tornado**: WSGI server for production-grade performance and concurrency

**Configuration:**
6. **config.hcl**: Human-friendly HCL configuration file
7. **config_loader.py**: Configuration parser and validator

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- Cython (for compiling performance modules)
- pyhcl (for HCL configuration parsing)
- Flask (web framework)
- Tornado (high-performance web server)

### 2. Build Cython Extensions

```bash
python setup.py build_ext --inplace
```

This will compile the Cython modules into native extensions (.so files on Linux/Mac, .pyd on Windows).

### 3. Configure Your Server

Edit `config.hcl` to customize your settings:

```hcl
server {
  host = "0.0.0.0"
  source_port = 8000
  listen_port = 8001
  source_password = "your-secure-password"
  mount_point = "/stream"
}

metadata {
  station_name = "Your Station Name"
  station_genre = "Your Genre"
}

playlist {
  directory = "./music"
  shuffle = true
}
```

### 4. Prepare Your Music

Create a `music` directory and add some MP3 or OGG files:

```bash
mkdir music
# Copy your music files to the music directory
```

## Usage

### Start the Server

```bash
python cycast_server.py
```

Or with a custom configuration file:

```bash
python cycast_server.py -c /path/to/myconfig.hcl
```

The server will display:
```
============================================================
Starting Cycast Server
============================================================
Configuration loaded from: config.hcl
Source port: 8000 (password: ******)
Listen port: 8001
Mount point: /stream
Station: Your Station Name
Buffer size: 10 MB
============================================================
Playlist loaded: 42 tracks
============================================================
Server ready!
Connect your source to: http://0.0.0.0:8000/stream
Listen at: http://0.0.0.0:8001/stream
Status page: http://0.0.0.0:8001/
Statistics: http://0.0.0.0:8001/api/stats
============================================================
```

### Configure Your Source (Mixxx Example)

In Mixxx:
1. Go to **Preferences → Live Broadcasting**
2. Click **Create new connection**
3. Select **Icecast 2**
4. Set:
   - Host: `localhost`
   - Port: `8000`
   - Mount: `stream`
   - Password: `hackme`
   - Format: MP3 or OGG
5. Click **Enable Live Broadcasting**

### Configure Your Source (VLC Example)

In VLC:
1. Go to **Media → Stream**
2. Add your audio source
3. Click **Stream**
4. Choose destination: **IceCast**
5. Set:
   - Address: `localhost:8000`
   - Mount point: `stream`
   - Login: `source`
   - Password: `hackme`

### Listen to the Stream

**Stream URL** - Open in your media player or browser:
```
http://localhost:8001/stream
```

**Status Page** - Beautiful web interface with real-time updates:
```
http://localhost:8001/
```

**API Endpoints:**
```
http://localhost:8001/api/status  # Current status (JSON)
http://localhost:8001/api/stats   # Detailed statistics (JSON)
```

## Customization

All configuration is done via the `config.hcl` file using HCL (HashiCorp Configuration Language):

```hcl
server {
  host = "0.0.0.0"              # Bind address
  source_port = 8000            # Port for DJ connections
  listen_port = 8001            # Port for listeners
  source_password = "secure123" # CHANGE THIS!
  mount_point = "/stream"
}

buffer {
  size_mb = 10  # Circular buffer size in MB
}

playlist {
  directory = "./music"
  shuffle = true
  extensions = [".mp3", ".ogg"]
}

broadcaster {
  chunk_size = 8192       # Bytes per chunk
  sleep_high = 0.001      # Sleep time when buffer >80% full
  sleep_medium = 0.005    # Sleep time when buffer 50-80% full
  sleep_low = 0.010       # Sleep time when buffer <50% full
}

metadata {
  station_name = "Cycast Radio"
  station_description = "High-performance internet radio"
  station_genre = "Various"
  station_url = "http://localhost:8001"
  enable_icy = true
  icy_metaint = 16000
}

advanced {
  max_listeners = 0           # 0 = unlimited
  source_timeout = 10.0       # Seconds
  verbose_logging = false
  enable_stats = true
  flask_debug = false         # Enable for development only!
  flask_secret_key = "change-me-in-production"
}
```

### Why HCL?

HCL provides:
- Human-friendly syntax with comments
- Clear hierarchical structure
- Type safety
- Better than JSON or YAML for configuration

## Performance Tuning

The combination of Cython + Flask + Tornado provides excellent performance:

**Cython Optimizations:**
1. **Buffer Management**: The circular audio buffer uses native C memory operations (memcpy) for zero-copy data handling
2. **Broadcasting**: The broadcaster is optimized to send data to multiple listeners with minimal overhead
3. **Dynamic Buffering**: Automatically adjusts sleep times based on buffer fill level

**Flask on Tornado Benefits:**
1. **Non-blocking I/O**: Tornado handles concurrent connections efficiently
2. **Low latency**: Better than traditional WSGI servers for streaming
3. **Scalability**: Handles hundreds of concurrent listeners
4. **Production-ready**: Battle-tested in high-traffic applications

**Tuning Tips:**
```hcl
buffer {
  size_mb = 20  # Increase for more buffering (uses more RAM)
}

broadcaster {
  chunk_size = 16384  # Larger chunks = less overhead, higher latency
}

advanced {
  max_listeners = 500  # Set a limit to protect your server
}
```

For maximum performance on production systems:
- Run on multi-core systems for better concurrent handling
- Use an SSD for playlist files
- Put behind nginx reverse proxy with caching
- Monitor with the `/api/stats` endpoint

## How It Works

1. **Source Connection**: When Mixxx/VLC connects, it sends audio data to port 8000
2. **Buffer**: Audio is written to a high-performance circular buffer (Cython)
3. **Broadcast**: A separate thread reads from the buffer and sends to all listeners (Cython)
4. **Fallback**: When no source is connected, the playlist feeder writes to the same buffer
5. **Listeners**: HTTP server on port 8001 serves the stream to multiple clients

## Limitations

This is a simplified streaming server suitable for:
- Small to medium internet radio stations
- Personal/hobby broadcasts
- LAN streaming
- Testing and development

For production use with hundreds of simultaneous listeners, consider:
- Full Icecast2 server
- Load balancing
- CDN integration

## Architecture Diagram

```
┌─────────────┐         ┌──────────────────┐
│   Mixxx/    │────────▶│   Source Port    │
│     VLC     │  8000   │    (8000)        │
└─────────────┘         └────────┬─────────┘
                                 │
                                 ▼
                        ┌────────────────┐
                        │ Circular Buffer│ (Cython)
                        │  (10 MB RAM)   │
                        └────────┬───────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
         ┌─────────┐       ┌─────────┐       ┌─────────┐
         │Listener │       │Listener │       │Listener │
         │    1    │       │    2    │       │    N    │
         └─────────┘       └─────────┘       └─────────┘
              ▲                  ▲                  ▲
              │                  │                  │
              └──────────────────┴──────────────────┘
                       Flask on Tornado (8001)
                     ┌─────────────────────────┐
                     │ • Web UI (HTML/CSS/JS)  │
                     │ • /api/status (JSON)    │
                     │ • /api/stats (JSON)     │
                     │ • /stream (audio)       │
                     └─────────────────────────┘

         ┌──────────────────┐
         │ Playlist Feeder  │ (Fallback when no source)
         │  (music/*.mp3)   │
         └────────┬─────────┘
                  │
                  └──────────────▶ Circular Buffer
```

## Troubleshooting

**Cython build fails:**
- Make sure you have a C compiler installed (gcc on Linux, Xcode on Mac, MSVC on Windows)
- Try: `pip install --upgrade cython setuptools`

**Audio stutters/buffers:**
- Increase buffer size: `audio_buffer.CircularAudioBuffer(size_mb=20)`
- Check network latency
- Reduce number of simultaneous listeners for testing

**Can't connect source:**
- Check firewall settings
- Verify port 8000 is not in use: `netstat -an | grep 8000`
- Try changing the password

**Playlist not working:**
- Ensure MP3/OGG files are in the `./music` directory
- Check file permissions
- Look for errors in console output

## License

MIT License - feel free to modify and use for your projects!

## Contributing

This is a demonstration project showing how to use Cython for performance-critical audio streaming. Feel free to extend it with:
- Better metadata handling
- Recording functionality
- Multiple mount points
- Admin interface
- Statistics/analytics
- Relay functionality
