# Cycast Logging Guide

## Default Logging

By default, Cycast logs everything to **stdout** at the **INFO** level.

Example output:
```
2026-02-08 14:30:15,123 - cycast - INFO - ============================================================
2026-02-08 14:30:15,124 - cycast - INFO - Starting Cycast Server
2026-02-08 14:30:15,124 - cycast - INFO - ============================================================
2026-02-08 14:30:15,125 - cycast - INFO - Configuration loaded from: config.hcl
2026-02-08 14:30:15,125 - cycast - INFO - Source port: 8000 (password: ******)
2026-02-08 14:30:15,126 - cycast - INFO - Listen port: 8001
2026-02-08 14:30:15,240 - cycast.broadcaster - INFO - Broadcaster thread started
2026-02-08 14:30:15,241 - cycast - INFO - Playlist loaded: 3 tracks
2026-02-08 14:30:15,242 - cycast - INFO - No source connected, starting playlist fallback
```

## Log Levels

Cycast uses these log levels:

- **INFO**: Normal operations (startup, connections, playlist changes)
- **WARNING**: Non-critical issues (authentication failures, timeouts)
- **ERROR**: Errors that don't stop the server (file read errors, connection errors)

## Changing Log Level

### Via Environment Variable

```bash
# Show only warnings and errors
export CYCAST_LOG_LEVEL=WARNING
python cycast_server.py

# Show everything including debug (very verbose)
export CYCAST_LOG_LEVEL=DEBUG
python cycast_server.py
```

### Via Code (cycast_server.py)

Edit the logging setup at the top of `cycast_server.py`:

```python
# Change level=logging.INFO to:
logging.basicConfig(
    level=logging.WARNING,  # Only warnings and errors
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
```

## Logging to File

### Option 1: Redirect stdout

```bash
python cycast_server.py > cycast.log 2>&1
```

### Option 2: Use tee (see output and save to file)

```bash
python cycast_server.py | tee cycast.log
```

### Option 3: Modify cycast_server.py

Add a file handler:

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(
            'cycast.log',
            maxBytes=10485760,  # 10 MB
            backupCount=5
        )
    ]
)
```

This will:
- Log to stdout (terminal)
- Log to `cycast.log` file
- Rotate logs at 10 MB
- Keep 5 backup files

## Custom Format

Change the format string in `cycast_server.py`:

```python
# Simple format (just the message)
format='%(message)s'

# Compact format
format='%(asctime)s - %(levelname)s - %(message)s'

# Very detailed format
format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
```

## Logger Components

Cycast uses multiple loggers for different components:

- `cycast`: Main server
- `cycast.config`: Configuration loading
- `cycast.broadcaster`: Stream broadcaster (Cython)
- `cycast.web`: Flask web application

### Filter by Component

To see only broadcaster logs:

```python
# In cycast_server.py
logging.basicConfig(level=logging.INFO, ...)

# Then set other loggers to WARNING
logging.getLogger('cycast.config').setLevel(logging.WARNING)
logging.getLogger('cycast.web').setLevel(logging.WARNING)
# Now only cycast and cycast.broadcaster will show INFO
```

## systemd Service Logging

When running as a systemd service, logs go to journald:

```bash
# View logs
sudo journalctl -u cycast -f

# View logs from last hour
sudo journalctl -u cycast --since "1 hour ago"

# View only errors
sudo journalctl -u cycast -p err
```

## Production Recommendations

### 1. Use Log Rotation

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    '/var/log/cycast/cycast.log',
    maxBytes=10485760,  # 10 MB
    backupCount=10
)
```

### 2. Set Appropriate Level

```python
# Production: INFO or WARNING
level=logging.INFO

# Development: DEBUG
level=logging.DEBUG
```

### 3. Structure Logs for Parsing

```python
# JSON format for log aggregation
import json
import logging

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage()
        })

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logging.basicConfig(handlers=[handler])
```

## Troubleshooting Logs

### No Logs Appearing

Check that stdout isn't being suppressed:
```bash
python cycast_server.py 2>&1
```

### Too Verbose

Increase log level:
```bash
export CYCAST_LOG_LEVEL=WARNING
python cycast_server.py
```

### Need More Detail

Enable debug mode:
```bash
export CYCAST_LOG_LEVEL=DEBUG
python cycast_server.py
```

## Example: Production Logging Setup

```python
# In cycast_server.py, replace the logging.basicConfig() call:

import logging
from logging.handlers import RotatingFileHandler
import sys

# Create formatters
detailed_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
simple_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)

# Console handler (simple format)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(simple_formatter)
console_handler.setLevel(logging.INFO)

# File handler (detailed format, with rotation)
file_handler = RotatingFileHandler(
    '/var/log/cycast/cycast.log',
    maxBytes=10485760,  # 10 MB
    backupCount=10
)
file_handler.setFormatter(detailed_formatter)
file_handler.setLevel(logging.DEBUG)

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[console_handler, file_handler]
)

# Get logger for this module
logger = logging.getLogger('cycast')
```

This setup:
- Logs INFO and above to console (simple format)
- Logs DEBUG and above to file (detailed format)
- Rotates files at 10 MB
- Keeps 10 backup files
