# Quick Fix: AttributeError 'chunk_size'

## The Problem

```
AttributeError: 'stream_broadcaster.StreamBroadcaster' object has no attribute 'chunk_size'
```

## The Solution

The Cython module needs to be rebuilt with the updated code that declares `chunk_size` as a cdef attribute.

### Step 1: Rebuild Cython Modules

```bash
# Option A: Using make
make rebuild

# Option B: Manual rebuild
python setup.py build_ext --inplace

# Option C: Clean rebuild
make clean
make build
```

### Step 2: Verify the Fix

```bash
python test_chunk_size.py
```

You should see:
```
✓ Created buffer
✓ Created broadcaster with chunk_size=16384
✓ Broadcaster chunk_size: 16384
✓ Default chunk_size: 16384

✓✓✓ All tests passed! The chunk_size fix is working.
```

### Step 3: Run the Server

```bash
python cycast_server.py
```

## What Changed

The `stream_broadcaster.pyx` file was updated to include `chunk_size` in the cdef declarations:

```python
cdef class StreamBroadcaster:
    cdef:
        object audio_buffer
        dict listeners
        object listeners_lock
        int next_listener_id
        object broadcast_thread
        bint running
        Py_ssize_t chunk_size  # ← This line was added
```

This allows the Cython class to have a `chunk_size` attribute that can be set during initialization.

## Why This Happened

Cython classes need to explicitly declare attributes in the `cdef` block. Unlike pure Python, you can't just assign attributes in `__init__` - they must be declared first.

## Still Having Issues?

1. Make sure you're in the correct directory
2. Verify Cython is installed: `pip install Cython`
3. Check for permission issues with build files
4. Try a completely fresh rebuild:
   ```bash
   rm -f *.so *.c
   rm -rf build/
   python setup.py build_ext --inplace
   ```

## Verification Checklist

- [ ] Ran `make rebuild` or `python setup.py build_ext --inplace`
- [ ] Saw "Build complete" message
- [ ] `test_chunk_size.py` passes
- [ ] Can import: `python -c "import stream_broadcaster; print('OK')"`
- [ ] Server starts without AttributeError

If all boxes are checked, you're good to go! 🎉
