#!/usr/bin/env python3
"""
Cycast - A simple Icecast-compatible streaming server in Python/Cython
Accepts sources from Mixxx, VLC, etc. and falls back to playlists
Web interface powered by Flask on Tornado
"""

import socket
import threading
import time
import base64
import os
import random
import sys
import logging

# Import Cython modules for performance
import audio_buffer
import stream_broadcaster

# Import configuration loader
from config_loader import load_config

# Import Flask/Tornado integration
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer as TornadoHTTPServer
from tornado.ioloop import IOLoop
from flask_app import StreamWebApp

# Configure logging to stdout only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('cycast')


class StreamServer:
    def __init__(self, config):
        """Initialize stream server with HCL configuration"""
        self.config = config
        
        # Extract configuration
        self.host = config.get('server', 'host')
        self.source_port = config.get('server', 'source_port')
        self.listen_port = config.get('server', 'listen_port')
        self.source_password = config.get('server', 'source_password')
        self.mount_point = config.get('server', 'mount_point')
        
        # Stream state
        self.current_source = None
        self.source_lock = threading.Lock()
        
        # Use Cython-optimized audio buffer
        buffer_size = config.get('buffer', 'size_mb')
        self.audio_buffer = audio_buffer.CircularAudioBuffer(size_mb=buffer_size)
        
        # Use Cython-optimized broadcaster with configured chunk size
        chunk_size = config.get('broadcaster', 'chunk_size')
        self.broadcaster = stream_broadcaster.StreamBroadcaster(self.audio_buffer, chunk_size=chunk_size)
        
        # Playlist fallback
        self.playlist_files = []
        self.playlist_active = False
        self.current_metadata = {"title": config.get('metadata', 'station_name'), "artist": ""}
        self.metadata_lock = threading.Lock()
        
        # Statistics
        self.bytes_sent = 0
        self.start_time = time.time()
        
    def load_playlist(self, directory=None):
        """Load MP3 files from directory for fallback playlist"""
        if directory is None:
            directory = self.config.get('playlist', 'directory')
        
        if not os.path.exists(directory):
            logger.info(f"Playlist directory {directory} not found")
            return
        
        extensions = tuple(self.config.get('playlist', 'extensions'))
        
        for file in os.listdir(directory):
            if file.lower().endswith(extensions):
                self.playlist_files.append(os.path.join(directory, file))
        
        if self.playlist_files:
            logger.info(f"Loaded {len(self.playlist_files)} files into playlist")
            if self.config.get('playlist', 'shuffle'):
                random.shuffle(self.playlist_files)
        else:
            logger.info("No audio files found in playlist directory")
    
    def parse_icy_metadata(self, data):
        """Parse Icecast metadata from stream"""
        try:
            if b"StreamTitle='" in data:
                start = data.find(b"StreamTitle='") + 13
                end = data.find(b"';", start)
                if end > start:
                    title = data[start:end].decode('utf-8', errors='ignore')
                    with self.metadata_lock:
                        if ' - ' in title:
                            artist, track = title.split(' - ', 1)
                            self.current_metadata = {"title": track, "artist": artist}
                        else:
                            self.current_metadata = {"title": title, "artist": ""}
        except Exception as e:
            logger.error(f"Error parsing metadata: {e}")
    
    def playlist_feeder(self):
        """Feed audio from playlist files when no source is connected"""
        current_file_index = 0
        
        while True:
            with self.source_lock:
                should_play = self.current_source is None
            
            if should_play and self.playlist_files:
                if not self.playlist_active:
                    logger.info("No source connected, starting playlist fallback")
                    self.playlist_active = True
                
                try:
                    file_path = self.playlist_files[current_file_index]
                    filename = os.path.basename(file_path)
                    
                    with self.metadata_lock:
                        self.current_metadata = {
                            "title": filename,
                            "artist": "Playlist"
                        }
                    
                    logger.info(f"Playing from playlist: {filename}")
                    
                    with open(file_path, 'rb') as f:
                        # Skip ID3v2 tags if present
                        header = f.read(10)
                        if header[:3] == b'ID3':
                            size = ((header[6] & 0x7f) << 21) | ((header[7] & 0x7f) << 14) | \
                                   ((header[8] & 0x7f) << 7) | (header[9] & 0x7f)
                            f.seek(size + 10)
                        else:
                            f.seek(0)
                        
                        # Stream the file in chunks
                        chunk_size = 8192
                        bytes_written = 0
                        
                        while True:
                            with self.source_lock:
                                if self.current_source is not None:
                                    logger.info("Live source connected, stopping playlist")
                                    self.playlist_active = False
                                    break
                            
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            
                            # Write to Cython buffer with minimal blocking
                            while not self.audio_buffer.write(chunk):
                                time.sleep(0.0001)  # 0.1ms micro-sleep
                            
                            bytes_written += len(chunk)
                        
                        logger.info(f"Finished playing {filename} ({bytes_written} bytes)")
                    
                    current_file_index = (current_file_index + 1) % len(self.playlist_files)
                    
                except Exception as e:
                    logger.error(f"Error playing file: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(1)
            else:
                self.playlist_active = False
                time.sleep(0.1)  # Short sleep when idle
    
    def handle_source_connection(self, conn, addr):
        """Handle incoming source connection (Mixxx, VLC, etc.)"""
        logger.info(f"Source connection from {addr}")
        
        try:
            # Read HTTP request
            request = b''
            conn.settimeout(5.0)
            while b'\r\n\r\n' not in request and len(request) < 8192:
                try:
                    chunk = conn.recv(1024)
                    if not chunk:
                        return
                    request += chunk
                except socket.timeout:
                    return
            
            request_str = request.decode('utf-8', errors='ignore')
            lines = request_str.split('\r\n')
            
            # Parse request line
            if not lines[0].startswith(('SOURCE', 'PUT')):
                logger.warning(f"Not a valid source request: {lines[0]}")
                conn.sendall(b'HTTP/1.1 405 Method Not Allowed\r\n\r\n')
                return
            
            # Check authentication
            authenticated = False
            content_type = 'audio/mpeg'
            
            for line in lines:
                if line.startswith('Authorization: Basic '):
                    try:
                        auth_data = base64.b64decode(line.split(' ')[2]).decode('utf-8')
                        if ':' in auth_data:
                            username, password = auth_data.split(':', 1)
                            if password == self.source_password:
                                authenticated = True
                    except Exception as e:
                        logger.error(f"Auth decode error: {e}")
                elif line.startswith('Content-Type:'):
                    content_type = line.split(':', 1)[1].strip()
            
            if not authenticated:
                logger.warning("Authentication failed")
                conn.sendall(b'HTTP/1.1 401 Unauthorized\r\nWWW-Authenticate: Basic realm="Cycast"\r\n\r\n')
                return
            
            # Accept the source
            logger.info(f"Source authenticated, accepting connection (Content-Type: {content_type})")
            conn.sendall(b'HTTP/1.1 200 OK\r\n\r\n')
            
            # Set as current source
            with self.source_lock:
                if self.current_source is not None:
                    logger.info("Disconnecting previous source")
                    try:
                        self.current_source.close()
                    except:
                        pass
                self.current_source = conn
            
            with self.metadata_lock:
                self.current_metadata = {"title": "Live Stream", "artist": ""}
            
            # Read and broadcast audio data
            conn.settimeout(10.0)
            chunk_size = 8192
            
            while True:
                try:
                    chunk = conn.recv(chunk_size)
                    if not chunk:
                        logger.info("Source disconnected")
                        break
                    
                    # Check for Icecast metadata (simplified)
                    if b"StreamTitle=" in chunk:
                        self.parse_icy_metadata(chunk)
                    
                    # Write to Cython buffer
                    while not self.audio_buffer.write(chunk):
                        time.sleep(0.001)
                    
                except socket.timeout:
                    logger.warning("Source connection timeout")
                    break
                except Exception as e:
                    logger.error(f"Error reading from source: {e}")
                    break
            
        except Exception as e:
            logger.error(f"Source connection error: {e}")
        finally:
            with self.source_lock:
                if self.current_source == conn:
                    self.current_source = None
            try:
                conn.close()
            except:
                pass
            logger.info("Source handler exiting")
    
    def source_listener(self):
        """Listen for incoming source connections"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.source_port))
        sock.listen(5)
        print(f"Source server listening on {self.host}:{self.source_port}")
        
        while True:
            try:
                conn, addr = sock.accept()
                thread = threading.Thread(target=self.handle_source_connection, args=(conn, addr))
                thread.daemon = True
                thread.start()
            except Exception as e:
                print(f"Error accepting source connection: {e}")
    
    def start(self):
        """Start the streaming server"""
        logger.info("=" * 60)
        logger.info("Starting Cycast Server")
        logger.info("=" * 60)
        logger.info(f"Configuration loaded from: {self.config.config_file}")
        logger.info(f"Source port: {self.source_port} (password: {self.source_password})")
        logger.info(f"Listen port: {self.listen_port}")
        logger.info(f"Mount point: {self.mount_point}")
        logger.info(f"Station: {self.config.get('metadata', 'station_name')}")
        logger.info(f"Buffer size: {self.config.get('buffer', 'size_mb')} MB")
        logger.info("=" * 60)
        
        # Start source listener thread
        source_thread = threading.Thread(target=self.source_listener, daemon=True)
        source_thread.start()
        
        # Start playlist feeder thread
        if self.playlist_files:
            logger.info(f"Playlist loaded: {len(self.playlist_files)} tracks")
            playlist_thread = threading.Thread(target=self.playlist_feeder, daemon=True)
            playlist_thread.start()
        else:
            logger.info("No playlist configured - will only stream from live sources")
        
        # Start broadcaster thread
        self.broadcaster.start()
        
        # Create Flask application
        web_app = StreamWebApp(self, self.config)
        flask_app = web_app.get_app()
        
        # Wrap Flask in Tornado WSGI container
        from tornado.wsgi import WSGIContainer
        from tornado.httpserver import HTTPServer as TornadoHTTPServer
        from tornado.ioloop import IOLoop
        import tornado.web
        
        # Create WSGI container
        container = WSGIContainer(flask_app)
        
        # Create Tornado application
        tornado_app = tornado.web.Application([
            (r".*", tornado.web.FallbackHandler, dict(fallback=container)),
        ])
        
        # Create HTTP server with settings optimized for streaming
        http_server = TornadoHTTPServer(
            tornado_app,
            # Disable timeouts for streaming connections
            idle_connection_timeout=0,
            body_timeout=0,
            # Increase max buffer size
            max_buffer_size=10485760,  # 10 MB
        )
        
        http_server.listen(self.listen_port, address=self.host)
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("Server ready!")
        logger.info(f"Connect your source to: http://{self.host}:{self.source_port}{self.mount_point}")
        logger.info(f"Listen at: http://{self.host}:{self.listen_port}{self.mount_point}")
        logger.info(f"Status page: http://{self.host}:{self.listen_port}/")
        if self.config.get('advanced', 'enable_stats'):
            logger.info(f"Statistics: http://{self.host}:{self.listen_port}/api/stats")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Press Ctrl+C to stop")
        logger.info("Note: VLC may require Ctrl+C to start playback (see VLC_WORKAROUND.md)")
        logger.info("")
        
        try:
            # Start Tornado IOLoop
            IOLoop.current().start()
        except KeyboardInterrupt:
            logger.info("")
            logger.info("Shutting down...")
            self.broadcaster.stop()
            IOLoop.current().stop()
            logger.info("Server stopped.")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Cycast - Icecast-compatible streaming server')
    parser.add_argument('-c', '--config', default='config.hcl', 
                       help='Path to HCL configuration file (default: config.hcl)')
    args = parser.parse_args()
    
    try:
        # Load configuration from HCL file
        config = load_config(args.config)
        
        # Create and start server
        server = StreamServer(config)
        
        # Load playlist if configured
        server.load_playlist()
        
        # Start server (blocks until Ctrl+C)
        server.start()
        
    except FileNotFoundError:
        logger.error(f"Configuration file '{args.config}' not found")
        logger.info("Creating default config.hcl file...")
        
        # Copy default config
        import shutil
        if os.path.exists('config.hcl.example'):
            shutil.copy('config.hcl.example', 'config.hcl')
            logger.info("Created config.hcl from example. Please edit and restart.")
        else:
            logger.info("Please create a config.hcl file. See config.hcl for an example.")
        sys.exit(1)
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Shutdown complete.")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
