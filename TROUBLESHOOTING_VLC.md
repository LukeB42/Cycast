# Troubleshooting: VLC Requires Ctrl+C to Start Playback

## The Problem

VLC (or other media players) connect to the stream but don't start playing until you press Ctrl+C on the server.

## Root Cause

This is caused by a blocking operation in the Tornado/Flask event loop. When a client connects, the server needs to send initial data immediately, but the event loop may be blocked waiting for something else.

## The Fix (Already Applied)

Three changes have been made:

### 1. Tornado Timeout Configuration

The server now disables timeouts for streaming connections:

```python
http_server = TornadoHTTPServer(
    tornado_app,
    idle_connection_timeout=0,  # No timeout
    body_timeout=0,             # No timeout
    max_buffer_size=10485760,   # 10 MB buffer
)
```

### 2. Initial Data Wait

The stream endpoint now waits for initial data before responding:

```python
# Wait up to 5 seconds for initial data
initial_wait = 0
while writer.queue.empty() and initial_wait < 50:
    time.sleep(0.1)
    initial_wait += 1
```

This ensures VLC gets data immediately upon connection.

### 3. Non-Blocking Thread Initialization

All threads are now daemon threads and start with a small delay to ensure proper initialization:

```python
source_thread = threading.Thread(target=self.source_listener, daemon=True)
playlist_thread = threading.Thread(target=self.playlist_feeder, daemon=True)
# ... start threads ...
time.sleep(0.5)  # Let threads initialize
```

## Testing the Fix

### 1. Restart the Server

```bash
python cycast_server.py
```

### 2. Connect with VLC

```bash
vlc http://localhost:8001/stream
```

**Expected behavior:**
- VLC connects
- Buffering message appears briefly
- Playback starts within 1-2 seconds
- No need to press Ctrl+C

### 3. Test with curl

```bash
# Should start receiving data immediately
curl http://localhost:8001/stream --output test.mp3
# Ctrl+C after a few seconds
ls -lh test.mp3  # Should be several KB
```

## If Still Having Issues

### Check Buffer Status

```bash
# While server is running
curl http://localhost:8001/api/stats | jq '.buffer'
```

**If buffer.available is 0:**
- Playlist not feeding data
- Check console for "Playing from playlist: ..." message
- Verify music files exist in `./music/`

### Enable Verbose Logging

Edit `config.hcl`:
```hcl
advanced {
  verbose_logging = true
}
```

Look for these messages:
```
Broadcaster thread started
No source connected, starting playlist fallback
Playing from playlist: test_tone.mp3
New listener from 127.0.0.1
```

### Test Different Players

**mpv (usually faster):**
```bash
mpv http://localhost:8001/stream
```

**ffplay (immediate):**
```bash
ffplay -nodisp -loglevel quiet http://localhost:8001/stream
```

**Browser:**
```
Open: http://localhost:8001/stream
```

If some players work and others don't, it's a player buffering issue, not a server issue.

## Understanding the Startup Sequence

**Correct sequence:**
1. Server starts → ✓
2. Threads initialize → ✓
3. Playlist starts feeding buffer → ✓
4. Broadcaster starts reading buffer → ✓
5. Client connects → ✓
6. Initial data wait (max 5 sec) → ✓
7. Streaming begins → ✓

**If hanging at step 6:**
- Buffer is empty
- Check console output
- Run: `curl http://localhost:8001/api/stats`

## VLC-Specific Settings

VLC has aggressive buffering. You can adjust it:

**Tools → Preferences → Show All → Input/Codecs:**
- Network caching: 1000ms (default is usually fine)
- File caching: 300ms

**Or via command line:**
```bash
vlc http://localhost:8001/stream --network-caching=500
```

## Alternative: Use Direct Audio Output

If VLC is problematic, try these alternatives:

**1. mpv (recommended for streams):**
```bash
mpv --cache=no http://localhost:8001/stream
```

**2. mplayer:**
```bash
mplayer -cache 128 http://localhost:8001/stream
```

**3. Browser HTML5:**
Open in browser and use built-in audio player:
```html
<audio controls autoplay>
  <source src="http://localhost:8001/stream" type="audio/mpeg">
</audio>
```

## Debugging Checklist

Run through this checklist:

- [ ] Server starts without errors
- [ ] Console shows "Broadcaster thread started"
- [ ] Console shows "Playing from playlist: ..."
- [ ] `/api/stats` shows buffer.available > 0
- [ ] VLC connects (shows buffering message)
- [ ] Playback starts within 5 seconds
- [ ] No Ctrl+C needed

If all checks pass, the issue is fixed!

## Advanced: Monitoring Startup

Add this to see exact timing:

```bash
python cycast_server.py &
SERVER_PID=$!

# Wait for server to be ready
sleep 2

# Connect and time it
time vlc http://localhost:8001/stream --play-and-exit --run-time=5

# Cleanup
kill $SERVER_PID
```

**Good timing:** Connection + buffering + start < 3 seconds
**Problematic:** > 10 seconds

## Still Not Working?

1. **Check firewall:**
   ```bash
   sudo ufw status
   # Ensure port 8001 is open
   ```

2. **Check port conflicts:**
   ```bash
   netstat -tuln | grep 8001
   # Should only show your Cycast server
   ```

3. **Test with local file first:**
   Verify VLC works normally:
   ```bash
   vlc /path/to/local.mp3
   ```

4. **Check system resources:**
   ```bash
   top
   # CPU should be <50%, plenty of RAM available
   ```

5. **Try with fresh config:**
   ```bash
   mv config.hcl config.hcl.backup
   python cycast_server.py  # Uses defaults
   ```

## Summary of Changes

The key changes that fix the Ctrl+C issue:

1. ✅ Tornado timeouts disabled for streaming
2. ✅ Initial data wait added (max 5 sec)
3. ✅ All threads daemonized
4. ✅ Startup delay added for thread initialization
5. ✅ Non-blocking queue operations throughout

These ensure VLC gets data immediately without blocking the event loop.
