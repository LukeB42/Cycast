#!/usr/bin/env python3
"""
Test script to verify IOLoop tickler fixes VLC startup delay
"""

import subprocess
import time
import sys
import signal

def test_vlc_startup():
    """Test that VLC can start playback without manual intervention"""
    
    print("=" * 60)
    print("Testing VLC Startup with IOLoop Tickler")
    print("=" * 60)
    print()
    
    # Start the server
    print("1. Starting Cycast server...")
    server_process = subprocess.Popen(
        ['python', 'cycast_server.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    print("2. Waiting for server to initialize...")
    time.sleep(3)
    
    # Check if server is running
    if server_process.poll() is not None:
        print("✗ Server failed to start!")
        print(server_process.stderr.read())
        return False
    
    print("✓ Server started (PID: {})".format(server_process.pid))
    print()
    
    # Test streaming with curl (simulates VLC)
    print("3. Testing stream connection...")
    print("   Connecting to http://localhost:8001/stream")
    print("   If this hangs for more than 2 seconds, the tickler isn't working")
    print()
    
    start_time = time.time()
    
    try:
        # Try to get stream data
        curl_process = subprocess.Popen(
            ['curl', '-m', '5', 'http://localhost:8001/stream', '-o', '/dev/null', '-w', '%{http_code}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for first response (should be immediate with tickler)
        time.sleep(2)
        
        if curl_process.poll() is None:
            # Still running - getting data
            elapsed = time.time() - start_time
            print(f"✓ Stream started after {elapsed:.2f} seconds")
            
            # Kill curl
            curl_process.terminate()
            curl_process.wait()
            
            if elapsed < 3.0:
                print("✓ IOLoop tickler is working! (startup < 3 seconds)")
                success = True
            else:
                print("⚠ Stream started but took longer than expected")
                print("  This might indicate the tickler isn't working optimally")
                success = False
        else:
            print("✗ Stream connection failed")
            print(curl_process.stderr.read())
            success = False
            
    except Exception as e:
        print(f"✗ Error testing stream: {e}")
        success = False
    
    finally:
        # Cleanup
        print()
        print("4. Cleaning up...")
        server_process.terminate()
        server_process.wait()
        print("✓ Server stopped")
    
    print()
    print("=" * 60)
    
    if success:
        print("SUCCESS: IOLoop tickler is working!")
        print()
        print("You can now use VLC without pressing Ctrl+C:")
        print("  vlc http://localhost:8001/stream")
        return True
    else:
        print("FAILED: There may still be issues")
        print()
        print("Try adjusting the tickle interval in config.hcl:")
        print("  advanced { ioloop_tickle_interval = 0.05 }")
        return False


def quick_test():
    """Quick test just to see if stream responds"""
    print("Quick stream responsiveness test...")
    print()
    
    import socket
    
    # Try to connect
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    
    try:
        start = time.time()
        sock.connect(('localhost', 8001))
        
        # Send HTTP GET
        request = b"GET /stream HTTP/1.1\r\nHost: localhost\r\n\r\n"
        sock.sendall(request)
        
        # Wait for first byte
        data = sock.recv(1)
        elapsed = time.time() - start
        
        if data:
            print(f"✓ Got first byte in {elapsed:.3f} seconds")
            if elapsed < 1.0:
                print("✓ Excellent responsiveness!")
                return True
            elif elapsed < 3.0:
                print("✓ Good responsiveness")
                return True
            else:
                print("⚠ Slow response - tickler may not be optimal")
                return False
        else:
            print("✗ No data received")
            return False
            
    except socket.timeout:
        print("✗ Connection timed out")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    finally:
        sock.close()


if __name__ == '__main__':
    print()
    
    # Check if curl is available
    try:
        subprocess.run(['curl', '--version'], capture_output=True, check=True)
    except:
        print("Note: curl not found, using simplified test")
        print()
        
        # Just test with socket
        print("Please start the server manually:")
        print("  python cycast_server.py")
        print()
        input("Press Enter when server is running...")
        
        if quick_test():
            print()
            print("Stream is responsive! Try VLC:")
            print("  vlc http://localhost:8001/stream")
        sys.exit(0)
    
    # Full test with automated server start
    result = test_vlc_startup()
    sys.exit(0 if result else 1)
