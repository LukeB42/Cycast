# Cycast Server Configuration
# HCL format for easy human editing

server {
  # Host to bind to (0.0.0.0 for all interfaces, 127.0.0.1 for localhost only)
  host = "0.0.0.0"
  
  # Port where sources (Mixxx, VLC) connect
  source_port = 8000
  
  # Port where listeners connect via HTTP
  listen_port = 8001
  
  # Password for source authentication
  # CHANGE THIS IN PRODUCTION!
  source_password = "hackme"
  
  # Mount point for the stream
  mount_point = "/stream"
}

buffer {
  # Size of circular audio buffer in megabytes
  # Larger = more buffering, less skipping, more memory usage
  # 20 MB = ~2 minutes of 128kbps MP3 (increased from 10 MB)
  size_mb = 20
}

playlist {
  # Directory containing music files for fallback playlist
  directory = "./music"
  
  # Shuffle playlist on load
  shuffle = true
  
  # Supported file extensions
  extensions = [".mp3", ".ogg"]
}

broadcaster {
  # Chunk size for reading/sending data (bytes)
  # Larger = more efficient, less overhead, smoother playback
  # 16384 = 16 KB chunks (increased from 8192)
  chunk_size = 16384
  
  # Sleep times for different buffer fill levels (seconds)
  # Reduced sleep times for more responsive broadcasting
  sleep_high   = 0.0005  # When buffer >80% full (was 0.001)
  sleep_medium = 0.001   # When buffer 50-80% full (was 0.005)
  sleep_low    = 0.002   # When buffer <50% full (was 0.010)
}

metadata {
  # Station information
  station_name        = "Cycast Radio"
  station_description = "High-performance internet radio"
  station_genre       = "Various"
  station_url         = "http://localhost:8001"
  
  # Enable ICY metadata
  enable_icy = true
  
  # Metadata interval (in bytes)
  icy_metaint = 16000
}

advanced {
  # Maximum number of simultaneous listeners (0 = unlimited)
  max_listeners = 0
  
  # Connection timeout for source (seconds)
  source_timeout = 10.0
  
  # Enable detailed logging
  verbose_logging = false
  
  # Enable statistics endpoint
  enable_stats = true
  
  # Enable Flask debug mode (development only!)
  flask_debug = false
  
  # Flask secret key for sessions
  # CHANGE THIS IN PRODUCTION!
  flask_secret_key = "change-me-in-production"
}

# You can define multiple mount points (future feature)
# mount "/alternative" {
#   source_password = "different-password"
#   playlist_directory = "./alternative-music"
# }
