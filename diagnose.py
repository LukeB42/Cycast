#!/usr/bin/env python3
"""
Diagnostic script for Cycast
Tests all components and identifies issues
"""

import sys
import os
import time

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        import audio_buffer
        print("  ✓ audio_buffer")
    except ImportError as e:
        print(f"  ✗ audio_buffer: {e}")
        return False
    
    try:
        import stream_broadcaster
        print("  ✓ stream_broadcaster")
    except ImportError as e:
        print(f"  ✗ stream_broadcaster: {e}")
        return False
    
    try:
        import config_loader
        print("  ✓ config_loader")
    except ImportError as e:
        print(f"  ✗ config_loader: {e}")
        return False
    
    try:
        import flask_app
        print("  ✓ flask_app")
    except ImportError as e:
        print(f"  ✗ flask_app: {e}")
        return False
    
    try:
        from flask import Flask
        print("  ✓ Flask")
    except ImportError as e:
        print(f"  ✗ Flask: {e}")
        return False
    
    try:
        import tornado
        print("  ✓ Tornado")
    except ImportError as e:
        print(f"  ✗ Tornado: {e}")
        return False
    
    try:
        import hcl
        print("  ✓ pyhcl")
    except ImportError as e:
        print(f"  ✗ pyhcl: {e}")
        return False
    
    return True


def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from config_loader import Config
        
        # Test with default config
        if os.path.exists('config.hcl'):
            config = Config('config.hcl')
            print("  ✓ Loaded config.hcl")
            print(f"    Source port: {config.get('server', 'source_port')}")
            print(f"    Listen port: {config.get('server', 'listen_port')}")
            print(f"    Station: {config.get('metadata', 'station_name')}")
        else:
            print("  ⚠ config.hcl not found, using defaults")
            config = Config('nonexistent.hcl')
        
        # Test validation
        if config.validate():
            print("  ✓ Configuration valid")
        else:
            print("  ✗ Configuration invalid")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ Config error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_buffer_and_broadcaster():
    """Test buffer and broadcaster functionality"""
    print("\nTesting buffer and broadcaster...")
    
    try:
        import audio_buffer
        import stream_broadcaster
        
        # Create buffer
        buf = audio_buffer.CircularAudioBuffer(size_mb=1)
        print("  ✓ Created audio buffer")
        
        # Create broadcaster
        broadcaster = stream_broadcaster.StreamBroadcaster(buf)
        print("  ✓ Created broadcaster")
        
        # Start broadcaster
        broadcaster.start()
        print("  ✓ Started broadcaster")
        
        # Write test data
        test_data = b"TEST" * 1000
        success = buf.write(test_data)
        if success:
            print(f"  ✓ Wrote {len(test_data)} bytes to buffer")
        else:
            print("  ✗ Failed to write to buffer")
            return False
        
        # Check buffer has data
        available = buf.available()
        if available > 0:
            print(f"  ✓ Buffer has {available} bytes available")
        else:
            print("  ✗ Buffer empty after write")
            return False
        
        # Test broadcaster with fake listener
        class FakeListener:
            def __init__(self):
                self.data = b''
                self.active = True
            
            def write(self, data):
                self.data += data
            
            def flush(self):
                pass
        
        listener = FakeListener()
        listener_id = broadcaster.add_listener(listener)
        print(f"  ✓ Added test listener (ID: {listener_id})")
        
        # Wait for broadcast
        time.sleep(0.5)
        
        # Check listener received data
        if len(listener.data) > 0:
            print(f"  ✓ Listener received {len(listener.data)} bytes")
        else:
            print("  ✗ Listener received no data")
            print(f"    Buffer available: {buf.available()}")
            print(f"    Listener active: {broadcaster.is_listener_active(listener_id)}")
            broadcaster.stop()
            return False
        
        # Clean up
        broadcaster.remove_listener(listener_id)
        broadcaster.stop()
        print("  ✓ Cleaned up broadcaster")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Buffer/broadcaster error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_playlist_loading():
    """Test playlist loading"""
    print("\nTesting playlist loading...")
    
    if not os.path.exists('./music'):
        print("  ⚠ No music directory found")
        print("    Create ./music and add MP3/OGG files for playlist fallback")
        return True
    
    files = [f for f in os.listdir('./music') if f.lower().endswith(('.mp3', '.ogg'))]
    
    if not files:
        print("  ⚠ Music directory exists but is empty")
        print("    Add MP3/OGG files for playlist fallback")
        return True
    
    print(f"  ✓ Found {len(files)} audio files in ./music")
    for f in files[:5]:
        print(f"    - {f}")
    if len(files) > 5:
        print(f"    ... and {len(files) - 5} more")
    
    return True


def test_streaming_simulation():
    """Simulate the full streaming pipeline"""
    print("\nTesting streaming pipeline...")
    
    try:
        import audio_buffer
        import stream_broadcaster
        import queue
        
        # Create components
        buf = audio_buffer.CircularAudioBuffer(size_mb=1)
        broadcaster = stream_broadcaster.StreamBroadcaster(buf)
        broadcaster.start()
        
        # Create a queue-based listener (like Flask uses)
        class QueueListener:
            def __init__(self):
                self.queue = queue.Queue(maxsize=100)
                self.active = True
            
            def write(self, data):
                if self.active:
                    try:
                        self.queue.put(data, block=False)
                    except queue.Full:
                        pass
            
            def flush(self):
                pass
        
        listener = QueueListener()
        listener_id = broadcaster.add_listener(listener)
        print("  ✓ Created queue-based listener")
        
        # Write data to buffer
        chunks = [b"CHUNK_%d_" % i * 100 for i in range(10)]
        for chunk in chunks:
            buf.write(chunk)
        
        print(f"  ✓ Wrote {len(chunks)} chunks to buffer")
        
        # Wait for processing
        time.sleep(1.0)
        
        # Try to read from queue
        received_chunks = 0
        received_bytes = 0
        
        try:
            while True:
                data = listener.queue.get(timeout=0.1)
                received_chunks += 1
                received_bytes += len(data)
        except queue.Empty:
            pass
        
        if received_chunks > 0:
            print(f"  ✓ Received {received_chunks} chunks ({received_bytes} bytes)")
        else:
            print("  ✗ No data received from queue")
            broadcaster.stop()
            return False
        
        # Clean up
        broadcaster.remove_listener(listener_id)
        broadcaster.stop()
        print("  ✓ Streaming pipeline works correctly")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Streaming pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("Cycast Diagnostic Tool")
    print("=" * 60)
    print()
    
    results = []
    
    # Run tests
    results.append(("Module imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Buffer & Broadcaster", test_buffer_and_broadcaster()))
    results.append(("Playlist loading", test_playlist_loading()))
    results.append(("Streaming pipeline", test_streaming_simulation()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {name:25s} {status}")
    
    print()
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("✓ All diagnostics passed!")
        print("\nYour Cycast installation appears to be working correctly.")
        print("\nTo start the server:")
        print("  python cycast_server.py")
        print("\nTo test streaming:")
        print("  1. Start the server")
        print("  2. Connect a source (Mixxx/VLC) to port 8000")
        print("  3. Open http://localhost:8001/stream in a media player")
        print()
        return 0
    else:
        print("✗ Some diagnostics failed.")
        print("\nPlease fix the issues above before starting the server.")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
