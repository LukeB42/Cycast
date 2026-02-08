# Troubleshooting: No Audio from /stream Endpoint

## Quick Diagnostics

Run the diagnostic script first:
```bash
python diagnose.py
```

This will test all components and identify issues.

## Common Issues and Solutions

### 1. No Audio from Playlist

**Symptom:** Server starts, but `/stream` endpoint produces no audio

**Checklist:**
- [ ] Do you have MP3/OGG files in the `./music` directory?
- [ ] Is the playlist loading? Check server output for "Loaded N files into playlist"
- [ ] Is the broadcaster thread running? Check for "Broadcaster started"

**Solution:**
```bash
# Create test audio
mkdir -p music
python generate_test_audio.py

# Restart server
python cycast_server.py
```

**What to look for in logs:**
```
Playlist loaded: 1 tracks
Broadcaster started
No source connected, starting playlist fallback
Playing from playlist: test_tone.mp3
```

### 2. Broadcaster Not Sending Data

**Symptom:** Buffer has data, but listeners receive nothing

**Debug:**
Add this to check buffer status:
```bash
# While server is running, in another terminal:
curl http://localhost:8001/api/stats
```

Look for:
```json
{
  "buffer": {
    "available": 524288,  // Should be > 0
    "fill_percentage": 5.0
  }
}
```

**If buffer is empty (available: 0):**
- Playlist not feeding data
- Check file permissions on music files
- Check for errors in server console

**If buffer is full but no broadcast:**
- Broadcaster thread may have crashed
- Check for Python exceptions in console
- Restart server

### 3. Flask/Tornado Configuration Issue

**Symptom:** Can access status page but not `/stream`

**Test:**
```bash
# Test if endpoint responds
curl -I http://localhost:8001/stream

# Should return:
HTTP/1.1 200 OK
Content-Type: audio/mpeg
```

**If 404 Not Found:**
- Check mount_point in config.hcl
- Default is `/stream`, not `/stream.mp3`

**If connection closes immediately:**
- Check Flask app is properly integrated
- Verify Tornado is running (not dev server)

### 4. Cython Module Issues

**Symptom:** Import errors or broadcaster not working

**Test:**
```bash
python -c "import audio_buffer; import stream_broadcaster; print('OK')"
```

**If import fails:**
```bash
# Rebuild Cython modules
python setup.py build_ext --inplace

# Or
make build
```

### 5. Network/Firewall Issues

**Test locally first:**
```bash
# On the server machine
curl http://localhost:8001/stream --output test.mp3 &
sleep 5
killall curl
file test.mp3  # Should say "MPEG"
```

**If that works but browser doesn't:**
- Firewall blocking port 8001
- Try with VLC: `vlc http://localhost:8001/stream`

## Step-by-Step Debugging

### Step 1: Verify Components

```bash
# Test imports
python -c "import audio_buffer; print('buffer OK')"
python -c "import stream_broadcaster; print('broadcaster OK')"
python -c "from flask_app import StreamWebApp; print('flask OK')"
```

### Step 2: Test Buffer Directly

```python
import audio_buffer
buf = audio_buffer.CircularAudioBuffer(size_mb=1)
buf.write(b"TEST" * 1000)
print(f"Available: {buf.available()}")  # Should be 4000
data = buf.read(4000)
print(f"Read: {len(data)}")  # Should be 4000
```

### Step 3: Test Broadcaster Directly

```python
import audio_buffer
import stream_broadcaster
import time

buf = audio_buffer.CircularAudioBuffer(size_mb=1)
bc = stream_broadcaster.StreamBroadcaster(buf)
bc.start()

# Write test data
for i in range(10):
    buf.write(b"TEST" * 1000)
    time.sleep(0.1)

print(f"Stats: {bc.get_stats()}")
bc.stop()
```

### Step 4: Check Server Output

When you start the server, you should see:

```
============================================================
Starting Cycast Server
============================================================
Configuration loaded from: config.hcl
Source port: 8000 (password: ******)
Listen port: 8001
Mount point: /stream
Station: Cycast Radio
Buffer size: 10 MB
============================================================
Playlist loaded: 1 tracks
============================================================
Server ready!
...
============================================================

Broadcaster started
No source connected, starting playlist fallback
Playing from playlist: test_tone.mp3
```

**Missing "Broadcaster started"?**
- Cython module issue
- Rebuild: `python setup.py build_ext --inplace`

**Missing "Playlist loaded"?**
- No music files
- Run: `python generate_test_audio.py`

**Missing "Playing from playlist"?**
- Playlist feeder not starting
- Check for exceptions in console

### Step 5: Test Streaming

```bash
# Terminal 1: Start server
python cycast_server.py

# Terminal 2: Stream to file
timeout 10 curl http://localhost:8001/stream --output test.mp3

# Check file
ls -lh test.mp3  # Should be several KB
file test.mp3    # Should say "MPEG" or "Audio file"
```

**If test.mp3 is 0 bytes:**
- No data being written to buffer
- Check playlist is playing (see server console)

**If test.mp3 is HTML:**
- Wrong URL (probably got the status page)
- Use `/stream`, not `/`

## Enable Verbose Logging

Edit `config.hcl`:
```hcl
advanced {
  verbose_logging = true
}
```

This will show:
- Every chunk written to buffer
- Every chunk broadcast to listeners
- Detailed connection info

## Check Port Conflicts

```bash
# Linux/Mac
netstat -an | grep -E ':(8000|8001)'

# Should show:
tcp  0  0.0.0.0:8000  LISTEN
tcp  0  0.0.0.0:8001  LISTEN
```

## Test with Different Players

**VLC:**
```bash
vlc http://localhost:8001/stream
```

**mpv:**
```bash
mpv http://localhost:8001/stream
```

**ffplay:**
```bash
ffplay -nodisp http://localhost:8001/stream
```

**curl (save to file):**
```bash
curl http://localhost:8001/stream --output stream.mp3
```

## Still Not Working?

1. Run full diagnostics:
   ```bash
   python diagnose.py
   ```

2. Check server output for errors

3. Enable verbose logging in config.hcl

4. Test each component individually (see steps above)

5. Try with test audio:
   ```bash
   python generate_test_audio.py
   python cycast_server.py
   ```

6. Check GitHub issues or create a new one with:
   - Output of `diagnose.py`
   - Server console output
   - Your `config.hcl` file
   - OS and Python version

## Success Indicators

When everything is working, you should see:

✓ Diagnostic script passes all tests
✓ Server shows "Broadcaster started"
✓ Server shows "Playing from playlist: ..."
✓ `/api/stats` shows buffer.available > 0
✓ Media player connects and plays audio
✓ Status page shows "Listeners: 1"

## Quick Fix Script

```bash
#!/bin/bash
# quick-fix.sh - Reset and test Cycast

echo "Cleaning up..."
make clean

echo "Rebuilding Cython modules..."
make build

echo "Creating test audio..."
python generate_test_audio.py

echo "Running diagnostics..."
python diagnose.py

echo "Ready! Start server with:"
echo "  python cycast_server.py"
```

Save as `quick-fix.sh`, make executable (`chmod +x quick-fix.sh`), and run it.
