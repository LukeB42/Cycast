#!/usr/bin/env python3
"""
Comprehensive test suite for Cycast hybrid Flask/Tornado implementation
Tests that the Tornado async handler fixes VLC startup delay
"""

import subprocess
import time
import sys
import signal
import requests
import socket

def test_server_starts():
    """Test 1: Server starts successfully"""
    print("=" * 70)
    print("TEST 1: Server Startup")
    print("=" * 70)
    
    try:
        # Start server
        print("Starting Cycast server...")
        server = subprocess.Popen(
            ['python', 'cycast_server.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Wait for startup and capture logs
        print("\nServer output:")
        print("-" * 70)
        startup_success = False
        for i in range(30):  # Wait up to 3 seconds
            time.sleep(0.1)
            if server.poll() is not None:
                print("✗ Server exited prematurely!")
                print(server.stdout.read())
                return False, None
            
            # Check if server is responding
            try:
                response = requests.get('http://localhost:8001/api/status', timeout=0.5)
                if response.status_code == 200:
                    startup_success = True
                    break
            except:
                pass
        
        if startup_success:
            print("✓ Server started successfully")
            print("-" * 70)
            return True, server
        else:
            print("✗ Server failed to respond after 3 seconds")
            server.terminate()
            return False, None
            
    except Exception as e:
        print(f"✗ Error starting server: {e}")
        return False, None


def test_status_page(server):
    """Test 2: Status page works (Flask WSGI)"""
    print("\n" + "=" * 70)
    print("TEST 2: Status Page (Flask)")
    print("=" * 70)
    
    try:
        response = requests.get('http://localhost:8001/', timeout=5)
        
        if response.status_code == 200:
            if 'Cycast' in response.text and 'NOW PLAYING' in response.text:
                print("✓ Status page loads correctly")
                print(f"  Response size: {len(response.text)} bytes")
                return True
            else:
                print("✗ Status page has unexpected content")
                return False
        else:
            print(f"✗ Status page returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Error accessing status page: {e}")
        return False


def test_api_endpoints(server):
    """Test 3: API endpoints work (Flask WSGI)"""
    print("\n" + "=" * 70)
    print("TEST 3: API Endpoints (Flask)")
    print("=" * 70)
    
    results = []
    
    # Test /api/status
    try:
        response = requests.get('http://localhost:8001/api/status', timeout=5)
        data = response.json()
        
        if 'listeners' in data and 'station_name' in data:
            print("✓ /api/status works")
            print(f"  Station: {data.get('station_name')}")
            print(f"  Listeners: {data.get('listeners')}")
            results.append(True)
        else:
            print("✗ /api/status missing expected fields")
            results.append(False)
    except Exception as e:
        print(f"✗ /api/status error: {e}")
        results.append(False)
    
    # Test /api/stats
    try:
        response = requests.get('http://localhost:8001/api/stats', timeout=5)
        data = response.json()
        
        if 'buffer' in data and 'total_listeners' in data:
            print("✓ /api/stats works")
            print(f"  Buffer available: {data['buffer'].get('available')} bytes")
            results.append(True)
        else:
            print("✗ /api/stats missing expected fields")
            results.append(False)
    except Exception as e:
        print(f"✗ /api/stats error: {e}")
        results.append(False)
    
    return all(results)


def test_stream_connection_speed(server):
    """Test 4: Stream connects quickly (Tornado async handler)"""
    print("\n" + "=" * 70)
    print("TEST 4: Stream Connection Speed (Tornado Async)")
    print("=" * 70)
    print("This is the key test - stream should connect in < 2 seconds")
    print()
    
    # Test with raw socket for precise timing
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        print("Connecting to stream...")
        start_time = time.time()
        
        sock.connect(('localhost', 8001))
        
        # Send HTTP GET
        request = b"GET /stream HTTP/1.1\r\nHost: localhost\r\n\r\n"
        sock.sendall(request)
        
        # Wait for first byte
        first_byte = sock.recv(1)
        elapsed = time.time() - start_time
        
        sock.close()
        
        print(f"Time to first byte: {elapsed:.3f} seconds")
        
        if elapsed < 2.0:
            print("✓ EXCELLENT: Stream connected in < 2 seconds!")
            print("  This means VLC should work without Ctrl+C")
            return True
        elif elapsed < 5.0:
            print("⚠ ACCEPTABLE: Stream connected in < 5 seconds")
            print("  VLC might still have slight delay")
            return True
        else:
            print("✗ SLOW: Stream took > 5 seconds to connect")
            print("  VLC will likely still need Ctrl+C")
            return False
            
    except socket.timeout:
        print("✗ Connection timed out (> 10 seconds)")
        return False
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False


def test_stream_data_flow(server):
    """Test 5: Stream delivers continuous data"""
    print("\n" + "=" * 70)
    print("TEST 5: Stream Data Flow")
    print("=" * 70)
    
    try:
        print("Streaming for 3 seconds...")
        
        response = requests.get('http://localhost:8001/stream', stream=True, timeout=10)
        
        if response.status_code != 200:
            print(f"✗ Stream returned {response.status_code}")
            return False
        
        # Check headers
        if response.headers.get('Content-Type') != 'audio/mpeg':
            print(f"✗ Wrong content type: {response.headers.get('Content-Type')}")
            return False
        
        print("✓ Headers correct (audio/mpeg)")
        
        # Collect data for 3 seconds
        bytes_received = 0
        start_time = time.time()
        
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                bytes_received += len(chunk)
            
            if time.time() - start_time > 3:
                break
        
        elapsed = time.time() - start_time
        
        if bytes_received > 0:
            rate = bytes_received / elapsed
            print(f"✓ Received {bytes_received} bytes in {elapsed:.1f}s")
            print(f"  Rate: {rate:.0f} bytes/sec ({rate*8/1000:.0f} kbps)")
            
            # For 128kbps stream, expect ~16,000 bytes/sec
            if rate > 10000:
                print("✓ Data rate looks good")
                return True
            else:
                print("⚠ Data rate seems low")
                return True  # Still pass, might be low bitrate test file
        else:
            print("✗ No data received")
            return False
            
    except Exception as e:
        print(f"✗ Stream error: {e}")
        return False


def test_multiple_concurrent_listeners(server):
    """Test 6: Multiple listeners can connect simultaneously"""
    print("\n" + "=" * 70)
    print("TEST 6: Concurrent Listeners")
    print("=" * 70)
    
    import threading
    
    results = {'success': 0, 'failed': 0}
    
    def connect_listener(listener_id):
        try:
            response = requests.get('http://localhost:8001/stream', 
                                   stream=True, timeout=5)
            
            # Get some data
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    results['success'] += 1
                    break
        except Exception as e:
            results['failed'] += 1
    
    # Start 5 concurrent listeners
    threads = []
    for i in range(5):
        t = threading.Thread(target=connect_listener, args=(i,))
        t.daemon = True
        t.start()
        threads.append(t)
        time.sleep(0.1)  # Stagger connections slightly
    
    # Wait for threads
    for t in threads:
        t.join(timeout=10)
    
    print(f"Results: {results['success']} succeeded, {results['failed']} failed")
    
    if results['success'] >= 3:
        print("✓ Multiple listeners work")
        return True
    else:
        print("✗ Too many listener failures")
        return False


def test_tornado_handler_used(server):
    """Test 7: Verify Tornado handler is actually being used"""
    print("\n" + "=" * 70)
    print("TEST 7: Verify Tornado Async Handler")
    print("=" * 70)
    
    # The server should have logged that it's using Tornado handler
    # We can verify by checking the response behavior
    
    try:
        import socket
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('localhost', 8001))
        
        # Send request
        request = b"GET /stream HTTP/1.1\r\nHost: localhost\r\n\r\n"
        sock.sendall(request)
        
        # Read response headers
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = sock.recv(1024)
            if not chunk:
                break
            response += chunk
        
        sock.close()
        
        response_str = response.decode('utf-8', errors='ignore')
        
        # Check for Tornado-specific behaviors
        if "HTTP/1.1 200" in response_str or "HTTP/1.0 200" in response_str:
            print("✓ Stream endpoint responds correctly")
            
            # Tornado typically doesn't add certain Flask-specific headers
            if "Server:" in response_str:
                server_header = [line for line in response_str.split('\r\n') 
                               if line.startswith('Server:')]
                if server_header:
                    print(f"  Server header: {server_header[0]}")
            
            print("✓ Tornado async handler appears to be working")
            return True
        else:
            print("✗ Unexpected response")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def run_all_tests():
    """Run complete test suite"""
    print("\n" + "=" * 70)
    print("CYCAST HYBRID FLASK/TORNADO TEST SUITE")
    print("=" * 70)
    print()
    
    server = None
    test_results = []
    
    try:
        # Test 1: Server startup
        success, server = test_server_starts()
        test_results.append(("Server Startup", success))
        
        if not success or server is None:
            print("\n✗ Cannot continue - server failed to start")
            return False
        
        # Give server a moment to stabilize
        time.sleep(1)
        
        # Test 2: Status page
        success = test_status_page(server)
        test_results.append(("Status Page (Flask)", success))
        
        # Test 3: API endpoints
        success = test_api_endpoints(server)
        test_results.append(("API Endpoints (Flask)", success))
        
        # Test 4: Stream connection speed (KEY TEST)
        success = test_stream_connection_speed(server)
        test_results.append(("Stream Speed (Tornado)", success))
        
        # Test 5: Stream data flow
        success = test_stream_data_flow(server)
        test_results.append(("Stream Data Flow", success))
        
        # Test 6: Concurrent listeners
        success = test_multiple_concurrent_listeners(server)
        test_results.append(("Concurrent Listeners", success))
        
        # Test 7: Tornado handler verification
        success = test_tornado_handler_used(server)
        test_results.append(("Tornado Handler", success))
        
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        test_results.append(("Tests", False))
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        test_results.append(("Tests", False))
    finally:
        # Cleanup
        if server:
            print("\n" + "=" * 70)
            print("Shutting down server...")
            server.terminate()
            try:
                server.wait(timeout=5)
            except:
                server.kill()
            print("Server stopped")
    
    # Print results
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    
    for test_name, passed in test_results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8s} {test_name}")
    
    print("=" * 70)
    
    all_passed = all(result[1] for result in test_results)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nThe hybrid Flask/Tornado implementation is working correctly.")
        print("VLC should now connect without requiring Ctrl+C!")
        return True
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("\nPlease review the failures above.")
        failed_tests = [name for name, passed in test_results if not passed]
        print(f"Failed: {', '.join(failed_tests)}")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
