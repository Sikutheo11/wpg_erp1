import multiprocessing


bind = "unix:/run/wpg-bos/gunicorn.sock"

# The first production Droplet has one vCPU and 2 GB RAM.
workers = min(
    multiprocessing.cpu_count() * 2,
    2,
)
threads = 2

worker_class = "sync"
timeout = 120
graceful_timeout = 30
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True

max_requests = 1000
max_requests_jitter = 50

# Avoid loading Django before Gunicorn forks its workers.
preload_app = False