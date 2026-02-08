#!/usr/bin/env python3
"""
Pure Python implementation of stream_broadcaster for testing
This is a fallback when Cython modules aren't compiled
"""

import threading
import time
import logging

logger = logging.getLogger('cycast.broadcaster')


class StreamBroadcaster:
    """Broadcaster that sends audio to multiple listeners - pure Python version"""
    
    def __init__(self, audio_buffer, chunk_size=16384):
        self.audio_buffer = audio_buffer
        self.chunk_size = chunk_size
        self.listeners = {}
        self.listeners_lock = threading.RLock()
        self.next_listener_id = 0
        self.running = False
        self.broadcast_thread = None
    
    def add_listener(self, listener):
        """Add a new listener, returns listener ID"""
        with self.listeners_lock:
            listener_id = self.next_listener_id
            self.next_listener_id += 1
            
            self.listeners[listener_id] = {
                'writer': listener,
                'bytes_sent': 0,
                'connected_at': time.time()
            }
            
            logger.info(f"Listener {listener_id} added")
            return listener_id
    
    def remove_listener(self, listener_id):
        """Remove a listener"""
        with self.listeners_lock:
            if listener_id in self.listeners:
                del self.listeners[listener_id]
                logger.info(f"Listener {listener_id} removed")
    
    def is_listener_active(self, listener_id):
        """Check if listener is still active"""
        with self.listeners_lock:
            return listener_id in self.listeners
    
    def _broadcast_chunk(self, chunk):
        """Send chunk to all listeners"""
        with self.listeners_lock:
            for listener_id, info in list(self.listeners.items()):
                try:
                    info['writer'].write(chunk)
                    info['writer'].flush()
                    info['bytes_sent'] += len(chunk)
                except Exception as e:
                    logger.error(f"Error broadcasting to listener {listener_id}: {e}")
    
    def _broadcast_loop(self):
        """Main broadcast loop"""
        logger.info("Broadcaster thread started")
        
        consecutive_empty = 0
        
        while self.running:
            # Check if we have data
            if self.audio_buffer.available() >= self.chunk_size:
                chunk = self.audio_buffer.read(self.chunk_size)
                
                if chunk:
                    self._broadcast_chunk(chunk)
                    consecutive_empty = 0
                    
                    # Dynamic sleep based on buffer fill
                    fill_pct = self.audio_buffer.fill_percentage()
                    if fill_pct > 0.8:
                        time.sleep(0.0001)  # 0.1ms
                    elif fill_pct > 0.5:
                        time.sleep(0.0005)  # 0.5ms
                    else:
                        time.sleep(0.001)   # 1ms
                else:
                    consecutive_empty += 1
                    time.sleep(0.005)
            else:
                # Not enough data
                consecutive_empty += 1
                
                if consecutive_empty > 10:
                    time.sleep(0.02)   # 20ms if persistently empty
                else:
                    time.sleep(0.005)  # 5ms otherwise
        
        logger.info("Broadcaster thread stopped")
    
    def start(self):
        """Start broadcasting"""
        if not self.running:
            self.running = True
            self.broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
            self.broadcast_thread.start()
            logger.info("Broadcaster started")
    
    def stop(self):
        """Stop broadcasting"""
        if self.running:
            self.running = False
            if self.broadcast_thread:
                self.broadcast_thread.join(timeout=2.0)
            logger.info("Broadcaster stopped")
    
    def get_stats(self):
        """Get statistics about listeners"""
        with self.listeners_lock:
            return {
                'total_listeners': len(self.listeners),
                'listeners': [
                    {
                        'id': lid,
                        'bytes_sent': info['bytes_sent'],
                        'connected_seconds': time.time() - info['connected_at']
                    }
                    for lid, info in self.listeners.items()
                ]
            }
