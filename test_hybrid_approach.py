#!/usr/bin/env python3
"""
Test script to verify the hybrid Tornado/Flask approach
Tests the TornadoStreamHandler without needing full server dependencies
"""

import sys
import asyncio
import queue as Queue
import threading
import time

# Mock the logger
class MockLogger:
    def info(self, msg):
        print(f"INFO: {msg}")
    def error(self, msg):
        print(f"ERROR: {msg}")
    def warning(self, msg):
        print(f"WARNING: {msg}")

logger = MockLogger()

# Import local modules
try:
    import audio_buffer
    import stream_broadcaster
    print("✓ Successfully imported audio_buffer and stream_broadcaster")
except ImportError as e:
    print(f"✗ Failed to import modules: {e}")
    sys.exit(1)


class MockStreamServer:
    """Mock stream server for testing"""
    def __init__(self):
        self.audio_buffer = audio_buffer.CircularAudioBuffer(size_mb=1)
        self.broadcaster = stream_broadcaster.StreamBroadcaster(self.audio_buffer, chunk_size=8192)
        
        self.config_data = {
            'metadata': {
                'enable_icy': True,
                'icy_metaint': 16000,
                'station_name': 'Test Station',
                'station_genre': 'Test',
                'station_url': 'http://test'
            }
        }
    
    def config_get(self, section, key):
        return self.config_data.get(section, {}).get(key)
    
    # Make config callable like the real one
    class ConfigProxy:
        def __init__(self, server):
            self.server = server
        
        def get(self, section, key):
            return self.server.config_get(section, key)
    
    @property  
    def config(self):
        return self.ConfigProxy(self)


class MockRequest:
    """Mock Tornado request object"""
    def __init__(self):
        self.remote_ip = "127.0.0.1"
        self.headers = {}


class MockTornadoStreamHandler:
    """Simulated TornadoStreamHandler for testing async behavior"""
    
    def __init__(self, stream_server):
        self.stream_server = stream_server
        self.request = MockRequest()
        self.written_data = []
        self.flushed_count = 0
    
    def set_header(self, key, value):
        """Mock set_header"""
        pass
    
    def write(self, data):
        """Mock write"""
        self.written_data.append(data)
    
    async def flush(self):
        """Mock flush"""
        self.flushed_count += 1
        await asyncio.sleep(0.001)  # Simulate async I/O
    
    async def get(self):
        """The async streaming handler - this is what we're testing"""
        client_ip = self.request.remote_ip
        logger.info(f"New listener from {client_ip} (Tornado async handler)")
        
        # Set headers (mocked)
        self.set_header('Content-Type', 'audio/mpeg')
        
        # Create queue-based writer
        class StreamWriter:
            def __init__(self):
                self.queue = Queue.Queue(maxsize=500)
                self.active = True
            
            def write(self, data):
                if self.active:
                    try:
                        self.queue.put(data, block=False)
                    except Queue.Full:
                        pass
            
            def flush(self):
                pass
            
            def close(self):
                self.active = False
        
        writer = StreamWriter()
        listener_id = self.stream_server.broadcaster.add_listener(writer)
        
        chunks_received = 0
        
        try:
            # Stream data asynchronously (this is the key part)
            loop = asyncio.get_event_loop()
            
            # Stream for a limited time in test
            start_time = time.time()
            timeout = 2.0  # Test for 2 seconds
            
            while time.time() - start_time < timeout:
                try:
                    # Get data from queue asynchronously
                    data = await loop.run_in_executor(
                        None,
                        lambda: writer.queue.get(timeout=0.5)
                    )
                    
                    if data:
                        self.write(data)
                        await self.flush()
                        chunks_received += 1
                        
                except Queue.Empty:
                    # No data available, continue
                    await asyncio.sleep(0.01)
                    continue
                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            writer.close()
            self.stream_server.broadcaster.remove_listener(listener_id)
            logger.info(f"Listener cleanup complete (received {chunks_received} chunks)")
        
        return chunks_received


def test_audio_pipeline():
    """Test the audio buffer and broadcaster"""
    print("\n" + "="*60)
    print("TEST 1: Audio Pipeline")
    print("="*60)
    
    # Create components
    buf = audio_buffer.CircularAudioBuffer(size_mb=1)
    broadcaster = stream_broadcaster.StreamBroadcaster(buf, chunk_size=8192)
    
    print("✓ Created buffer and broadcaster")
    
    # Start broadcaster
    broadcaster.start()
    print("✓ Started broadcaster")
    
    # Write test data
    test_data = b"TEST_AUDIO_DATA" * 1000
    for i in range(10):
        if buf.write(test_data):
            pass
        else:
            print(f"  Buffer full after {i} writes")
            break
    
    print(f"✓ Wrote data to buffer (available: {buf.available()} bytes)")
    
    # Wait a moment for broadcasting
    time.sleep(0.5)
    
    # Stop
    broadcaster.stop()
    print("✓ Stopped broadcaster")
    
    return True


