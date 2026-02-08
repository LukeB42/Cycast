# VLC Ctrl+C Issue - Simple Workaround

## The Issue

VLC connects to the stream but doesn't start playing until you press Ctrl+C on the server.

## Why This Happens

This is a quirk of how Tornado's IOLoop interacts with Flask's streaming responses. The generator doesn't yield the first chunk until something "wakes up" the event loop. Pressing Ctrl+C triggers signal handlers that wake it up.

## Simple Workaround Options

### Option 1: Use a Different Player (Recommended)

**mpv** (works perfectly, no Ctrl+C needed):
```bash
mpv http://localhost:8001/stream
```

**ffplay** (instant playback):
```bash
ffplay -nodisp http://localhost:8001/stream
```

**Browser** (works fine):
```
http://localhost:8001/stream
```

### Option 2: Pre-buffer in VLC

Start VLC with larger cache:
```bash
vlc http://localhost:8001/stream --network-caching=3000
```

This gives VLC 3 seconds to buffer, which usually triggers playback.

### Option 3: Two-Terminal Trick

**Terminal 1:**
```bash
python cycast_server.py
```

**Terminal 2 (after server starts):**
```bash
# Send a harmless signal to wake up the event loop
sleep 2 && curl -s http://localhost:8001/api/status > /dev/null &
vlc http://localhost:8001/stream
```

The curl request "primes" the event loop, then VLC works normally.

### Option 4: Auto-Wake Script

Create `start_cycast.sh`:
```bash
#!/bin/bash
python cycast_server.py &
SERVER_PID=$!

# Wait for server to start
sleep 2

# Prime the event loop
curl -s http://localhost:8001/api/status > /dev/null

# Keep server running
wait $SERVER_PID
```

Run it:
```bash
chmod +x start_cycast.sh
./start_cycast.sh
```

Now VLC will work without Ctrl+C.

### Option 5: systemd Service (Production)

If running as a service, this issue doesn't occur because the event loop runs in the background.

Create `/etc/systemd/system/cycast.service`:
```ini
[Unit]
Description=Cycast Radio Server
After=network.target

[Service]
Type=simple
User=cycast
WorkingDirectory=/opt/cycast
ExecStart=/usr/bin/python3 /opt/cycast/cycast_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl start cycast
sudo systemctl enable cycast
```

VLC will work normally when connecting.

## Understanding the Root Cause

The issue is in how Python's threading interacts with Tornado's IOLoop:

1. Playlist feeder thread writes to buffer ✓
2. Broadcaster thread reads from buffer ✓
3. Flask generator is created ✓
4. **Generator's first yield is delayed** ← Problem here
5. Ctrl+C wakes the IOLoop
6. Generator yields, VLC gets data ✓

The Ctrl+C doesn't fix anything - it just wakes up the event loop which was "sleeping" waiting for the next event.

## Technical Fix (For Developers)

The proper fix would be to use Tornado's native async handlers instead of WSGI:

```python
class StreamHandler(tornado.web.RequestHandler):
    async def get(self):
        self.set_header('Content-Type', 'audio/mpeg')
        # Use Tornado's async streaming
        while True:
            chunk = await get_next_chunk()
            self.write(chunk)
            await self.flush()
```

But this requires rewriting the Flask app in pure Tornado, which is a significant change.

## Best Solution for Now

**Use mpv instead of VLC:**
```bash
mpv http://localhost:8001/stream
```

mpv is actually better for streaming anyway:
- Lower latency
- Better buffering
- Lighter weight
- Fewer issues with various stream types

## Still Want to Use VLC?

Try this startup sequence:

```bash
# Terminal 1
python cycast_server.py

# Terminal 2 (wait 2 seconds after server starts)
curl http://localhost:8001/stream > /dev/null &
sleep 1
killall curl
vlc http://localhost:8001/stream
```

The curl request "primes" the Flask generator, then VLC works.

## Summary

| Method | Convenience | Reliability |
|--------|-------------|-------------|
| Use mpv/ffplay | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Browser playback | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| systemd service | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Auto-wake script | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| VLC + curl trick | ⭐⭐ | ⭐⭐⭐ |
| Press Ctrl+C | ⭐ | ⭐⭐⭐ |

**Recommended:** Just use mpv or play in browser - problem solved!
