#!/usr/bin/env python3
"""
Test script for Cycast Cython modules
Run this after building to verify everything works
"""

import sys
import time

def test_audio_buffer():
    """Test the Cython audio buffer"""
    print("Testing audio_buffer module...")
    
    try:
        import audio_buffer
        
        # Create buffer
        buf = audio_buffer.CircularAudioBuffer(size_mb=1)
        print("  ✓ Created CircularAudioBuffer")
        
        # Test write
        test_data = b"Hello, World!" * 1000
        success = buf.write(test_data)
        assert success, "Write failed"
        print(f"  ✓ Wrote {len(test_data)} bytes")
        
        # Test available
        avail = buf.available()
        assert avail == len(test_data), f"Available mismatch: {avail} != {len(test_data)}"
        print(f"  ✓ Available: {avail} bytes")
        
        # Test read
        read_data = buf.read(len(test_data))
        assert read_data == test_data, "Read data mismatch"
        print(f"  ✓ Read {len(read_data)} bytes")
        
        # Test wrap-around
        large_data = b"X" * (500 * 1024)  # 500 KB
        for i in range(5):
            buf.write(large_data)
            buf.read(len(large_data))
        print("  ✓ Wrap-around test passed")
        
        # Test fill percentage
        buf.clear()
        buf.write(b"Y" * (512 * 1024))  # 512 KB in 1 MB buffer
        fill = buf.fill_percentage()
        assert 0.45 < fill < 0.55, f"Fill percentage incorrect: {fill}"
        print(f"  ✓ Fill percentage: {fill*100:.1f}%")
        
        print("✓ audio_buffer tests PASSED\n")
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import audio_buffer: {e}")
        print("  Did you run 'make build' or 'python setup.py build_ext --inplace'?")
        return False
    except Exception as e:
        print(f"✗ audio_buffer test FAILED: {e}")
        return False


def test_stream_broadcaster():
    """Test the Cython stream broadcaster"""
    print("Testing stream_broadcaster module...")
    
    try:
        import audio_buffer
        import stream_broadcaster
        
        # Create buffer and broadcaster
        buf = audio_buffer.CircularAudioBuffer(size_mb=1)
        broadcaster = stream_broadcaster.StreamBroadcaster(buf)
        print("  ✓ Created StreamBroadcaster")
        
        # Test listener management
        class FakeSocket:
            def __init__(self):
                self.data = b''
            def write(self, data):
                self.data += data
            def flush(self):
                pass
        
        sock1 = FakeSocket()
        sock2 = FakeSocket()
        
        id1 = broadcaster.add_listener(sock1)
        id2 = broadcaster.add_listener(sock2)
        print(f"  ✓ Added 2 listeners (IDs: {id1}, {id2})")
        
        # Test listener count
        count = broadcaster.get_listener_count()
        assert count == 2, f"Listener count mismatch: {count} != 2"
        print(f"  ✓ Listener count: {count}")
        
        # Test active check
        assert broadcaster.is_listener_active(id1), "Listener 1 should be active"
        assert broadcaster.is_listener_active(id2), "Listener 2 should be active"
        print("  ✓ Listeners are active")
        
        # Test broadcaster start/stop
        broadcaster.start()
        print("  ✓ Started broadcaster")
        
        # Write some data and let it broadcast
        test_data = b"Broadcasting test data!" * 100
        buf.write(test_data)
        time.sleep(0.5)  # Give broadcaster time to process
        
        broadcaster.stop()
        print("  ✓ Stopped broadcaster")
        
        # Test stats
        stats = broadcaster.get_stats()
        print(f"  ✓ Stats: {stats['total_listeners']} listeners, "
              f"{stats['total_bytes_sent']} bytes sent")
        
        # Clean up
        broadcaster.remove_listener(id1)
        broadcaster.remove_listener(id2)
        print("  ✓ Removed listeners")
        
        print("✓ stream_broadcaster tests PASSED\n")
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import stream_broadcaster: {e}")
        print("  Did you run 'make build' or 'python setup.py build_ext --inplace'?")
        return False
    except Exception as e:
        print(f"✗ stream_broadcaster test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test integration between modules"""
    print("Testing integration...")
    
    try:
        import audio_buffer
        import stream_broadcaster
        
        # Create components
        buf = audio_buffer.CircularAudioBuffer(size_mb=1)
        broadcaster = stream_broadcaster.StreamBroadcaster(buf)
        
        # Simulate streaming scenario
        class FakeListener:
            def __init__(self, name):
                self.name = name
                self.received = b''
            def write(self, data):
                self.received += data
            def flush(self):
                pass
        
        listeners = [FakeListener(f"L{i}") for i in range(3)]
        
        broadcaster.start()
        for listener in listeners:
            broadcaster.add_listener(listener)
        
        # Stream data
        chunks = [b"Chunk %d data! " % i for i in range(20)]
        for chunk in chunks:
            buf.write(chunk * 100)  # Write larger chunks
            time.sleep(0.05)
        
        time.sleep(0.5)  # Let broadcaster process
        broadcaster.stop()
        
        # Verify all listeners got data
        for listener in listeners:
            assert len(listener.received) > 0, f"{listener.name} received no data"
        
        print(f"  ✓ All {len(listeners)} listeners received data")
        print("✓ Integration tests PASSED\n")
        return True
        
    except Exception as e:
        print(f"✗ Integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("Cycast Cython Module Tests")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("audio_buffer", test_audio_buffer()))
    results.append(("stream_broadcaster", test_stream_broadcaster()))
    results.append(("integration", test_integration()))
    
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "PASSED" if passed else "FAILED"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {name:20s} {status}")
    
    print()
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("✓ All tests passed! The Cython modules are working correctly.")
        sys.exit(0)
    else:
        print("✗ Some tests failed. Please check the output above.")
        sys.exit(1)
