#!/usr/bin/env python3
"""
Quick test to verify chunk_size attribute fix
"""

try:
    import audio_buffer
    import stream_broadcaster
    
    print("Testing StreamBroadcaster with chunk_size parameter...")
    
    # Create buffer
    buf = audio_buffer.CircularAudioBuffer(size_mb=1)
    print("✓ Created buffer")
    
    # Create broadcaster with custom chunk_size
    bc = stream_broadcaster.StreamBroadcaster(buf, chunk_size=16384)
    print("✓ Created broadcaster with chunk_size=16384")
    
    # Verify chunk_size is accessible
    print(f"✓ Broadcaster chunk_size: {bc.chunk_size}")
    
    # Test with default chunk_size
    bc2 = stream_broadcaster.StreamBroadcaster(buf)
    print(f"✓ Default chunk_size: {bc2.chunk_size}")
    
    print("\n✓✓✓ All tests passed! The chunk_size fix is working.")
    print("\nYou can now run: python cycast_server.py")
    
except AttributeError as e:
    print(f"✗ AttributeError: {e}")
    print("\nThe chunk_size attribute is still not defined.")
    print("Please rebuild the Cython modules:")
    print("  python setup.py build_ext --inplace")
    exit(1)
    
except ImportError as e:
    print(f"✗ ImportError: {e}")
    print("\nCython modules not built yet.")
    print("Please build them first:")
    print("  python setup.py build_ext --inplace")
    exit(1)
    
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
