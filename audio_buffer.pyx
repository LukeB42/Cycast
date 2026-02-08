# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

"""
Audio buffer module optimized with Cython for high-performance streaming
"""

from libc.stdlib cimport malloc, free
from libc.string cimport memcpy
from cpython.bytes cimport PyBytes_FromStringAndSize, PyBytes_AsString, PyBytes_Size
cimport cython

cdef class CircularAudioBuffer:
    """
    High-performance circular buffer for audio streaming
    Uses Cython for zero-copy operations where possible
    """
    cdef:
        char* buffer
        Py_ssize_t buffer_size
        Py_ssize_t write_pos
        Py_ssize_t read_pos
        Py_ssize_t data_available
        object lock
    
    def __cinit__(self, int size_mb=10):
        """Initialize the circular buffer"""
        self.buffer_size = size_mb * 1024 * 1024
        self.buffer = <char*>malloc(self.buffer_size)
        if not self.buffer:
            raise MemoryError("Failed to allocate audio buffer")
        
        self.write_pos = 0
        self.read_pos = 0
        self.data_available = 0
    
    def __init__(self, int size_mb=10):
        import threading
        self.lock = threading.RLock()
    
    def __dealloc__(self):
        """Clean up allocated memory"""
        if self.buffer:
            free(self.buffer)
    
    @cython.boundscheck(False)
    @cython.wraparound(False)
    cpdef bint write(self, bytes data):
        """
        Write data to the buffer
        Returns True if successful, False if buffer is full
        """
        cdef:
            Py_ssize_t data_len = PyBytes_Size(data)
            char* data_ptr = PyBytes_AsString(data)
            Py_ssize_t space_available
            Py_ssize_t first_chunk
            Py_ssize_t second_chunk
        
        with self.lock:
            space_available = self.buffer_size - self.data_available
            
            if data_len > space_available:
                return False
            
            # Handle wrap-around
            if self.write_pos + data_len > self.buffer_size:
                first_chunk = self.buffer_size - self.write_pos
                second_chunk = data_len - first_chunk
                
                memcpy(self.buffer + self.write_pos, data_ptr, first_chunk)
                memcpy(self.buffer, data_ptr + first_chunk, second_chunk)
                self.write_pos = second_chunk
            else:
                memcpy(self.buffer + self.write_pos, data_ptr, data_len)
                self.write_pos += data_len
                if self.write_pos >= self.buffer_size:
                    self.write_pos = 0
            
            self.data_available += data_len
            return True
    
    @cython.boundscheck(False)
    @cython.wraparound(False)
    cpdef bytes read(self, Py_ssize_t size):
        """
        Read data from the buffer
        Returns bytes object with data, or empty bytes if not enough data
        """
        cdef:
            bytes result
            char* temp_buffer
            Py_ssize_t first_chunk
            Py_ssize_t second_chunk
        
        with self.lock:
            if size > self.data_available:
                return b''
            
            # Handle wrap-around
            if self.read_pos + size > self.buffer_size:
                first_chunk = self.buffer_size - self.read_pos
                second_chunk = size - first_chunk
                
                # Allocate temporary buffer for combining chunks
                temp_buffer = <char*>malloc(size)
                if not temp_buffer:
                    return b''
                
                memcpy(temp_buffer, self.buffer + self.read_pos, first_chunk)
                memcpy(temp_buffer + first_chunk, self.buffer, second_chunk)
                
                result = PyBytes_FromStringAndSize(temp_buffer, size)
                free(temp_buffer)
                
                self.read_pos = second_chunk
            else:
                result = PyBytes_FromStringAndSize(self.buffer + self.read_pos, size)
                self.read_pos += size
                if self.read_pos >= self.buffer_size:
                    self.read_pos = 0
            
            self.data_available -= size
            return result
    
    cpdef Py_ssize_t available(self):
        """Return the amount of data available to read"""
        with self.lock:
            return self.data_available
    
    cpdef Py_ssize_t space(self):
        """Return the amount of space available for writing"""
        with self.lock:
            return self.buffer_size - self.data_available
    
    cpdef void clear(self):
        """Clear the buffer"""
        with self.lock:
            self.write_pos = 0
            self.read_pos = 0
            self.data_available = 0
    
    cpdef float fill_percentage(self):
        """Return buffer fill percentage (0.0 to 1.0)"""
        with self.lock:
            return <float>self.data_available / <float>self.buffer_size
