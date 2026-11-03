import os

# Railway / Cloud Production Gunicorn Configuration
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"

# Concurrency and worker settings
workers = int(os.environ.get("WEB_CONCURRENCY", 2))
threads = int(os.environ.get("PYTHON_THREADS", 4))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
keepalive = 5

# Logging to stdout/stderr for Railway log streaming
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")

