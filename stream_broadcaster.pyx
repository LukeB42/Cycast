# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

"""
Stream broadcaster module optimized with Cython
Efficiently broadcasts audio to multiple listeners
"""

import threading
import time
import logging
from cpython.bytes cimport PyBytes_Size
cimport cython

# Get logger
logger = logging.getLogger('cycast.broadcaster')

cdef class StreamBroadcaster:
    """
    High-performance broadcaster that sends audio data to multiple listeners
    """
    cdef:
        object audio_buffer  # CircularAudioBuffer instance
        dict listeners
        object listeners_lock
        int next_listener_id
        object broadcast_thread
        bint running
        Py_ssize_t chunk_size  # Configurable chunk size
    
    def __init__(self, audio_buffer, chunk_size=16384):
        self.audio_buffer = audio_buffer
        self.chunk_size = chunk_size  # Configurable chunk size
        self.listeners = {}
        self.listeners_lock = threading.RLock()
        self.next_listener_id = 0
        self.running = False
        self.broadcast_thread = None
    
    cpdef int add_listener(self, object socket_file):
        """
        Add a new listener
        Returns the listener ID
        """
        cdef int listener_id
        
        with self.listeners_lock:
            listener_id = self.next_listener_id
            self.next_listener_id += 1
            
            self.listeners[listener_id] = {
                'socket': socket_file,
                'active': True,
                'bytes_sent': 0,
                'connected_at': time.time()
            }
            
            logger.info(f"Listener {listener_id} added (total: {len(self.listeners)})")
            return listener_id
    
    cpdef void remove_listener(self, int listener_id):
        """Remove a listener"""
        with self.listeners_lock:
            if listener_id in self.listeners:
                del self.listeners[listener_id]
                logger.info(f"Listener {listener_id} removed (total: {len(self.listeners)})")
    
    cpdef bint is_listener_active(self, int listener_id):
        """Check if a listener is still active"""
        with self.listeners_lock:
            if listener_id not in self.listeners:
                return False
            return self.listeners[listener_id]['active']
    
    cpdef int get_listener_count(self):
        """Get the current number of listeners"""
        with self.listeners_lock:
            return len(self.listeners)
    
    @cython.boundscheck(False)
    cdef void _broadcast_chunk(self, bytes chunk):
        """
        Broadcast a chunk of audio to all listeners
        This is the hot path - optimized with Cython
        """
        cdef:
            int listener_id
            dict listener_info
            object socket_file
            list to_remove = []
            Py_ssize_t chunk_size = PyBytes_Size(chunk)
        
        with self.listeners_lock:
            for listener_id, listener_info in list(self.listeners.items()):
                if not listener_info['active']:
                    continue
                
                socket_file = listener_info['socket']
                
                try:
                    socket_file.write(chunk)
                    socket_file.flush()
                    listener_info['bytes_sent'] += chunk_size
                except Exception as e:
                    # Mark for removal
                    listener_info['active'] = False
                    to_remove.append(listener_id)
            
            # Remove disconnected listeners
            for listener_id in to_remove:
                if listener_id in self.listeners:
                    del self.listeners[listener_id]
    
    def _broadcast_loop(self):
        """
        Main broadcast loop - runs in separate thread
        Reads from buffer and sends to all listeners
        """
        cdef:
            bytes chunk
            Py_ssize_t chunk_size = self.chunk_size
            float sleep_time
            int consecutive_empty = 0
        
        logger.info("Broadcaster thread started")
        
        while self.running:
            # Check if we have data to send
            if self.audio_buffer.available() >= chunk_size:
                chunk = self.audio_buffer.read(chunk_size)
                
                if chunk:
                    self._broadcast_chunk(chunk)
                    consecutive_empty = 0
                    
                    # Minimal sleep to yield CPU but stay responsive
                    # Dynamic based on buffer fill percentage
                    fill_pct = self.audio_buffer.fill_percentage()
                    if fill_pct > 0.8:
                        # Buffer is filling up, process faster
                        time.sleep(0.0001)  # 0.1ms
                    elif fill_pct > 0.5:
                        # Normal operation
                        time.sleep(0.0005)  # 0.5ms
                    else:
                        # Buffer running low, be gentle
                        time.sleep(0.001)   # 1ms
                else:
                    # No data despite buffer reporting available
                    consecutive_empty += 1
                    time.sleep(0.005)
            else:
                # Not enough data yet - adaptive backoff
                consecutive_empty += 1
                
                # Longer sleep when consistently empty to save CPU
                if consecutive_empty > 10:
                    time.sleep(0.02)   # 20ms if persistently empty
                else:
                    time.sleep(0.005)  # 5ms otherwise
        
        logger.info("Broadcaster thread stopped")
    
    cpdef void start(self):
        """Start the broadcaster thread"""
        if not self.running:
            self.running = True
            self.broadcast_thread = threading.Thread(target=self._broadcast_loop)
            self.broadcast_thread.daemon = True
            self.broadcast_thread.start()
            logger.info("Broadcaster started")
    
    cpdef void stop(self):
        """Stop the broadcaster thread"""
        if self.running:
            self.running = False
            if self.broadcast_thread:
                self.broadcast_thread.join(timeout=2.0)
            logger.info("Broadcaster stopped")
    
    cpdef dict get_stats(self):
        """Get statistics about listeners"""
        cdef:
            dict stats = {
                'total_listeners': 0,
                'total_bytes_sent': 0,
                'listeners': []
            }
            int listener_id
            dict listener_info
        
        with self.listeners_lock:
            stats['total_listeners'] = len(self.listeners)
            
            for listener_id, listener_info in self.listeners.items():
                stats['total_bytes_sent'] += listener_info['bytes_sent']
                stats['listeners'].append({
                    'id': listener_id,
                    'bytes_sent': listener_info['bytes_sent'],
                    'connected_seconds': int(time.time() - listener_info['connected_at']),
                    'active': listener_info['active']
                })
        
        return stats
