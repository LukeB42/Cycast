# Performance Tuning Guide

## Quick Fixes for Audio Skipping

### 1. Default Optimized Settings (Already Applied)

The latest `config.hcl` has been optimized with:

```hcl
buffer {
  size_mb = 20  # Doubled from 10 MB → ~2 min buffering
}

broadcaster {
  chunk_size = 16384  # Doubled from 8192 → less overhead
  sleep_high = 0.0005    # Reduced from 0.001 → more responsive
  sleep_medium = 0.001   # Reduced from 0.005
  sleep_low = 0.002      # Reduced from 0.010
}
```

**Impact:**
- 2x larger buffer = more buffering against interruptions
- 2x larger chunks = 50% less overhead per second
- 2-5x shorter sleep times = more responsive broadcasting

### 2. Rebuild After Config Changes

After updating `config.hcl`, rebuild the Cython modules:

```bash
python setup.py build_ext --inplace
python cycast_server.py
```

## Understanding the Buffer

### Buffer Size Calculation

```
Buffer Time = (buffer_size_mb * 1024 * 1024) / bitrate_bytes_per_second

For 128 kbps MP3:
- 10 MB = ~85 seconds
- 20 MB = ~170 seconds (~2.8 minutes)
- 50 MB = ~425 seconds (~7 minutes)
```

### Monitoring Buffer Health

Check buffer status while streaming:

```bash
curl http://localhost:8001/api/stats | jq '.buffer'
```

**Good buffer health:**
```json
{
  "available": 5242880,      // ~5 MB of data ready
  "space": 15728640,         // ~15 MB free space
  "fill_percentage": 25.0    // 25% full = healthy
}
```

**Warning signs:**
- `fill_percentage` < 5%: Buffer running low → increase buffer size
- `fill_percentage` > 95%: Buffer full → listeners not keeping up
- `available` fluctuating rapidly: Unstable source or CPU issues

## Tuning Parameters

### 1. Buffer Size (`buffer.size_mb`)

**Small (5-10 MB):**
- ✅ Low memory usage
- ✅ Faster start time
- ❌ More sensitive to CPU spikes
- **Use for:** Powerful servers, few listeners

**Medium (20-30 MB):**
- ✅ Good balance
- ✅ Handles brief interruptions
- ✅ Recommended default
- **Use for:** Most deployments

**Large (50-100 MB):**
- ✅ Maximum stability
- ✅ Survives long CPU spikes
- ❌ Higher memory usage
- ❌ Slower to start streaming
- **Use for:** Raspberry Pi, resource-constrained systems

### 2. Chunk Size (`broadcaster.chunk_size`)

**Small (4096-8192 bytes):**
- ✅ Lower latency
- ❌ More CPU overhead (more frequent operations)
- **Use for:** Live DJ sets, real-time sources

**Medium (16384 bytes) - RECOMMENDED:**
- ✅ Good balance of latency and efficiency
- ✅ ~100-200ms latency with typical setup
- **Use for:** Most use cases

**Large (32768-65536 bytes):**
- ✅ Maximum efficiency
- ❌ Higher latency (~500ms)
- **Use for:** Playlist-only streaming, non-interactive

### 3. Sleep Times (`broadcaster.sleep_*`)

**Current optimized values:**
```hcl
sleep_high = 0.0005    # 0.5ms when buffer >80% full
sleep_medium = 0.001   # 1ms when buffer 50-80% full  
sleep_low = 0.002      # 2ms when buffer <50% full
```

**For even smoother playback (more CPU):**
```hcl
sleep_high = 0.0001    # 0.1ms
sleep_medium = 0.0005  # 0.5ms
sleep_low = 0.001      # 1ms
```

**For lower CPU usage (potential skips):**
```hcl
sleep_high = 0.001     # 1ms
sleep_medium = 0.005   # 5ms
sleep_low = 0.01       # 10ms
```

## Common Scenarios

### Scenario 1: Raspberry Pi or Low-Power Device

**Problem:** CPU spikes cause skipping

**Solution:**
```hcl
buffer {
  size_mb = 50  # Large buffer
}

broadcaster {
  chunk_size = 32768  # Larger chunks = less overhead
  sleep_high = 0.001
  sleep_medium = 0.005
  sleep_low = 0.01
}
```

### Scenario 2: Many Concurrent Listeners (100+)

**Problem:** Broadcaster can't keep up with all listeners

**Solution:**
```hcl
buffer {
  size_mb = 30  # More buffer
}

broadcaster {
  chunk_size = 32768  # Larger chunks
  sleep_high = 0.0001  # Fast processing
  sleep_medium = 0.0005
  sleep_low = 0.001
}

advanced {
  max_listeners = 200  # Set a limit
}
```

### Scenario 3: Live DJ Streaming (Low Latency)

**Problem:** Need minimal delay between source and listeners

