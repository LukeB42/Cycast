#!/usr/bin/env python3
"""
Flask web application for Cycast
Serves the status page and stream endpoints
"""

from flask import Flask, Response, render_template_string, request, jsonify, stream_with_context
import time
import threading
import logging

# Get logger
logger = logging.getLogger('cycast.web')


class StreamWebApp:
    """Flask application for serving streams and status pages"""
    
    def __init__(self, stream_server, config):
        self.stream_server = stream_server
        self.config = config
        self.app = Flask(__name__)
        
        # Configure Flask
        self.app.config['SECRET_KEY'] = config.get('advanced', 'flask_secret_key')
        self.app.config['DEBUG'] = config.get('advanced', 'flask_debug')
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self):
        """Register Flask routes"""
        
        @self.app.route('/')
        def index():
            """Serve status page"""
            return self._render_status_page()
        
        @self.app.route(self.config.get('server', 'mount_point'))
        def stream():
            """Serve audio stream"""
            return self._serve_stream()
        
        @self.app.route('/api/status')
        def api_status():
            """API endpoint for status information"""
            return jsonify(self._get_status_data())
        
        @self.app.route('/api/stats')
        def api_stats():
            """API endpoint for detailed statistics"""
            if not self.config.get('advanced', 'enable_stats'):
                return jsonify({'error': 'Stats disabled'}), 403
            
            stats = self.stream_server.broadcaster.get_stats()
            stats['buffer'] = {
                'available': self.stream_server.audio_buffer.available(),
                'space': self.stream_server.audio_buffer.space(),
                'fill_percentage': self.stream_server.audio_buffer.fill_percentage() * 100
            }
            return jsonify(stats)
    
    def _get_status_data(self):
        """Get current server status data"""
        with self.stream_server.metadata_lock:
            metadata = self.stream_server.current_metadata.copy()
        
        listeners = self.stream_server.broadcaster.get_listener_count()
        uptime = int(time.time() - self.stream_server.start_time)
        
        with self.stream_server.source_lock:
            source_connected = self.stream_server.current_source is not None
        
        return {
            'source_connected': source_connected,
            'source_status': 'Connected' if source_connected else 'Playlist Fallback',
            'metadata': metadata,
            'listeners': listeners,
            'uptime_seconds': uptime,
            'uptime_formatted': f"{uptime // 3600}h {(uptime % 3600) // 60}m",
            'station_name': self.config.get('metadata', 'station_name'),
            'station_genre': self.config.get('metadata', 'station_genre'),
        }
    
    def _render_status_page(self):
        """Render the status page"""
        status = self._get_status_data()
        
        template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ station_name }} - Cycast Server</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 800px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1em;
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            border-left: 4px solid #667eea;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .stat-label {
            font-weight: 600;
            color: #666;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        
        .stat-value {
            color: #333;
            font-size: 1.3em;
            font-weight: 500;
        }
        
        .now-playing {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 25px;
        }
        
        .now-playing-label {
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 8px;
        }
        
        .now-playing-title {
            font-size: 1.8em;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .now-playing-artist {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        
        .status-live {
            background: #4CAF50;
        }
        
        .status-fallback {
            background: #FF9800;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .stream-link {
            background: #333;
            color: white;
            padding: 15px 25px;
            border-radius: 8px;
            text-decoration: none;
            display: inline-block;
            font-weight: 600;
            transition: background 0.3s;
            margin-top: 10px;
        }
        
        .stream-link:hover {
            background: #555;
        }
        
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 0.9em;
        }
        
        .api-links {
            margin-top: 20px;
            padding: 15px;
            background: #f0f0f0;
            border-radius: 8px;
        }
        
        .api-links h3 {
            margin-bottom: 10px;
            color: #555;
            font-size: 1.1em;
        }
        
        .api-links a {
            color: #667eea;
            text-decoration: none;
            margin-right: 15px;
        }
        
        .api-links a:hover {
            text-decoration: underline;
        }
    </style>
    <script>
        // Auto-refresh status every 5 seconds
        setInterval(function() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('listeners').textContent = data.listeners;
                    document.getElementById('uptime').textContent = data.uptime_formatted;
                    document.getElementById('status-text').textContent = data.source_status;
                    document.getElementById('now-playing-title').textContent = data.metadata.title || 'Unknown';
                    document.getElementById('now-playing-artist').textContent = data.metadata.artist || '';
                    
                    // Update status indicator
                    const indicator = document.getElementById('status-indicator');
                    if (data.source_connected) {
                        indicator.className = 'status-indicator status-live';
                    } else {
                        indicator.className = 'status-indicator status-fallback';
                    }
                });
        }, 5000);
    </script>