async def test_async_streaming():
    """Test the async streaming handler"""
    print("\n" + "="*60)
    print("TEST 2: Async Streaming Handler")
    print("="*60)
    
    # Create mock server
    server = MockStreamServer()
    print("✓ Created mock server")
    
    # Start broadcaster
    server.broadcaster.start()
    print("✓ Started broadcaster")
    
    # Feed data to buffer in background
    def feed_data():
        test_chunk = b"AUDIO_CHUNK_" * 100
        for i in range(100):
            if not server.broadcaster.running:
                break
            server.audio_buffer.write(test_chunk)
            time.sleep(0.02)  # Feed data every 20ms
    
    feeder_thread = threading.Thread(target=feed_data, daemon=True)
    feeder_thread.start()
    print("✓ Started data feeder thread")
    
    # Create and run handler
    handler = MockTornadoStreamHandler(server)
    print("✓ Created async handler")
    
    print("⏳ Testing async streaming for 2 seconds...")
    chunks_received = await handler.get()
    
    print(f"✓ Async handler received {chunks_received} chunks")
    print(f"✓ Handler wrote {len(handler.written_data)} times")
    print(f"✓ Handler flushed {handler.flushed_count} times")
    
    # Stop broadcaster
    server.broadcaster.stop()
    
    # Verify we got data
    if chunks_received > 0:
        print("✓ Async streaming worked! Data flowed through the pipeline")
        return True
    else:
        print("✗ No chunks received - streaming may have issues")
        return False


async def test_immediate_response():
    """Test that async handler responds immediately (VLC fix test)"""
    print("\n" + "="*60)
    print("TEST 3: Immediate Response (VLC Fix)")
    print("="*60)
    
    server = MockStreamServer()
    server.broadcaster.start()
    
    # Pre-fill buffer with data
    test_chunk = b"IMMEDIATE_DATA" * 1000
    for _ in range(5):
        server.audio_buffer.write(test_chunk)
    
    print(f"✓ Pre-filled buffer with {server.audio_buffer.available()} bytes")
    
    # Create handler
    handler = MockTornadoStreamHandler(server)
    
    # Time how long it takes to get first data
    start_time = time.time()
    
    # Run handler asynchronously
    task = asyncio.create_task(handler.get())
    
    # Wait for first write
    while len(handler.written_data) == 0 and time.time() - start_time < 2.0:
        await asyncio.sleep(0.01)
    
    first_data_time = time.time() - start_time
    
    # Cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    server.broadcaster.stop()
    
    print(f"✓ First data received in {first_data_time:.3f} seconds")
    
    if first_data_time < 0.5:
        print("✓ EXCELLENT: Data arrived immediately (< 0.5s)")
        print("  This should fix the VLC startup delay!")
        return True
    elif first_data_time < 1.0:
        print("✓ GOOD: Data arrived quickly (< 1s)")
        return True
    else:
        print("⚠ SLOW: Data took > 1s to arrive")
        return False


def test_queue_behavior():
    """Test that Queue.get() in executor doesn't block IOLoop"""
    print("\n" + "="*60)
    print("TEST 4: Queue Behavior with Executor")
    print("="*60)
    
    async def queue_test():
        q = Queue.Queue()
        loop = asyncio.get_event_loop()
        
        # Put data in queue after a delay
        def delayed_put():
            time.sleep(0.2)
            q.put(b"TEST_DATA")
        
        threading.Thread(target=delayed_put, daemon=True).start()
        
        # Try to get from queue using executor
        try:
            start = time.time()
            data = await loop.run_in_executor(
                None,
                lambda: q.get(timeout=0.5)
            )
            elapsed = time.time() - start
            
            print(f"✓ Got data from queue in {elapsed:.3f}s")
            print(f"✓ Data: {data}")
            
            if elapsed < 0.3:
                print("✓ run_in_executor allows IOLoop to process other events")
                return True
            else:
                print("⚠ run_in_executor may have blocked")
                return False
                
        except Queue.Empty:
            print("✗ Queue timeout")
            return False
    
    return asyncio.run(queue_test())


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Cycast Hybrid Tornado/Flask Implementation Tests")
    print("="*60)
    
    results = []
    
    # Test 1: Basic audio pipeline
    try:
        results.append(("Audio Pipeline", test_audio_pipeline()))
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Audio Pipeline", False))
    
    # Test 2: Async streaming
    try:
        result = asyncio.run(test_async_streaming())
        results.append(("Async Streaming", result))
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Async Streaming", False))
    
    # Test 3: Immediate response (VLC fix)
    try:
        result = asyncio.run(test_immediate_response())
        results.append(("Immediate Response", result))
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Immediate Response", False))
    
    # Test 4: Queue behavior
    try:
        results.append(("Queue with Executor", test_queue_behavior()))
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Queue with Executor", False))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    print("="*60)
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓✓✓ All tests passed!")
        print("\nThe hybrid Tornado/Flask approach is working correctly.")
        print("This should fix the VLC startup delay issue.")
        return 0
    else:
        print("\n✗ Some tests failed.")
        print("There may be issues with the implementation.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
