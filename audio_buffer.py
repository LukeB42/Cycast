#!/usr/bin/env python3
"""
Pure Python implementation of audio_buffer for testing
This is a fallback when Cython modules aren't compiled
"""

import threading


class CircularAudioBuffer:
    """Circular buffer for audio data - pure Python version"""
    
    def __init__(self, size_mb=10):
        self.size = size_mb * 1024 * 1024
        self.buffer = bytearray(self.size)
        self.write_pos = 0
        self.read_pos = 0
        self.available_bytes = 0
        self.lock = threading.RLock()
    
    def write(self, data):
        """Write data to buffer, returns True if successful"""
        with self.lock:
            data_len = len(data)
            
            # Check if there's space
            if self.available_bytes + data_len > self.size:
                return False
            
            # Write data (may wrap around)
            for byte in data:
                self.buffer[self.write_pos] = byte
                self.write_pos = (self.write_pos + 1) % self.size
            
            self.available_bytes += data_len
            return True
    
    def read(self, size):
        """Read up to size bytes from buffer"""
        with self.lock:
            # Can't read more than available
            to_read = min(size, self.available_bytes)
            
            if to_read == 0:
                return b''
            
            # Read data (may wrap around)
            data = bytearray(to_read)
            for i in range(to_read):
                data[i] = self.buffer[self.read_pos]
                self.read_pos = (self.read_pos + 1) % self.size
            
            self.available_bytes -= to_read
            return bytes(data)
    
    def available(self):
        """Return number of bytes available to read"""
        with self.lock:
            return self.available_bytes
    
    def space(self):
        """Return number of bytes available to write"""
        with self.lock:
            return self.size - self.available_bytes
    
    def clear(self):
        """Clear all data from buffer"""
        with self.lock:
            self.write_pos = 0
            self.read_pos = 0
            self.available_bytes = 0
    
    def fill_percentage(self):
        """Return buffer fill percentage (0.0 to 1.0)"""
        with self.lock:
            return self.available_bytes / self.size