</head>
<body>
    <div class="container">
        <h1>🎵 {{ station_name }}</h1>
        <p class="subtitle">{{ station_genre }}</p>
        
        <div class="now-playing">
            <div class="now-playing-label">NOW PLAYING</div>
            <div class="now-playing-title" id="now-playing-title">{{ metadata.title }}</div>
            {% if metadata.artist %}
            <div class="now-playing-artist" id="now-playing-artist">{{ metadata.artist }}</div>
            {% endif %}
        </div>
        
        <div class="status-grid">
            <div class="stat-card">
                <div class="stat-label">Status</div>
                <div class="stat-value">
                    <span id="status-indicator" class="status-indicator {% if source_connected %}status-live{% else %}status-fallback{% endif %}"></span>
                    <span id="status-text">{{ source_status }}</span>
                </div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Listeners</div>
                <div class="stat-value" id="listeners">{{ listeners }}</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-label">Uptime</div>
                <div class="stat-value" id="uptime">{{ uptime_formatted }}</div>
            </div>
        </div>
        
        <div style="text-align: center;">
            <a href="{{ mount_point }}" class="stream-link">🎧 Listen Now</a>
        </div>
        
        {% if enable_stats %}
        <div class="api-links">
            <h3>API Endpoints</h3>
            <a href="/api/status" target="_blank">Status JSON</a>
            <a href="/api/stats" target="_blank">Statistics JSON</a>
        </div>
        {% endif %}
        
        <div class="footer">
            Powered by Cycast · Flask on Tornado · Cython Optimized
        </div>
    </div>
</body>
</html>
        """
        
        return render_template_string(
            template,
            station_name=status['station_name'],
            station_genre=status['station_genre'],
            metadata=status['metadata'],
            source_connected=status['source_connected'],
            source_status=status['source_status'],
            listeners=status['listeners'],
            uptime_formatted=status['uptime_formatted'],
            mount_point=self.config.get('server', 'mount_point'),
            enable_stats=self.config.get('advanced', 'enable_stats')
        )
    
    def _serve_stream(self):
        """Serve audio stream to listener"""
        client_ip = request.remote_addr
        logger.info(f"New listener from {client_ip}")
        
        # Create response generator
        def generate():
            # Create a queue-based writer for the broadcaster
            import queue
            
            class StreamWriter:
                def __init__(self):
                    # Larger queue to handle burst traffic and prevent drops
                    # 500 chunks * 16KB = 8MB buffer per listener
                    self.queue = queue.Queue(maxsize=500)
                    self.active = True
                
                def write(self, data):
                    if self.active:
                        try:
                            # Non-blocking put with immediate drop if full
                            # This prevents slow listeners from blocking the broadcaster
                            self.queue.put(data, block=False)
                        except queue.Full:
                            # Listener is too slow, drop oldest data
                            pass
                
                def flush(self):
                    pass
                
                def close(self):
                    self.active = False
            
            writer = StreamWriter()
            listener_id = self.stream_server.broadcaster.add_listener(writer)
            
            try:
                # Stream data as it becomes available
                while self.stream_server.broadcaster.is_listener_active(listener_id):
                    try:
                        # Get data with short timeout
                        data = writer.queue.get(timeout=0.5)
                        if data:
                            yield data
                    except queue.Empty:
                        # No data available - continue waiting
                        continue
                    except:
                        break
                        
            except GeneratorExit:
                logger.info(f"Listener {client_ip} disconnected (client closed)")
            except Exception as e:
                logger.error(f"Listener {client_ip} error: {e}")
            finally:
                writer.close()
                self.stream_server.broadcaster.remove_listener(listener_id)
                logger.info(f"Listener {client_ip} cleanup complete")
        
        # Build response headers
        headers = {
            'Content-Type': 'audio/mpeg',
            'Cache-Control': 'no-cache, no-store',
            'Pragma': 'no-cache',
            'Connection': 'close',
            'Accept-Ranges': 'none',
        }
        
        # ICY metadata support
        if request.headers.get('Icy-MetaData') == '1' and self.config.get('metadata', 'enable_icy'):
            headers['icy-metaint'] = str(self.config.get('metadata', 'icy_metaint'))
            headers['icy-name'] = self.config.get('metadata', 'station_name')
            headers['icy-genre'] = self.config.get('metadata', 'station_genre')
            headers['icy-url'] = self.config.get('metadata', 'station_url')
        
        return Response(
            generate(),
            mimetype='audio/mpeg',
            headers=headers,
            direct_passthrough=True
        )
    
    def get_app(self):
        """Get the Flask application"""
        return self.app