**Solution:**
```hcl
buffer {
  size_mb = 5  # Small buffer for low latency
}

broadcaster {
  chunk_size = 4096  # Small chunks
  sleep_high = 0.0001
  sleep_medium = 0.0005
  sleep_low = 0.001
}
```

### Scenario 4: Playlist-Only Station (Maximum Stability)

**Problem:** Want maximum stability, latency not critical

**Solution:**
```hcl
buffer {
  size_mb = 100  # Very large buffer
}

broadcaster {
  chunk_size = 65536  # Very large chunks
  sleep_high = 0.001
  sleep_medium = 0.005
  sleep_low = 0.01
}
```

## Advanced Tuning

### Operating System Level

**Linux - Increase process priority:**
```bash
# Run server with higher priority (requires sudo)
sudo nice -n -10 python cycast_server.py
```

**Linux - CPU affinity:**
```bash
# Pin to specific CPU cores
taskset -c 0,1 python cycast_server.py
```

**Disable CPU frequency scaling (constant max speed):**
```bash
# Ubuntu/Debian
sudo cpupower frequency-set -g performance
```

### Python Level

**Use PyPy for better performance (optional):**
```bash
# Install PyPy
sudo apt install pypy3 pypy3-dev

# Install dependencies
pypy3 -m pip install -r requirements.txt

# Build Cython (still uses CPython for Cython modules)
python setup.py build_ext --inplace

# Run with PyPy
pypy3 cycast_server.py
```

**Disable garbage collection during critical sections (advanced):**
This is already handled by the Cython code, but for pure Python parts you could disable GC.

### Network Level

**For internet streaming (not LAN):**

Use nginx buffer tuning:
```nginx
location /stream {
    proxy_pass http://localhost:8001;
    proxy_buffering off;
    proxy_buffer_size 16k;
    proxy_busy_buffers_size 24k;
    tcp_nodelay on;
}
```

## Measuring Performance

### CPU Usage

```bash
# Monitor CPU usage
top -p $(pgrep -f cycast_server.py)
```

**Good:** 10-30% CPU usage
**Warning:** >50% CPU - consider optimizing
**Critical:** >80% CPU - will cause skipping

### Memory Usage

```bash
# Check memory
ps aux | grep cycast_server.py
```

**Expected usage:**
- Base: ~50-100 MB
- + Buffer: config.buffer.size_mb
- + Per listener: ~1-2 MB

**Example:** 20 MB buffer + 10 listeners = ~100 MB total

### Latency Testing

Test end-to-end latency:

```bash
# Terminal 1: Start server
python cycast_server.py

# Terminal 2: Measure time to first byte
time curl -I http://localhost:8001/stream
```

**Good:** <100ms
**Acceptable:** 100-500ms
**High:** >500ms (check buffer size, chunk size)

### Throughput Testing

Test sustained throughput:

```bash
# Download for 30 seconds
timeout 30 curl http://localhost:8001/stream -o /dev/null -w "%{speed_download}\n"
```

**Expected:** ~16,000 bytes/sec for 128kbps stream
**If lower:** Skipping is occurring

## Diagnostics

### Enable Verbose Logging

```hcl
advanced {
  verbose_logging = true
}
```

This shows:
- Every chunk read from buffer
- Every chunk sent to listeners
- Buffer fill percentage updates
- Timing information

### Monitor Buffer in Real-Time

```bash
# Poll buffer stats every second
watch -n 1 'curl -s http://localhost:8001/api/stats | jq .buffer'
```

### Listener Connection Analysis

```bash
# Check connected listeners
curl -s http://localhost:8001/api/stats | jq '.listeners'
```

Look for:
- Listeners with very low `bytes_sent` (stalled)
- Many listeners connecting/disconnecting (network issues)

## Quick Reference

| Issue | Increase | Decrease |
|-------|----------|----------|
| Skipping/stuttering | buffer.size_mb | sleep times |
| High CPU usage | sleep times | chunk_size |
| High latency | — | buffer.size_mb, chunk_size |
| Memory usage too high | — | buffer.size_mb |
| Can't handle many listeners | chunk_size | sleep times |

## Recommended Configurations by Use Case

### Home Server (Default)
```hcl
buffer { size_mb = 20 }
broadcaster { chunk_size = 16384, sleep_low = 0.002 }
```

### Raspberry Pi
```hcl
buffer { size_mb = 50 }
broadcaster { chunk_size = 32768, sleep_low = 0.01 }
```

### Production Server (100+ listeners)
```hcl
buffer { size_mb = 30 }
broadcaster { chunk_size = 32768, sleep_low = 0.001 }
advanced { max_listeners = 500 }
```

### Low-Latency DJ Mode
```hcl
buffer { size_mb = 5 }
broadcaster { chunk_size = 4096, sleep_low = 0.0005 }
```

After changing configuration, always:
1. Restart the server
2. Test with `curl` for 30 seconds
3. Monitor buffer with `/api/stats`
4. Adjust as needed
